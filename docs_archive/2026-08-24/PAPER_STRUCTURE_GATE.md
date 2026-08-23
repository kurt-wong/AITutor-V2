# Paper Structure Gate

## 1. 目的

`run_live_validation.py` 原先只验证复现性和答案质量，无法发现“两次运行都稳定，但综合题分组错误”的问题。Paper Structure Gate 将每份真实试卷的预期分组固化为 manifest，并对每次 live run 做严格结构校验。

## 2. Manifest 位置

```text
test/annotations/structure/
  math_2026_chaoyang.paper_structure.json
  physics_2026_chaoyang.paper_structure.json
  english_2026_chaoyang.paper_structure.json
  english_2026_dongcheng.paper_structure.json
```

`test/scripts/paper_structure.py` 中的 `PAPER_STRUCTURES` 将 subject 映射到对应 manifest。

## 3. Schema

顶层字段：

```json
{
  "schema_version": 1,
  "subject": "english",
  "source_file": "2026北京朝阳高一（上）期末英语（教师版）.pdf",
  "bottom_question_numbers": ["1", "2", "...", "54"],
  "groups": []
}
```

`groups[]` 的每个元素：

```json
{
  "question_number": "1",
  "kind": "composite",
  "question_types": ["cloze", "fill_in"],
  "sub_questions": ["1", "2", "3"],
  "shared_material": "required",
  "sub_question_numbering": "absolute"
}
```

字段说明：

- `kind`：`composite` 表示共享材料综合题，`independent` 表示独立题。
- `question_types`：允许的 canonical 题型别名；LLM 输出落在这个集合内即可。
- `sub_questions`：综合题的子题号。独立题为 `[]`。
- `shared_material`：`composite` 必须为 `required`，`independent` 必须为 `forbidden`。
- `sub_question_numbering`：默认 `absolute`。物理等试卷的子题号是相对母题的 `（1）（2）` 时，使用 `relative`，此时底层题号由 `母题号 + 子题号` 组成，例如 `15（1）`。

## 4. 校验规则

校验器 `validate_paper_structure(run_result, manifest)` 对每次 run 独立执行：

1. 顶层题号必须与 manifest 的 groups 一一对应，不能缺题、多题、重复。
2. `is_composite` 必须与 `kind` 一致。
3. 综合题的 `sub_questions` 必须与 manifest 完全一致，包括顺序。
4. 综合题必须有非空 `shared_material_line_ids`；独立题必须为空。
5. `bottom_question_numbers` 必须被所有顶层独立题和综合题子题完全覆盖，不能缺、多、重叠。
6. `question_type` 必须落在 `question_types` 允许集合内。

该门禁不做“子集/超集容差”。LLM 分组漂移、漏题、误合并都会被判 FAIL。

## 5. 接入位置

- `test/scripts/run_live_validation.py`：live 运行后对每个 run 执行校验，结果写入 `report["paper_structure"]`；任一 run 无效会进入 `report["failures"]` 并使 `overall=FAIL`。
- `test/scripts/adversarial_check_live_validation.py`：独立读取 run JSON 和 manifest 重新计算，避免只信任 report。
- `backend/tests/test_paper_structure_gate.py`：覆盖朝阳英语、东城英语、物理、数学缺题、错误合并、缺失共享材料、report 门禁失败等场景。

## 6. 新增试卷

1. 人工确认 PDF 的分节和题目关系，确定每个顶层综合题/独立题。
2. 在 `test/annotations/structure/` 新建 manifest。
3. 在 `paper_structure.PAPER_STRUCTURES` 增加映射。
4. 用真实 run JSON 验证通过，并补一条回归测试。

注意：不同试卷必须使用自己的 manifest。朝阳英语的语法填空是 10 道独立题，东城英语的语法填空按 A/B/C 材料合并为 3 道综合题；这些差异由 manifest 表达，不应硬编码到解析 prompt。
