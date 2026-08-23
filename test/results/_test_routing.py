"""验证学科路由逻辑。"""
import os, sys
sys.path.insert(0, r"D:\Project\AITutors-v2\backend")
from app.domains.document.simple_pipeline import (
    _extract_subject_from_filename,
    _ocr_model_for_subject,
    _SUBJECT_OCR_MODEL,
)

print(f"_SUBJECT_OCR_MODEL = {_SUBJECT_OCR_MODEL}")

fname = "2026北京八一学校高一（上）期末化学（教师版）.pdf"
subject = _extract_subject_from_filename(fname)
print(f"_extract_subject_from_filename({fname!r}) = {subject!r}")

model = _ocr_model_for_subject(subject)
print(f"_ocr_model_for_subject({subject!r}) = {model!r}")

# 检查是否有环境变量覆盖
env_override = os.environ.get("OCR_MODEL_OVERRIDE")
print(f"OCR_MODEL_OVERRIDE = {env_override!r}")
