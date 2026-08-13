# PaddleOCR-VL / PP-StructureV3 API 参考

Version: 1.1
Status: 项目资料
Date: 2026-08-11

---

## 1. 通用说明

- API：`https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`
- 认证：`Authorization: bearer <token>`
- 支持本地文件或文件 URL 两种提交模式。
- 提交后轮询任务状态，任务完成后下载 JSONL，并解析 `layoutParsingResults` 中的 Markdown 与图片。
- 密钥不写入本文档；示例统一从 `PADDLEOCR_VL_TOKEN` 环境变量读取。

---

## 2. PaddleOCR-VL-1.6 示例

```python
# pip install requests
import json
import os
import requests
import sys
import time

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = os.environ["PADDLEOCR_VL_TOKEN"]
MODEL = "PaddleOCR-VL-1.6"

file_path = "<local file path or file url>"

headers = {
    "Authorization": f"bearer {TOKEN}",
}

optional_payload = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}

print(f"Processing file: {file_path}")

if file_path.startswith("http"):
    headers["Content-Type"] = "application/json"
    payload = {
        "fileUrl": file_path,
        "model": MODEL,
        "optionalPayload": optional_payload,
    }
    job_response = requests.post(JOB_URL, json=payload, headers=headers)
else:
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    data = {
        "model": MODEL,
        "optionalPayload": json.dumps(optional_payload),
    }

    with open(file_path, "rb") as f:
        files = {"file": f}
        job_response = requests.post(JOB_URL, headers=headers, data=data, files=files)

print(f"Response status: {job_response.status_code}")
if job_response.status_code != 200:
    print(f"Response content: {job_response.text}")

assert job_response.status_code == 200
job_id = job_response.json()["data"]["jobId"]
print(f"Job submitted successfully. job id: {job_id}")
print("Start polling for results")

jsonl_url = ""
while True:
    job_result_response = requests.get(f"{JOB_URL}/{job_id}", headers=headers)
    assert job_result_response.status_code == 200
    state = job_result_response.json()["data"]["state"]
    if state == "pending":
        print("The current status of the job is pending")
    elif state == "running":
        try:
            total_pages = job_result_response.json()["data"]["extractProgress"]["totalPages"]
            extracted_pages = job_result_response.json()["data"]["extractProgress"]["extractedPages"]
            print(f"The current status of the job is running, total pages: {total_pages}, extracted pages: {extracted_pages}")
        except KeyError:
            print("The current status of the job is running...")
    elif state == "done":
        extracted_pages = job_result_response.json()["data"]["extractProgress"]["extractedPages"]
        start_time = job_result_response.json()["data"]["extractProgress"]["startTime"]
        end_time = job_result_response.json()["data"]["extractProgress"]["endTime"]
        print(f"Job completed, successfully extracted pages: {extracted_pages}, start time: {start_time}, end time: {end_time}")
        jsonl_url = job_result_response.json()["data"]["resultUrl"]["jsonUrl"]
        break
    elif state == "failed":
        error_msg = job_result_response.json()["data"]["errorMsg"]
        print(f"Job failed, failure reason: {error_msg}")
        sys.exit()

    time.sleep(5)

if jsonl_url:
    jsonl_response = requests.get(jsonl_url)
    jsonl_response.raise_for_status()
    lines = jsonl_response.text.strip().split("\n")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    page_num = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        result = json.loads(line)["result"]
        for res in result["layoutParsingResults"]:
            md_filename = os.path.join(output_dir, f"doc_{page_num}.md")
            with open(md_filename, "w", encoding="utf-8") as md_file:
                md_file.write(res["markdown"]["text"])
            print(f"Markdown document saved at {md_filename}")
            for img_path, img in res["markdown"]["images"].items():
                full_img_path = os.path.join(output_dir, img_path)
                os.makedirs(os.path.dirname(full_img_path), exist_ok=True)
                img_bytes = requests.get(img).content
                with open(full_img_path, "wb") as img_file:
                    img_file.write(img_bytes)
                print(f"Image saved to: {full_img_path}")
            for img_name, img in res["outputImages"].items():
                img_response = requests.get(img)
                if img_response.status_code == 200:
                    filename = os.path.join(output_dir, f"{img_name}_{page_num}.jpg")
                    with open(filename, "wb") as f:
                        f.write(img_response.content)
                    print(f"Image saved to: {filename}")
                else:
                    print(f"Failed to download image, status code: {img_response.status_code}")
            page_num += 1
```

---

## 3. PP-StructureV3 示例

与 PaddleOCR-VL 示例相同，仅将模型名改为：

```python
MODEL = "PP-StructureV3"
```

其余提交、轮询、JSONL 下载和图片保存流程一致。

---

## 4. 项目落地要求

- 后端必须通过专用 OCR/VL Client 接入，不直接在业务代码里散落 token。
- token 统一从 `backend/.env` 的 `PADDLEOCR_VL_TOKEN` 读取。
- 解析结果和图片应写入 `test/` 对应目录，用于字段级准确率基线。
- 已实现 `backend/app/domains/document/ocr/paddle_client.py`，`PaddleOCRClient.extract()` 完成文件提交、状态轮询、JSONL 下载与页面/图片解析。
- MIMO/Qwen VL 回退在 `backend/app/domains/document/ocr/providers.py` 中按 LLM Gateway 接入；未配置对应 base URL/model 时自动跳过。
