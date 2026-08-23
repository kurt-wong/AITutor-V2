"""分析各科试卷题目特征，决定 OCR 路由。"""
import json, io
import re

REPORT = r"D:\Project\AITutors-v2\test\results\ocr_comparison\comparison_report.json"
with io.open(REPORT, encoding="utf-8") as f:
    report = json.load(f)

VALIDATION_DIR = r"D:\Project\AITutors-v2\test\results\composite_validation"

SUBJECT_FILES = {
    "化学": "2026北京八一学校高一（上）期末化学（教师版）",
    "生物": "2026北京北师大附中高一（上）期末生物（教师版）",
    "地理": "2026北京朝阳高一（上）期末地理（教师版）",
    "语文": "2026北京八十中高一（上）期末语文（教师版）",
    "数学": "2026北京二中高一（上）期末数学（教师版）",
    "英语": "2026北京东城高一（上）期末英语（教师版）",
    "物理": "2026北京丰台高一（上）期末物理（教师版）",
    "历史": "2025北京东城高一（上）期末历史（教师版）",
    "政治": "2026北京东城高一（上）期末政治（教师版）",
}

out = []

for entry in report:
    subj = entry["subject"]
    pps = entry["results"].get("PP-StructureV3", {})
    vl = entry["results"].get("PaddleOCR-VL", {})
    if pps.get("status") != "ok" or vl.get("status") != "ok":
        continue

    # 特征分析
    latex_ratio_pps = pps.get("latex_line_count", 0) / max(pps.get("total_lines", 1), 1)
    table_count = max(pps.get("table_line_count", 0), vl.get("table_line_count", 0))
    img_diff = pps.get("image_count", 0) - vl.get("image_count", 0)

    # 选项行差异
    opt_diff = vl.get("option_line_count", 0) - pps.get("option_line_count", 0)

    out.append(f"\n{'='*60}")
    out.append(f"{subj}")
    out.append(f"{'='*60}")
    out.append(f"  总行数: PPS={pps['total_lines']} VL={vl['total_lines']}")
    out.append(f"  公式行: PPS={pps['latex_line_count']} VL={vl['latex_line_count']} (占比{latex_ratio_pps:.1%})")
    out.append(f"  表格行: PPS={pps['table_line_count']} VL={vl['table_line_count']}")
    out.append(f"  选项行: PPS={pps['option_line_count']} VL={vl['option_line_count']} (差异{opt_diff:+d})")
    out.append(f"  图片数: PPS={pps['image_count']} VL={vl['image_count']} (差异{img_diff:+d})")
    out.append(f"  速度: PPS={pps['elapsed_s']}s VL={vl['elapsed_s']}s")

    # 读验证结果
    stem = SUBJECT_FILES.get(subj, "")
    vpath = f"{VALIDATION_DIR}/{stem}_run1.json"
    try:
        with io.open(vpath, encoding="utf-8") as f:
            vd = json.load(f)
        disc = vd.get("ingest_summary", {}).get("discarded", 0)
        total = vd.get("question_count", 0)
        rate = disc / max(total, 1)
        composites = vd.get("_composite_stats", {}).get("composite_count", 0)
        out.append(f"  验证(PPS): {total}题, {composites}综合, 丢弃{disc}({rate:.0%})")
    except:
        out.append(f"  验证: 无数据")

with io.open(r"D:\Project\AITutors-v2\test\results\_subject_analysis.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written OK")
