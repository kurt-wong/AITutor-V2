import answer_verifier as av


def test_html_table_keeps_blank_cells_aligned():
    html = (
        "<table><tr><td>\u9898\u53f7</td><td>1</td><td>2</td><td>3</td><td>4</td>"
        "<td>5</td><td>6</td><td>7</td><td>8</td></tr>"
        "<tr><td>\u7b54\u6848</td><td>C</td><td>B</td><td>D</td><td></td>"
        "<td>C</td><td>D</td><td></td><td>B</td></tr></table>"
    )
    mapping, blank = av._parse_html_tables(html)
    assert mapping[5] == "C"
    assert mapping[6] == "D"
    assert mapping[8] == "B"
    assert 4 in blank
    assert 7 in blank


def test_prefix_parser_does_not_match_free_text():
    text = "18. was awarded\n21. confusing\n26. A\n37. B"
    mapping = av._parse_prefix(text)
    assert 18 not in mapping
    assert 21 not in mapping
    assert mapping[26] == "A"
    assert mapping[37] == "B"


def test_inline_parser_matches_history():
    text = (
        "1\uff0e\u3010\u5206\u6790\u3011\u672c\u9898\u4e3b\u8981\u8003\u67e5\u77f3\u5668\u65f6\u4ee3\u3002\n"
        "\u3010\u89e3\u7b54\u3011\u2026\u2026\u9009\u7b54C\u9879\uff1b\n"
        "2\uff0e\u2026\u2026\u9009\u7b54B\u9879\u3002"
    )
    mapping = av._parse_inline(text)
    assert mapping[1] == "C"
    assert mapping[2] == "B"


def test_raw_table_priority_over_ocr_errors():
    raw = (
        "\u53c2\u8003\u7b54\u6848\n\u9898\u53f7\n1\n2\n3\n4\n5\n6\n7\n"
        "\u7b54\u6848\nD\nA\nC\nB\nD\nC\nA\n"
    )
    ocr = (
        "<table><tr><td>\u9898\u53f7</td><td>1</td><td>2</td><td>3</td><td>4</td>"
        "<td>5</td><td>6</td><td>7</td></tr>"
        "<tr><td>\u7b54\u6848</td><td>D</td><td>A</td><td>C</td><td>B</td>"
        "<td>a</td><td>D</td><td>\u2200</td></tr></table>"
    )
    evidence = av.build_evidence(raw, "", ocr)
    assert evidence.table[5] == "D"
    assert evidence.table[6] == "C"
    assert evidence.table[7] == "A"


def test_long_free_text_answer_needs_manual_review():
    """长自由文本答案（作文/长解答题）→ essay_manual_review（需人工审核）。

    2026-08-25：英语 Q46 作文答案（713 字符）无法通过答案区标记自动验证，
    标记为"需人工审核"，区别于短答案的 free_text_answer。
    """
    raw = "\u53c2\u8003\u7b54\u6848\n\u9898\u53f7 46\n\u7b54\u6848\n\u4e00\u7bc7\u8303\u6587"
    evidence = av.build_evidence(raw, "", "")
    essay = "Dear Jim,\n" + "I am very glad to hear that you are coming to China. " * 8
    ver = av.verify_one("46", essay, None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "essay_manual_review"


def test_short_free_text_answer_stays_free_text():
    """短自由文本答案（找不到证据）仍标记 free_text_answer。"""
    raw = "\u53c2\u8003\u7b54\u6848\n\u9898\u53f7 1\n\u7b54\u6848\nA"
    evidence = av.build_evidence(raw, "", "")
    # 题号 9 不在答案区，答案较短（<100 字符）→ free_text_answer
    ver = av.verify_one("9", "x\u7684\u503c\u4e3a\u221a2", None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "free_text_answer"


def test_long_essay_matches_answer_area_without_qn_marker():
    """长作文答案在答案区逐字出现（无题号标记）→ matched（英语 Q46 类）。

    作文区是"第二节(20分) One possible version: Dear Jim, …"（无 "46." 锚点），
    _find_free_text 无法命中；答案前 40 字符在答案区逐字出现即可验证。
    """
    raw = (
        "参考答案 第二节(20分) One possible version:\n"
        "Dear Jim,\n"
        "I am so glad to hear you are coming to China to check out our cultural heritage!\n"
        "Since you are into history, my top suggestion is the Terracotta Army in Xi'an.\n"
        "Yours, Li Hua"
    )
    evidence = av.build_evidence(raw, "", "")
    essay = (
        "Dear Jim,\n"
        "I am so glad to hear you are coming to China to check out our cultural heritage!\n"
        "Since you are into history, my top suggestion is the Terracotta Army in Xi'an.\n"
        "Yours, Li Hua"
    )
    ver = av.verify_one("46", essay, None, evidence)
    assert ver.status == av.MATCHED
    assert ver.evidence_kind == "essay"


def test_long_essay_not_in_answer_area_stays_manual_review():
    """长作文答案不在答案区 → 仍 essay_manual_review（不得误报 matched）。"""
    raw = "参考答案 一篇范文 46."
    evidence = av.build_evidence(raw, "", "")
    essay = "Dear Jim,\n" + "I am very glad to hear that you are coming to China. " * 8
    ver = av.verify_one("46", essay, None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "essay_manual_review"


def test_normalize_math_unifies_three_representations():
    """DB/OCR/PDF 三路表示归一化到同一纯文本（数学二中卷 Q13 类）。

    归一化保留空白，比对前由 compact_text 统一（_find_free_text 的实际用法）。
    """
    db = "①. $0$ ②. $\\frac{4}{3}$"
    ocr = "①.$0\\quad\\textcircled{2}.\\;\\frac{4}{3}$"
    assert av.compact_text(av.normalize_math(db)) == "①.0②.4/3"
    assert av.compact_text(av.normalize_math(ocr)) == "①.0②.4/3"
    # 非 LaTeX 文本原样返回
    assert av.normalize_math("普通答案 A") == "普通答案 A"
    assert av.normalize_math("") == ""


def test_normalize_math_common_commands():
    assert av.compact_text(av.normalize_math(r"$\frac{\pi}{4}$")) == "π/4"
    assert av.compact_text(av.normalize_math(r"$6+6\sqrt{3}$")) == "6+6sqrt(3)"
    assert av.compact_text(av.normalize_math(r"$\{x\mid x=\frac{\pi}{12}+k\pi,k\in Z\}$")) == "x|x=π/12+kπ,kinZ"
    assert av.compact_text(av.normalize_math(r"$(-2,2)$")) == "(-2,2)"


def test_latex_db_answer_matches_ocr_latex_evidence():
    """DB LaTeX 答案 vs OCR LaTeX 答案区：归一化后 free_text 命中。"""
    ocr = "参考答案 13. 【答案】①. $0\\quad\\textcircled{2}.\\;\\frac{4}{3}$"
    evidence = av.build_evidence("", "", ocr)
    ver = av.verify_one("13", "①. $0$ ②. $\\frac{4}{3}$", None, evidence)
    assert ver.status == av.MATCHED
    assert ver.evidence_kind == "free_text"


def test_latex_answer_equality_via_table():
    """DB `$0$` vs 答案区表格 `0`：归一化后相等算 matched。"""
    evidence = av.DocumentAnswerEvidence(table={13: "0"})
    ver = av.verify_one("13", "$0$", None, evidence)
    assert ver.status == av.MATCHED
    assert ver.evidence_kind == "table"


def test_latex_missing_minus_not_false_positive():
    """OCR 答案区丢失负号（`\\frac{7}{3}` 无 `-`）时不得误报 matched（Q15 类）。"""
    ocr = "参考答案 15. 【答案】①. $6$ ②. $\\frac{7}{3}$"
    evidence = av.build_evidence("", "", ocr)
    ver = av.verify_one("15", "①. $6$ ②. $-\\frac{7}{3}$", None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "free_text_answer"


def test_plain_table_with_blank_cells_recovered():
    """竖排答案表含空单元格（物理八十中 Q4/Q7 空白）不再整体丢弃。

    2026-08-25：10 个题号只有 8 个答案（Q4/Q7 空单元格，答案在文末
    "自主命制试题答案"单独给出），旧实现 len 不等丢弃整行 → Q3/Q9/Q10
    失去答案证据。新实现按行重排：空行=空单元格，位置对齐。
    """
    raw = (
        "参考答案\n一、单项选择题\n题号\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"
        "答案\nC\nB\nD\n\nC\nD\n\nB\nD\nC\n二、多项选择题\n题号 11 12 13 14\n答案 BC AC AD BC"
    )
    evidence = av.build_evidence(raw, "", "")
    assert evidence.table[1] == "C"
    assert evidence.table[2] == "B"
    assert evidence.table[3] == "D"
    assert evidence.table[5] == "C"
    assert evidence.table[6] == "D"
    assert evidence.table[8] == "B"
    assert evidence.table[9] == "D"
    assert evidence.table[10] == "C"
    assert evidence.table[11] == "BC"
    assert 4 in evidence.blank_qns
    assert 7 in evidence.blank_qns
    ver = av.verify_one("3", "D", None, evidence)
    assert ver.status == av.MATCHED
    assert ver.evidence_kind == "table"


def test_composite_sub_answer_inline_search():
    """综合题子题答案内联搜索（物理八十中 Q15/Q16 类）。

    子题号"（1）"非数字走不了 verify_one 数字路径；父题整体答案因
    全角/半角+分值注记插缝整段命不中。按子题逐个在父题号附近搜索。
    """
    raw = (
        "参考答案 三、实验题\n15． （1）1.50 （2 分） （2）不能 （2 分） "
        "（3）0.50 （2 分）     100（2 分）\n"
        "16． （1）B （2分）\n（2）使小车所受合力大小等于绳上的拉力大小（2分）\n"
        "（3）左（1 分）         0.45（0.43~0.46 均可）（2 分）\n（4）C （3 分）"
    )
    evidence = av.build_evidence(raw, "", "")
    subs15 = [
        {"qno": "(1)", "answer": "1.50"},
        {"qno": "(2)", "answer": "不能"},
        {"qno": "(3)", "answer": "0.50；100"},
    ]
    ver15 = av.verify_one("15", "（1）1.50；（2）不能；（3）0.50；100", subs15, evidence)
    assert ver15.status == av.MATCHED
    assert ver15.evidence_kind == "composite"
    subs16 = [
        {"qno": "(1)", "answer": "B"},
        {"qno": "(2)", "answer": "使小车所受合力大小等于绳上的拉力大小"},
        {"qno": "(3)", "answer": "左；0.45（0.43~0.46均可）"},
        {"qno": "(4)", "answer": "C"},
    ]
    ver16 = av.verify_one("16", "（1）B；（2）使小车所受合力大小等于绳上的拉力大小；（3）左；0.45 (0.43~0.46均可)；（4）C", subs16, evidence)
    assert ver16.status == av.MATCHED
    assert ver16.evidence_kind == "composite"


def test_composite_sub_answer_partial_stays_unverifiable():
    """子题只找到部分（一个错/缺）→ 仍 composite_subquestion，不得算通过。"""
    raw = "参考答案 15． （1）1.50 （2 分） （2）不能 （2 分） （3）0.50 （2 分）"
    evidence = av.build_evidence(raw, "", "")
    subs = [
        {"qno": "(1)", "answer": "1.50"},
        {"qno": "(2)", "answer": "可以"},  # 答案区是"不能"，找不到"可以"
        {"qno": "(3)", "answer": "0.50"},
    ]
    ver = av.verify_one("15", "（1）1.50；（2）可以；（3）0.50", subs, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "composite_subquestion"


def test_structured_condensed_answer_matches_full_solution():
    """结构化精简答案 vs 完整解答（物理 Q17 类）。

    DB `（1）$a=0.2\\text{m/s}^2$；（2）$m=70\\text{kg}$；…` 无法整段命中
    答案区完整解答（含中间步骤与分值注记）→ 按子部分拆取 "=" 后核心值核对。
    """
    ocr = (
        "参考答案 17.(7分)解:(1)$a=\\frac{\\Delta v}{\\Delta t}=0.2\\text{m/s}^2$"
        "(2分公式1分结果1分)(2)由$F=ma$得$m=\\frac{F}{a}=70\\text{kg}$"
        "(2分公式1分结果1分)(3)$x=\\frac{1}{2}at^2$得$x=0.4\\text{m}$(3分公式2分结果1分)"
    )
    evidence = av.build_evidence("", "", ocr)
    answer = "（1）$a=0.2\\text{m/s}^2$；（2）$m=70\\text{kg}$；（3）$x=0.4\\text{m}$"
    ver = av.verify_one("17", answer, None, evidence)
    assert ver.status == av.MATCHED
    assert ver.evidence_kind == "structured"


def test_structured_condensed_answer_long_sub_section():
    """结构化答案的子部分很长（答案值远离子题标记）→ 大窗口仍能命中（物理 Q20 类）。"""
    ocr = (
        "参考答案 20.(11分)解:(1)由平衡条件可得:$f=F\\sin\\theta$(2分)"
        "(2)小包裹的速度$v_2$大于传送带的速度$v_1$,所以小包裹受到传送带的摩擦力方向沿传送带向上,"
        "根据牛顿第二定律可知$\\mu mg\\cos\\theta-mg\\sin\\theta=ma$,解得$a=0.4\\text{m/s}^2$(1分)"
        "小包裹开始阶段在传送带上做匀减速直线运动,所用时间$t_1=\\frac{v_2-v_1}{a}=2.5\\text{s}$(1分)"
        "在传送带上滑动的距离为$x_1=\\frac{v_1+v_2}{2}t_1=2.75\\text{m}$(1分)"
        "因为小包裹所受滑动摩擦力大于重力沿传送带方向上的分力,所以小包裹与传送带共速后做匀速直线运动,"
        "匀速运动的时间为$t_2=\\frac{L-x_1}{v_1}=2\\text{s}$(1分)"
        "所以小包裹通过传送带的时间为$t=t_1+t_2=4.5\\text{s}$(1分)"
        "(3)设平板及长柱体底面与水平面的夹角为$\\varphi$,字典在平板上受到的最大静摩擦力$f_1=\\mu mg\\cos\\varphi$(1分)"
        "可得$\\frac{f_1}{f_2}=\\cos\\theta$(1分)"
    )
    evidence = av.build_evidence("", "", ocr)
    answer = "（1）$f = F\\sin\\theta$；（2）$t = 4.5\\text{s}$；（3）$\\frac{f_1}{f_2} = \\cos\\theta$"
    ver = av.verify_one("20", answer, None, evidence)
    assert ver.status == av.MATCHED
    assert ver.evidence_kind == "structured"


def test_structured_condensed_answer_partial_stays_unverifiable():
    """结构化答案部分命中（一个值错误）→ 不得算通过。"""
    ocr = (
        "参考答案 17.(7分)解:(1)$a=\\frac{\\Delta v}{\\Delta t}=0.2\\text{m/s}^2$(2分)"
        "(2)由$F=ma$得$m=\\frac{F}{a}=70\\text{kg}$(2分)"
        "(3)$x=\\frac{1}{2}at^2$得$x=0.4\\text{m}$(3分)"
    )
    evidence = av.build_evidence("", "", ocr)
    # 第 (2) 部分值错误（80 而非 70）
    answer = "（1）$a=0.2\\text{m/s}^2$；（2）$m=80\\text{kg}$；（3）$x=0.4\\text{m}$"
    ver = av.verify_one("17", answer, None, evidence)
    assert ver.status == av.UNVERIFIABLE
    assert ver.reason == "structured_partial"
