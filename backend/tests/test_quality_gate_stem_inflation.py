"""P0-4 严格测试：quality_gate 题干异常膨胀检测。

审计发现（bugs.md BUG-012 §三 B/D）：
- quality_gate confidence 是纯结构打分，从不校验题干长度/材料混入 →
  英语综合题材料整段并入题干（stem 2000-2600 字符）仍 0.9 approved。
- 修复：非综合题 stem > 800 字符、综合题 stem > 3000 字符 → 降分 + 标记 issue。

本测试用真实 SlicedQuestion 验证：正常题不触发、材料混入题触发降分、
合理的长综合题不误伤。
"""

from app.domains.document.quality_gate import (
    _STEM_CHAR_LIMIT_COMPOSITE,
    _STEM_CHAR_LIMIT_NON_COMPOSITE,
    evaluate_quality,
)
from app.domains.document.schemas_l2 import SlicedQuestion


def _q(stem: str, *, is_composite: bool = False, qtype: str = "single_choice",
       with_answer: bool = True) -> SlicedQuestion:
    options = (
        [{"label": "A", "text": "x"}, {"label": "B", "text": "y"},
         {"label": "C", "text": "z"}, {"label": "D", "text": "w"}]
        if qtype in ("single_choice", "multiple_choice") else []
    )
    q = SlicedQuestion(
        question_number="1",
        question_type=qtype,
        stem=stem,
        options=options,
        answer="C" if with_answer else None,
        confidence=0.5,
        is_composite=is_composite,
        sub_questions=[{"qno": "1", "question_type": "single_choice", "answer": "C"}] if is_composite else None,
    )
    return q


class TestStemInflationDetection:
    def test_normal_question_not_flagged(self):
        """正常单题题干（远小于阈值）→ 不触发膨胀。"""
        q = _q("1. 已知函数 f(x)=x²-2x+3，求 f(1) 的值。")
        result = evaluate_quality([q])
        assert "题干异常膨胀" not in q.issues
        assert q.confidence >= 0.8  # 正常题保持高置信

    def test_composite_material_inflated_stem_flagged(self):
        """非综合题 stem 超 800 字符（材料混入）→ 标记 issue + 降分。"""
        # 模拟英语材料并入：一段材料 + 题目
        material = ("The ways we celebrate traditions can change over time. " * 40)[:900]
        q = _q(f"1. {material} ...题目...")
        result = evaluate_quality([q])
        assert any("题干异常膨胀" in i for i in q.issues)
        # 0.5 基础分扣 0.4 → 0.1（若还有别的扣分则更低），必低于 approved 门槛 0.8
        assert q.confidence < 0.8, f"材料混入题不应 approved，实际 conf={q.confidence}"

    def test_reasonable_long_composite_not_flagged(self):
        """综合题合理长题干（材料+子题，<3000 字符）→ 不误伤。"""
        material = ("A passage about traditions " * 100)[:2500]
        q = _q(material, is_composite=True, qtype="fill_in")
        result = evaluate_quality([q])
        assert "题干异常膨胀" not in q.issues

    def test_extreme_composite_material_flagged(self):
        """综合题 stem 超 3000 字符（材料被重复复制）→ 标记。"""
        material = ("A very long passage " * 200)[:3500]
        q = _q(material, is_composite=True, qtype="fill_in")
        result = evaluate_quality([q])
        assert any("题干异常膨胀" in i for i in q.issues)

    def test_threshold_values_exposed(self):
        """阈值常量存在且合理（防止误改）。"""
        assert _STEM_CHAR_LIMIT_NON_COMPOSITE == 800
        assert _STEM_CHAR_LIMIT_COMPOSITE == 3000

    def test_english_real_case_confidence_dropped(self):
        """真实观测：英语材料并入题 stem 2608 字符 → 修复后不 approved。

        对应审计报告记录的观测：len=2608 的英语 stem 原先 0.9 approved。
        """
        # 还原真实结构：非综合题被错切（is_composite=False）但 stem 含整段材料
        real_stem = (
            "People's views are becoming more and more divided, with 'echo chambers' — social "
            "media platforms where we see only what we agree with. " * 30
        )[:2608]
        q = _q(f"1. {real_stem}", is_composite=False)
        result = evaluate_quality([q])
        assert q.confidence < 0.8, f"2608 字符材料混入题必须 <0.8，实际 {q.confidence}"
        assert any("题干异常膨胀" in i for i in q.issues)

    def test_material_question_long_stem_not_flagged(self):
        """非综合材料题（历史 Q43 类）：题干含材料一/材料二（LLM 未标 shared 行号），
        1162 字符合法 → 不按 800 上限误伤。

        2026-08-25：历史东城 Q43 材料分析题（题干+材料一/二/三+子问 = 1162 字符）
        被 800 上限误标记为膨胀 → reviewing(low_confidence)。修复：材料标记 → 综合题上限。
        """
        stem = (
            "43．（11分）从和平共处五项原则到人类命运共同体理念\n"
            "材料一 构建人类命运共同体理念与和平共处五项原则一脉相承，都根植于"
            "亲仁善邻、讲信修睦、协和万邦的中华优秀传统文化。" * 3 + "\n"
            "材料二 中国援建非洲铁路，帮助沿线国家改善基础设施。" * 3 + "\n"
            "（1）根据材料一和材料二，谈谈你的理解。\n"
            "（2）从材料三的表格中任选两个成就，提炼一个主题并说明。"
        )[:1162]
        q = _q(stem, qtype="short_answer", with_answer=True)
        evaluate_quality([q])
        assert "题干异常膨胀" not in q.issues
        assert q.confidence >= 0.8, f"材料题不应降分，实际 conf={q.confidence}"

    def test_shared_material_independent_uses_composite_limit(self):
        """带 shared_material_line_ids 的独立题（v6.14 材料并入）按综合题上限计长。"""
        stem = ("材料" + "这是一段较长的共享材料文本。" * 60)[:1300]
        q = SlicedQuestion(
            question_number="1",
            question_type="short_answer",
            stem=stem,
            answer="答案",
            confidence=0.5,
            shared_material_line_ids=["P1L001", "P1L002"],
            is_composite=False,
        )
        evaluate_quality([q])
        assert "题干异常膨胀" not in q.issues

    def test_real_bloat_without_material_marker_still_flagged(self):
        """无材料标记的纯题干膨胀（语文 Q17 默写混入散文材料）仍被拦截。"""
        stem = '17.在横线处填写作品原句。\n（1）古诗词常借"月"表达情感。' + (
            "国就封，作为闯入者，自然招致徐国的反抗。伯禽在周王室支持下，"
            "率军讨伐徐国，古徐阁主体建筑7层，高" * 20
        )[:1840]
        q = _q(stem, qtype="short_answer", with_answer=True)
        evaluate_quality([q])
        assert any("题干异常膨胀" in i for i in q.issues)
        assert q.confidence < 0.8
