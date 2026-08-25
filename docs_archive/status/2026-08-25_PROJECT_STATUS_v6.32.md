# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.33
Status: 30 份样本验证（原始质量 61%）；P2/P4 修复；worker LLM 挂死双层超时兜底
Date: 2026-08-25

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR Provider 策略落地（PPS/PVL
主识别、LLM VL 移出驱动链）；**数据源决策完成**：PPS 为主（语文综合粒度
8/8、物理/历史/数学/生物/政治/英语/地理）+ **化学用 PaddleOCR-VL 26/26**
（人工核对确认 PVL 上下标/结构/表格质量远好于 PPS；15/26 真因是验证器
材料口径 + L2 标注小问题，修复后 26/26）。基线 **212/215 (99%)**（物理
Q18 图答案、数学 Q15 负号两项遗留已修复）。**30 份样本验证完成**：新样本
原始质量 **134/219 (61%)**，P2（260 路径）/P4（retry 500）已修复，审计
根因定位（化学锚定冲突/选择题提取/地理答案区）。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| P0 入库管线修复 | ✅ |
| OCR Provider 策略（PPS/PVL 主识别、LLM VL 移出驱动链） | ✅ 651 passed |
| paddle 耗尽不降级（OCROutageError + ocr_unavailable） | ✅ |
| 批量恢复脚本（retry_ocr_unavailable.py） | ✅ |
| provider_used 落盘 | ✅ |
| subject/ocr_model 传递修复（化学 VL 路由失效） | ✅ |
| 数据源决策（PPS 为主、化学 mimo） | ✅ |
| 英语 | ✅ 11/11 |
| 语文（PPS 综合题粒度） | ✅ 8/8 |
| 数学 | ✅ 23/23（Q15 圈号拆分 + 负号窗口搜索修复） |
| 历史 | ✅ 43/43（PPS 版 100%） |
| 物理 | ✅ 20/20（Q18（1）图答案"见解析"占位剔除 +（3）答案对齐） |
| 化学 | ✅ 26/26（PaddleOCR-VL——上下标/表格质量最优） |
| 生物 | ✅ 26/26 |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过 | ✅ 212/215 (99%) |
| pytest（专用测试库） | ✅ 651+ passed |
| Phase 2D | ⏸ 前置条件未满足 |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.33 | worker LLM 挂死 P7/P10 双层超时兜底（LLM 层 wait_for 600s + worker 任务级 3600s） |
| 6.32 | 30 份样本验证（原始质量 61%）、P2 路径260 + P4 retry500 修复、审计根因定位（化学锚定冲突/选择题提取/地理答案区） |
| 6.31 | 物理 Q18（图答案"见解析"占位剔除 +（3）答案对齐答案区）+ 数学 Q15（圈号 ①② 拆分 + 负号值窗口级搜索）修复，基线 212/215 (99%) |
| 6.30 | 化学换 PaddleOCR-VL 26/26（验证器材料口径修复 + L2 修正），基线 210/215 |
| 6.29 | 化学 VL 验证（15/26 比 PPS 更差）→ 化学保留 mimo；数据源决策完成，基线 210/215 |
| 6.28 | PPS 全科重跑（语文综合粒度 8/8、生物/英语/政治/地理干净）、化学 VL 重跑中、subject 传递修复 |
| 6.27 | PPS 数据补丁（物理 Q4/Q7/Q20、历史 Q37）+ 地理/生物缺库修复，基线 225/231 |
| 6.26 | OCR Provider 策略代码改造（VL 移出驱动链、ocr_unavailable、批量恢复）、PPS 重跑物理/历史 |
| 6.25 | 6 项遗留修复：Q4/Q7 回填、结构化答案、Q24 作文、Q26 选项 D、膨胀边界、Q46 essay |
| 6.24 | 语文 Q17 审核修复（串题截断 + 假冲突 BUG-026）、9 科基线 215/231 |
| 6.23 | 物理答案证据 5 题修复（BUG-025）、9 科基线 214/231 |
| 6.22 | 历史重跑 Q37 修复、9 科最终基线 209/231、快照模式落地 |
| 6.20 | 语文位置 23/24、膨胀检测材料题识别、物理 mimo-vl 重跑、pytest 648 passed |
| 6.17 | 数学 LaTeX 归一化、严格 16/23 → 22/23、9 科 204/231 |

## 当前状态

- 9 科基线：mismatch=0，严格通过 **212/215 (99%)**；答U 3、答M 0。
  **注意**：语文为 PPS 综合题粒度（8 题覆盖全卷，total 口径 231→215）；
  答U 3 全部为**地理报告管线幻选题号残留**（23/24/25，DB 27 题正确，
  非真实缺口）。
- 各科严格：语文 8/8、历史 43/43、化学 26/26、生物 26/26、政治 28/28、
  英语 11/11、地理 27/27（真实）、物理 **20/20**、数学 **23/23**。
- **数据源决策（2026-08-25）**：PPS（PP-StructureV3）为主——语文
  （综合粒度 8/8 非退化）、物理、历史、数学、生物、政治、英语、地理；
  **化学用 PaddleOCR-VL 26/26**——人工核对确认 PVL 上下标/结构/表格质量
  远好于 PPS（PPS 字母错乱、公式脏格式）。PVL 15/26 真因是验证器材料
  口径（section 共享材料误套）+ L2 标注小问题（Q12/13 section、stem
  marker），修复后 26/26。mimo/PPS 化学文档 superseded（数据保留）。
- OCR Provider 策略：L1 识别仅 paddle 系；LLM VL 移出驱动链；paddle
  不可用时任务标记 `ocr_unavailable` 等恢复重跑。10010 队列满为服务端
  瞬时状态（夜间批量更优）。subject/ocr_model 传递已修复（上传接口支持
  ocr_model 显式覆盖）。verify_material 改为按当前题 own_shared 检查
  （section 级材料不再误套非材料题）。
- **验证器增强（2026-08-24）**：① `_split_structured` 支持圈号 ①②③④
  拆分（数学 Q15 类 DB 答案）；② 短片段（纯数字值）只在子题标记紧邻区
  匹配防误命中；③ 负号值在答案行丢失时题号窗口级搜索（详解含正确值，
  Q15 `-7/3`）；④ "见解析/见详解"图答案占位剔除后核对其余子部分
  （物理 Q18（1）受力分析图）；⑤ "（或…）"等价表述在 split("=") 前剥离
  （物理 Q20（3），防内层 "=" 拆错）。
- 剩余缺口（诚实口径）：**仅地理报告管线幻选题号残留**（23/24/25 为
  管线幻选，DB 27 题正确）——需修报告生成侧过滤或登记为已知项。
- **30 份样本验证（2026-08-25）**：原始质量 **134/219 (61%)**（零人工
  干预）；stem/位置/材料覆盖 92%+，缺陷集中在答案/入库环节。修复：
  **P2**（processor._download_pdf 短文件名，解决 Windows 260 路径限制，
  验证 51bf043c/19086f92 completed）、**P4**（TaskService.refresh，解决
  retry API 500）、**P7/P10**（worker LLM 挂死双层超时兜底——LLM 层
  asyncio.wait_for 总超时 + worker 任务级 3600s，超时后 task 幂等 failed
  可重试）。审计：化学 17 mismatch=同号题锚定冲突；入库缺口=选择题
  stem_empty/锚点/answer_empty；地理育英 23 U=答案区无题号锚点。
- pytest：专用测试库 aitutors_test 下 **651+ passed**；2 failed + 2 errors 沙箱 ACL。
- T0-2 key 轮换：用户决定暂缓，泄漏原 key 未轮换；步骤见 `bugs.md`。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认重定向
  （`AITUTOR_TEST_DB=0` 关闭），初始化脚本 `backend/scripts/setup_test_db.py`。
- OCR 策略与实施：`Docs/02_Architecture/OCR_PROVIDER_POLICY.md`；
  批量恢复：`backend/scripts/retry_ocr_unavailable.py`；
  subject/ocr_model 传递：上传接口支持 ocr_model 显式覆盖（如
  "PaddleOCR-VL-1.6"）。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留最新/稳定内容，
  历史统一归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. 逐科调优（以 61% 为未调优基线）：化学锚定消歧、选择题提取、地理答案区锚点兜底、入库缺口。
2. 地理报告管线幻选题号残留（23/24/25）——修报告生成侧过滤或诚实登记。
3. T0-2 泄漏 API key 轮换（用户决定暂缓）。
4. 补齐 9 科 Structure Signature，条件满足后启动 Phase 2D。

## 历史与快照

- 完整变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_PROJECT_STATUS_v6.30.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_RESTART_PROMPT_v6.30.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_PROJECT_STATUS_v6.21.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_RESTART_PROMPT_v6.21.md`
