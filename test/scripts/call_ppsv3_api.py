"""Call PP-StructureV3 API to process test PDF and save results."""
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = os.environ.get("PADDLEOCR_VL_TOKEN", "")
if not TOKEN:
    raise SystemExit("PADDLEOCR_VL_TOKEN not found in backend/.env")
MODEL = "PP-StructureV3"

PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "pdf", "2026北京朝阳高一（上）期末数学（教师版）.pdf")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "ppsv3_output")

optional_payload = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}


def submit_job(file_path):
    headers = {"Authorization": "bearer " + TOKEN}
    data = {
        "model": MODEL,
        "optionalPayload": json.dumps(optional_payload),
    }
    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(JOB_URL, headers=headers, data=data, files=files)
    print("Submit status:", resp.status_code)
    if resp.status_code != 200:
        print("Error:", resp.text)
        sys.exit(1)
    job_id = resp.json()["data"]["jobId"]
    print("Job ID:", job_id)
    return job_id


def poll_job(job_id):
    headers = {"Authorization": "bearer " + TOKEN}
    while True:
        resp = requests.get(JOB_URL + "/" + job_id, headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        state = data["state"]
        if state == "pending":
            print("Status: pending")
        elif state == "running":
            prog = data.get("extractProgress", {})
            total = prog.get("totalPages", "?")
            done = prog.get("extractedPages", "?")
            print("Status: running (%s/%s pages)" % (done, total))
        elif state == "done":
            prog = data.get("extractProgress", {})
            print("Done! Pages:", prog.get("extractedPages"))
            return data["resultUrl"]["jsonUrl"]
        elif state == "failed":
            print("Failed:", data.get("errorMsg"))
            sys.exit(1)
        time.sleep(5)


def download_results(jsonl_url, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    resp = requests.get(jsonl_url)
    resp.raise_for_status()
    lines = resp.text.strip().split("\n")
    all_results = []
    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        for i, res in enumerate(result["layoutParsingResults"]):
            md_text = res["markdown"]["text"]
            md_filename = os.path.join(output_dir, "page_%d.md" % line_num)
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(md_text)
            print("Saved:", md_filename)
            all_results.append({
                "page_no": line_num,
                "markdown": md_text,
                "images": res["markdown"].get("images", {}),
            })
    return all_results


def main():
    pdf_path = os.path.abspath(PDF_PATH)
    if not os.path.exists(pdf_path):
        print("PDF not found:", pdf_path)
        sys.exit(1)
    print("Processing:", pdf_path)
    job_id = submit_job(pdf_path)
    jsonl_url = poll_job(job_id)
    results = download_results(jsonl_url, OUTPUT_DIR)
    combined_path = os.path.join(OUTPUT_DIR, "combined_results.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nCombined results saved to:", combined_path)


if __name__ == "__main__":
    main()
