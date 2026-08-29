# OCR Provider 策略（PPS/PVL 主识别 + LLM VL 移出驱动链）

Version: 1.0
Status: 决策已定，实施计划待执行
Date: 2026-08-25

---

## 1. 决策背景与动机

用户（项目所有者，个人题库系统）决定调整 OCR 提供方策略：

1. **质量第一**：题库在孩子使用前必须全部管线跑通、提前准备好；批量入库可在
   夜间空闲时段运行，**非限时任务**，质量优先于速度。
2. **成本**：Paddle 系产品（PPS / PaddleOCR-VL）每天各有 3000 页免费识别额度；
   LLM 调用（mimo/deepseek）按量计费，夜间无人值守批量时烧 LLM 不划算。
3. **结果可控**：实测 mimo-vl 在文档版面结构化上有系统性弱点——幻觉标题
   （"滑沙项目受力与运动分析"）、漏选项（历史 Q26 选项 D）、漏题干（物理
   Q4/Q7）、答案表空单元格等。PPS/PVL 是专用版面解析，对教师版数字 PDF
   （题库真实形态）是主场。
4. **无人值守安全**：半夜 paddle 服务中断时全部 fallback 到 LLM 完成 OCR，
   从结果和成本角度均不划算。

## 2. 决策结论（强制规则）

```
L1（原始 PDF → 结构化文本）：
  - 主识别：仅 PPS（PP-StructureV3）/ PVL（PaddleOCR-VL-1.6，学科路由）
  - 证据补充：native-markdown（PyMuPDF 提取）——同页同行证据 + PP 空行兜底
  - 禁止：LLM VL（mimo-vl / deepseek-vl）作为 L1 识别工具或入库驱动

LLM VL（mimo-vl / deepseek-vl）：
  - 移出 OCR 驱动链（不再出现在 OCRFallbackChain 的自动降级路径）
  - 仅保留为可选交叉验证/复核入口（默认关闭；以确定性规则门为主）
  - 交叉验证定位：题号序列断档、选项数不足、题干为空、答案表空单元格等
    结构异常信号——这些信号用确定性规则即可抓（e2e 语义验收已覆盖），
    LLM 复核只是低频人工触发时的辅助。

paddle 不可用（401/10010/网络错误）：
  - 保留现有重试 + 熔断（瞬时容错）
  - 重试/熔断耗尽后：任务失败并标记 `ocr_unavailable`，等待 paddle 恢复
    后重跑；**不自动降级 LLM VL 驱动入库**
```

## 3. 职责边界（与 L2 的区分）

| 层 | 工具 | 职责 |
|---|---|---|
| L1 | 仅 PPS / PaddleOCR-VL | 版面结构化、数据化、文本提取（OCR-markdown） |
| L1 证据 | native-markdown | 同页同行证据、PP 空行兜底（不覆盖 PP 内容） |
| L2 | LLM（deepseek 主 / mimo 备） | 题目识别、语义/结构理解、行号标注（LLM-annotated） |
| LLM VL | ❌ 不作为 OCR | 不做 L1 文本提取，不做入库驱动 |

术语澄清：`llm_annotated_markdown`（L2 标注输出，JSON 行号数据）不是 L1 文本源；
L1 的正文源是 `ocr_markdown`（PPS/PVL），`native_markdown` 是证据/兜底。
simple_pipeline 的 `_build_pp_canonical` 已实现该原则（PP 非空保留 PP、PP 空行
用 native 兜底、不逐行仲裁、不覆盖 PP 已有内容）。

## 4. 10010 根因调查结论（2026-08-25）

### 4.1 官方定义（异步 API 使用文档，2026-02-04 版）

错误码表明确列出：

| 错误码 | 说明 | HTTP | 解决建议 |
|---|---|---|---|
| 10010 | **任务提交队列已满** | 400 | 请稍后重试 |
| 12001 | 已达每日页数上限（配额） | 403 | 提升配额 |
| 12002 | 请求频率过高 | 429 | 请稍后重试 |
| 401 | Token 无效 | 401 | 检查 token |

### 4.2 结论

- **10010 是官方异步 API 错误码**，语义为"任务提交队列已满"——服务端任务
  提交队列（pending 队列）容量已满，新任务提交被拒绝。
- 与配额（12001 每日页数上限）、频率（12002）明确区分：10010 是**并发队列
  状态**，非认证、非配额、非频率问题。
- 官方未公开队列容量与恢复时间，唯一建议是"请稍后重试"。
- 任务状态机：提交后 `pending`（排队中）→ `running`（解析中）→ `done`/`failed`。
- 实测（2026-08-25，新 token）：连续多次提交均返回 10010，间隔 30s 未恢复；
  提示队列满可能是持续状态（免费层共享队列高峰期满载），夜间低谷相对空闲。
- **代码注释勘误**：`paddle_client.py` 注释"官方错误码表无 10010"不准确——
  异步 API 使用文档错误码表明确列出 10010。

### 4.3 对本项目的影响

- 夜间批量入库策略与平台负载天然匹配（低谷期队列空闲概率高）。
- 熔断/重试逻辑保留但**耗尽后不再降级 LLM VL**；标记 `ocr_unavailable` 等
  paddle 恢复后重跑。
- token 已更新（`backend/.env`，gitignore 不入库），401 已消除。

## 5. 实施计划

| # | 项 | 状态 |
|---|---|---|
| 1 | `OCRFallbackChain` 改造：paddle 失败 → 重试+熔断 → 耗尽后抛 `OCROutageError`，任务失败标记 `ocr_unavailable`，不降级 mimo/deepseek | ✅ 2026-08-25 完成 |
| 2 | LLM VL 移出驱动链：`build_ocr_chain` 不再包含 mimo-vl/deepseek-vl；保留 provider 实现为可选复核入口（默认关） | ✅ 2026-08-25 完成 |
| 3 | 批量任务恢复：worker 每轮自动调用 `recover_stale_running_tasks` 恢复僵尸任务；`ocr_unavailable` 标记的失败任务可手动重试 | ✅ 2026-08-25 完成 |
| 4 | 规则文档：本文件 + `rules.md` §11 + `PIPELINE.md`/`PADDLEOCR_API.md` 同步 | ✅ 2026-08-25 完成 |
| 5 | 测试：降级路径测试改造 + 新增"paddle 耗尽不降级"用例 | ✅ 2026-08-25 完成 |

配套：`app/core/logging.py` 配置 root logger INFO 输出（worker 日志可见，
OCR 降级/任务进度可实时监控）；`processor.py` 失败任务 error_detail 优先取
`result.errors`（含 `ocr_unavailable` 标记，供批量恢复脚本识别）。

## 6. 历史数据重跑计划

- 范围：paddle 401 期间用 mimo-vl 灌入的文档（物理八十中、历史东城等）。
- 时机：paddle 恢复后（实测可提交成功后）**下午 14:00 批量重跑**。
- 目的：以 PPS/PVL 主识别结果为准，对比 mimo 灌入效果（作为后续质量对照）。
- 注意：重跑会产生新文档版本，DB 基线以重跑后为准；此前基于 mimo 数据修复的
  题（Q4/Q7 回填、Q26 选项 D 等）将接受主识别结果印证或修正。

## 7. 相关文档

- API 参考与错误码：`Docs/02_Architecture/PADDLEOCR_API.md`
- 管线架构：`Docs/02_Architecture/PIPELINE.md`
- 强制规则：`rules.md`（§OCR 识别链）
- 实现：`backend/app/domains/document/ocr/providers.py`、
  `backend/app/domains/document/ocr/paddle_client.py`、
  `backend/app/domains/document/simple_pipeline.py`
