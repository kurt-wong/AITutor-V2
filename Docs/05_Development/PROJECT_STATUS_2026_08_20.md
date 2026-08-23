# AI Tutor V2 — 项目状态更新

**更新时间**: 2026-08-20 02:00  
**更新人**: MiMo

---

## 1. 当前阶段

**Task 2.5: live_pp 门禁验收**

目标：三科（数学/英语/物理）通过 `--with-ocr --runs 2` 复现性验证 + 对抗性门禁。

---

## 2. 三科门禁状态

| 科目 | 复现性 | 质量门 | 状态 | 备注 |
|------|--------|--------|------|------|
| **数学** | ✅ PASS (0 diff) | ✅ | **通过** | golden 8/8=100% |
| **物理** | ✅ PASS (0 diff) | ✅ | **通过** | - |
| **英语** | ⚠️ run2=19 正确 | ✅ | **待结构门禁** | run1=28 错误（拆分综合题），run2=19 正确 |

### 英语详细分析

朝阳英语 PDF 正确结构：
- Q1-Q10: 完形填空 → 1 道综合题
- Q11-Q20: 语法填空 → 10 个独立句（无共享材料）
- Q21-Q30: 选词填空 → 1 道综合题
- Q31-Q44: 阅读理解 → 4 道综合题
- Q45-Q49: 七选五 → 1 道综合题
- Q50-Q53: 阅读表达 → 1 道综合题
- Q54: 书面表达 → 1 道独立题

**问题**：LLM 对综合题的判断不稳定（有时拆分，有时合并）。需要结构门禁校验。

---

## 3. 新科目状态

| 科目 | L1 fixture | golden draft | 复现性 | 备注 |
|------|------------|--------------|--------|------|
| **化学** | ✅ 304 行 | ⚠️ 6 题（stem 为空）| 1 diff | LLM 标注失败，需用验证结果 |
| **生物** | ✅ 327 行 | ⚠️ 10 题（stem 为空）| 1 diff | 同上 |
| **语文** | ✅ 415 行 | ✅ 15 题 | 4 diff | 结构基本正确 |

### 新科目结构

**化学**（八十中）：
- Q1-Q14: 单选题（附图/表格）
- Q15-Q20: 实验综合题（每题有若干 sub_questions）
- 答案区从 P10 开始

**生物**（大兴）：
- Q1-Q35: 选择题（Q1-Q20 每题1分，Q21-Q35 每题2分）
- Q36-Q39: 实验综合题（每题 4 个 sub_questions）
- Q40: 独立 short_answer

**语文**（朝阳）：
- Q1-Q7: 材料阅读（1 道综合题）
- Q8-Q13: 语言运用（1 道综合题）
- Q14-Q16: 文言文/古诗（2 道综合题）
- Q17: 默写
- Q18-Q21: 文学类/实用类阅读
- Q22: 语言基础运用（2 小问）
- Q23: 有三小文
- Q24: 写作（两个选题，一篇文章）

---

## 4. 结构门禁设计（codex 进行中）

### 门禁规则（不检查具体数量）

| 规则 | 说明 |
|------|------|
| answer_anchor_valid | 答案锚点非 missing/retry |
| reproducibility | 同 fixture 两轮结果一致 |
| composite_has_subs | 综合题有 sub_questions |
| composite_has_shared_material | 综合题有 shared_material_line_ids |
| independent_no_subs | 独立题无 sub_questions |
| valid_question_type | 题型是 canonical 枚举 |
| answer_format | 答案符合题型约束 |

### Golden 文件设计

```json
{
  "filename": "...",
  "l1_fixture_version": "l1_ppsv3_xxx_2026_v1",
  "questions": [
    {
      "question_number": "1",
      "question_type": "single_choice",
      "is_composite": false,
      "stem_line_ids": ["P1L001"],
      "options_line_ids": {"A": ["P1L002"], ...},
      "answer": "B",
      "answer_line_ids": ["P10L001"],
      "expected_content": {"stem": "...", "answer": "B"}
    }
  ]
}
```

---

## 5. 本轮代码修改汇总

### 核心修复

| 文件 | 修改 | 效果 |
|------|------|------|
| `answer_matcher.py` | V1_LESSONS 3.17：答案表优先 + 字母校验 | 英语选择题答案收敛 |
| `answer_matcher.py` | short_answer 从 solution_blocks 提取答案行 | 数学 Q21 收敛 |
| `answer_matcher.py` | `_NON_ANSWER_HEADER_RE` 增加 【导语】 | 过滤导言行 |
| `semantic_anchor.py` | 选择题 stem 用 first_option - 1 | 数学 Q7 收敛 |
| `semantic_anchor.py` | short_answer/fill_in stem 用 next_question - 1 | 物理 Q15/Q16 收敛 |
| `anchor_corrector.py` | 从 stem 移除选项行 | 防止 stem 包含选项 |
| `line_annotator.py` | Rule 7b/7c/8a（stem 边界 + 图注 + 最终结果行）| prompt 强化 |
| `line_annotator.py` | canonical 映射 reading/cloze/seven_to_five | 题型归一化 |
| `content_slicer.py` | 同步 canonical 映射 | - |
| `run_live_validation.py` | `_norm()` 标点归一化 + 题号前缀归一化 | Q15/Q21 格式差异 |
| `run_live_validation.py` | `_REPRO_TYPE_MAP` 同步 | - |
| `http.py` | 新增 `max_tokens` + `max_completion_tokens` 参数 | MIMO 截断修复 |
| `providers.py` | mimo-vl 用 mimo-v2.5（vision）| VL 路由修复 |
| `gateway.py` | mimo-v2.5-pro 时间段切换（9-12, 14-18）| LLM 成本优化 |

### 测试

- 367 passed, 1 warning
- 新增测试：fill_in 下一题边界、复合题共享材料、题号前缀归一化、选择题答案表优先

---

## 6. MIMO 配置

| 配置项 | 值 |
|--------|-----|
| MIMO_API_KEY | sk-cnolie3bj6swyssiji0dpuehvuop18csfqfph5a36hrxvpm0 |
| MIMO_BASE_URL | https://api.xiaomimimo.com/v1 |
| MIMO_MODEL | mimo-v2.5-pro（文本任务）|
| MIMO_VL_MODEL | mimo-v2.5（VL 多模态任务）|

**max_completion_tokens 修复**：
- MIMO 用 `max_completion_tokens`（不是 `max_tokens`）
- 默认值 131072，我们设 65536
- DeepSeek 保持 `max_tokens`（其 API 用这个参数名）

---

## 7. 待处理事项

### 高优先级
1. **英语结构门禁**：codex 正在设计 expected composite signature + 校验逻辑
2. **化学/生物 golden**：用验证结果（`chemistry_run1.json` 等）生成临时 golden
3. **三科完整门禁**：确认 Math/English/Physics 全部通过

### 中优先级
4. **MIMO 稳定性**：验证 MIMO 在完整文档上的表现
5. **化学/生物 prompt 优化**：LLM 标注 stem/options 为空
6. **语文复现性**：4 个差异需要定位

### 低优先级
7. **赵岩问题**：文档解析不一致（暂时搁置）
8. **其他科目**：历史、政治、地理的验证

---

## 8. 关键文件位置

| 文件 | 路径 |
|------|------|
| L1 fixtures | `test/results/l1_ppsv3_*.json` |
| Golden drafts | `test/results/*_2026_real_golden.json` |
| 验证结果 | `test/results/live_validation/*.json` |
| 验证脚本 | `test/scripts/run_live_validation.py` |
| Golden 生成脚本 | `test/scripts/build_subject_golden_drafts.py` |
| Prompt | `backend/app/domains/document/line_annotator.py` |
| 答案匹配 | `backend/app/domains/document/answer_matcher.py` |
| 语义锚点 | `backend/app/domains/document/semantic_anchor.py` |

---

## 9. 验证命令

```bash
# 三科门禁
python test/scripts/run_live_validation.py --with-ocr --runs 2 --subjects math,english,physics

# 单科验证
python test/scripts/run_live_validation.py --with-ocr --runs 2 --subjects chemistry

# 对抗性门禁
python test/scripts/adversarial_check_live_validation.py --require-live-pp

# 生成 L1 fixture（仅 OCR）
python test/scripts/build_subject_l1_fixtures.py

# 生成 golden draft
python test/scripts/build_subject_golden_drafts.py
```

---

## 10. 重启后待办

1. 检查 codex 完成的结构门禁设计
2. 用验证结果生成化学/生物临时 golden
3. 重新跑三科门禁确认通过
4. 处理英语综合题结构问题
