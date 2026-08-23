"""WP3 测试 — 答案匹配与质量门：堵住高置信度错误答案路径。

覆盖：
  - document_answer_table 不再无条件 confidence=1.0
  - 公式丢失答案（如 Q11 的 "2 2"）→ 低置信度 + "答案可疑"标记
  - 质量门对"答案可疑"→ "答案可疑，禁止自动发布" + confidence < 0.8
  - llm_fallback 空答案保持 blocked（现有行为不回归）
"""

from app.domains.document.answer_matcher import match_answers
from app.domains.document.quality_gate import evaluate_quality
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import SlicedQuestion, SourceProvenance


def _doc_with_answer_table(answers_line: str) -> L1Document:
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 已知函数f(x)=2x+1，则f(3)=", "text"),
        L1Line("P1L002", 1, 2, 2, "参考答案", "text"),
        L1Line("P1L003", 1, 3, 3, answers_line, "text"),
    ]
    return L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )


def test_answer_matcher_answer_table_confidence_is_not_hardcoded():
    """答案表命中的 provenance confidence 不应是硬编码 1.0。"""
    doc = _doc_with_answer_table("（1）A")
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="已知函数f(x)=2x+1，则f(3)=",
            options=[{"label": "A", "text": "5"}, {"label": "B", "text": "6"}],
        ),
    ]
    result = match_answers(questions, doc)
    prov = result[0].answer_provenance
    assert prov.source == "document_answer_table"
    assert prov.confidence != 1.0, "答案表置信度不应硬编码 1.0"
    assert prov.confidence == 0.95
    assert "文末答案表第1题" in prov.evidence
    # evidence 应包含命中的行 ID 和原始答案表文本
    assert "P1L003" in prov.evidence, f"evidence 应含行 ID: {prov.evidence}"
    assert "（1）A" in prov.evidence, f"evidence 应含原始答案表文本: {prov.evidence}"


def test_answer_matcher_formula_loss_sets_low_confidence():
    """公式丢失答案（题干含公式线索、答案只有数字碎片）→ 低置信度 + 答案可疑标记。"""
    # Q11 模拟：golden = \frac{\sqrt{2}}{2}，文本层提取成 "2 2"
    doc = _doc_with_answer_table("（11）2 2")
    questions = [
        SlicedQuestion(
            question_number="11",
            question_type="fill_in",
            stem="（11） 3π sin\n=           .\n4",
            options=[],
        ),
    ]
    result = match_answers(questions, doc)
    prov = result[0].answer_provenance
    assert prov.source == "document_answer_table"
    assert prov.confidence < 0.8, f"公式丢失答案置信度必须 < 0.8: {prov.confidence}"
    assert result[0].answer == "2 2"
    assert any("答案可疑" in i for i in result[0].issues), (
        f"issues 应含'答案可疑': {result[0].issues}"
    )


def test_answer_matcher_plain_integer_not_suspicious():
    """答案表明确写 '7' 时，即使题干含公式线索，也不能误判为公式丢失。"""
    doc = _doc_with_answer_table("（13）7")
    questions = [
        SlicedQuestion(
            question_number="13",
            question_type="fill_in",
            stem="（13）已知$x>0$，则$x+\\frac{x+9}{x}$的最小值为",
            options=[],
        ),
    ]
    result = match_answers(questions, doc)
    prov = result[0].answer_provenance
    assert prov.source == "document_answer_table"
    assert prov.confidence >= 0.8, f"普通整数答案不应降级: {prov.confidence}"
    assert not any("答案可疑" in i for i in result[0].issues), result[0].issues


def test_quality_gate_blocks_formula_loss_answer():
    """质量门对公式丢失答案 → '答案可疑，禁止自动发布' + confidence < 0.8。"""
    questions = [
        SlicedQuestion(
            question_number="11",
            question_type="fill_in",
            stem="（11） 3π sin\n=           .\n4",
            options=[],
            answer="2 2",
            answer_provenance=SourceProvenance(
                "answer", "document_answer_table", 0.4,
                evidence="文末答案表第11题 [P1L003=（11）2 2]",
            ),
            issues=["答案可疑（题干含公式但答案疑似符号丢失）"],
        ),
    ]
    result = evaluate_quality(questions)
    sq = result[0]
    assert sq.confidence < 0.8, f"公式丢失答案 confidence 必须 < 0.8: {sq.confidence}"
    assert any("答案可疑，禁止自动发布" in i for i in sq.issues), (
        f"issues 应含'答案可疑，禁止自动发布': {sq.issues}"
    )


def test_quality_gate_blocks_empty_llm_answer():
    """llm_fallback 空答案保持 blocked（现有行为不回归）。"""
    questions = [
        SlicedQuestion(
            question_number="17",
            question_type="short_answer",
            stem="解答题",
            options=[],
            answer=None,
            answer_provenance=SourceProvenance(
                "answer", "llm_fallback", 0.5, "无文档答案，需 LLM 推理",
            ),
        ),
    ]
    result = evaluate_quality(questions)
    sq = result[0]
    assert sq.confidence < 0.8
    assert any("答案缺失，禁止自动发布" in i for i in sq.issues), (
        f"issues 应含'答案缺失，禁止自动发布': {sq.issues}"
    )


def test_q11_analog_never_high_conf_with_wrong_formula_answer():
    """Q11 端到端模拟：即使答案非空，公式丢失也必须禁止自动发布。"""
    doc = _doc_with_answer_table("（11）2 2")
    questions = [
        SlicedQuestion(
            question_number="11",
            question_type="fill_in",
            stem="（11） 3π sin\n=           .\n4",
            options=[],
        ),
    ]
    # answer_matcher → quality_gate 完整链路
    matched = match_answers(questions, doc)
    evaluated = evaluate_quality(matched)
    sq = evaluated[0]
    assert sq.answer == "2 2"  # 答案非空
    assert sq.confidence < 0.8, f"Q11 类结果 confidence 必须 < 0.8: {sq.confidence}"
    assert any("禁止自动发布" in i for i in sq.issues), (
        f"Q11 类结果必须禁止自动发布: {sq.issues}"
    )
    # provenance 已降级，不能是满置信度
    assert sq.answer_provenance.confidence < 0.8


def test_answer_matcher_pua_answer_low_confidence():
    """答案含 PUA 字符 → 低置信度 + 答案可疑。"""
    doc = _doc_with_answer_table("（1）\ue888\ue889")
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="题目",
            options=[],
        ),
    ]
    result = match_answers(questions, doc)
    assert result[0].answer_provenance.confidence < 0.8
    assert any("答案可疑" in i for i in result[0].issues)


def test_answer_matcher_math_formula_in_dollars_not_suspicious():
    """成对 $ 包裹的 LaTeX 公式是合法数学答案，不应降级（Q11 真实 PP 场景）。"""
    doc = _doc_with_answer_table("（11）$\\frac{\\sqrt{2}}{2}$")
    questions = [
        SlicedQuestion(
            question_number="11",
            question_type="fill_in",
            stem="（11） 3π sin\n=           .\n4",
            options=[],
        ),
    ]
    result = match_answers(questions, doc)
    prov = result[0].answer_provenance
    assert prov.source == "document_answer_table"
    assert prov.confidence == 0.95, f"成对 $ 公式不应降级: {prov.confidence}"
    assert not any("答案可疑" in i for i in result[0].issues), (
        f"成对 $ 公式不应带'答案可疑': {result[0].issues}"
    )


def test_answer_matcher_bare_latex_is_suspicious():
    """裸 LaTeX（无 $ 包裹）是提取残留，应降级。"""
    doc = _doc_with_answer_table("（1）\\frac{1}{2}")
    questions = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="题目",
            options=[],
        ),
    ]
    result = match_answers(questions, doc)
    assert result[0].answer_provenance.confidence < 0.8
    assert any("未解析 LaTeX" in i for i in result[0].issues)


def test_answer_table_dot_format():
    """点号格式答案表（英语 "1. D"）应被解析。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "1. D", "text"),
        L1Line("P1L003", 1, 3, 3, "2. C", "text"),
        L1Line("P1L004", 1, 4, 4, "3. A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [
        SlicedQuestion("1", "single_choice", stem="s1", options=[]),
        SlicedQuestion("2", "single_choice", stem="s2", options=[]),
        SlicedQuestion("3", "single_choice", stem="s3", options=[]),
    ]
    result = match_answers(questions, doc)
    assert [q.answer for q in result] == ["D", "C", "A"]
    assert all(q.answer_provenance.source == "document_answer_table" for q in result)


def test_inline_answer_same_line_dot_format():
    """题号与【答案】同行的点号格式（"11.【答案】would attend"）应被匹配。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "11.【答案】would attend", "text"),
        L1Line("P1L003", 1, 3, 3, "12.【答案】to become", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [
        SlicedQuestion("11", "fill_in", stem="s11", options=[]),
        SlicedQuestion("12", "fill_in", stem="s12", options=[]),
    ]
    result = match_answers(questions, doc)
    assert result[0].answer == "would attend"
    assert result[1].answer == "to become"
    assert result[0].answer_provenance.source == "document_answer_table"


def test_answer_table_detail_block_does_not_pollute():
    """详解区块后的写作指导行（"1.词汇积累"）不得覆盖真实答案。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "1. D", "text"),
        L1Line("P1L003", 1, 3, 3, "【导语】本文是一篇记叙文", "text"),
        L1Line("P1L004", 1, 4, 4, "2. 词汇积累", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [SlicedQuestion("1", "single_choice", stem="s1", options=[])]
    result = match_answers(questions, doc)
    assert result[0].answer == "D", f"详解区不应污染答案: {result[0].answer}"


def test_answer_table_table_format():
    """物理表格格式（"题号 1 2 3" + "答案 C B D" 两行配对）应被解析。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "一、单项选择题", "text"),
        L1Line("P1L003", 1, 3, 3, "题号  1  2  3", "text"),
        L1Line("P1L004", 1, 4, 4, "答案  C  B  D", "text"),
        L1Line("P1L005", 1, 5, 5, "二、多项选择题", "text"),
        L1Line("P1L006", 1, 6, 6, "题号  4  5", "text"),
        L1Line("P1L007", 1, 7, 7, "答案  BC  AC", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [
        SlicedQuestion("1", "single_choice", stem="s1", options=[]),
        SlicedQuestion("2", "single_choice", stem="s2", options=[]),
        SlicedQuestion("3", "single_choice", stem="s3", options=[]),
        SlicedQuestion("4", "multiple_choice", stem="s4", options=[]),
        SlicedQuestion("5", "multiple_choice", stem="s5", options=[]),
    ]
    result = match_answers(questions, doc)
    assert [q.answer for q in result] == ["C", "B", "D", "BC", "AC"]


def test_answer_table_mixed_dot_paren_no_truncation():
    """混合行（"15． （1）1.50..."）点号题号答案延伸到行尾，括号子步骤不截断。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, "15． （1）1.50 （2 分） （2）不能 （2 分）", "text"),
        L1Line("P1L003", 1, 3, 3, "16． （1）B （2分）", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="native",
        total_pages=1,
    )
    questions = [
        SlicedQuestion("15", "fill_in", stem="实验题15", options=[]),
        SlicedQuestion("16", "fill_in", stem="实验题16", options=[]),
    ]
    result = match_answers(questions, doc)
    assert result[0].answer == "（1）1.50 （2 分） （2）不能 （2 分）", (
        f"Q15 答案不应被括号子步骤截断: {result[0].answer!r}"
    )
    assert result[1].answer == "（1）B （2分）"


def test_answer_table_pp_html_format():
    """PP-StructureV3 把答案表格识别为 HTML <table> 行时应能解析（物理 canonical 场景）。"""
    html_line = (
        "<html><body><table>"
        "<tr><td>题号</td><td>1</td><td>2</td><td>3</td></tr>"
        "<tr><td>答案</td><td>C</td><td>B</td><td>D</td></tr>"
        "</table></body></html>"
    )
    lines = [
        L1Line("P1L001", 1, 1, 1, "参考答案", "text"),
        L1Line("P1L002", 1, 2, 2, html_line, "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    questions = [
        SlicedQuestion("1", "single_choice", stem="s1", options=[]),
        SlicedQuestion("2", "single_choice", stem="s2", options=[]),
        SlicedQuestion("3", "single_choice", stem="s3", options=[]),
    ]
    result = match_answers(questions, doc)
    assert [q.answer for q in result] == ["C", "B", "D"]
    assert all(q.answer_provenance.source == "document_answer_table" for q in result)
