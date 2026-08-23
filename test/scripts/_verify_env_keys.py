#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("backend/.env"))

for k in ["PADDLEOCR_VL_TOKEN", "MIMO_API_KEY", "DEEPSEEK_API_KEY"]:
    v = os.environ.get(k, "")
    if v:
        print(f"{k}: OK ({v[:6]}...)")
    else:
        print(f"{k}: MISSING")
