import logging
import sys

# 2026-08-25：应用 logger 默认只输出 WARNING+（Python root logger 默认级别），
# 导致 worker 的 INFO 日志（"document_parse_worker started"、"worker: picked
# up task"）不可见，OCR 降级/任务进度无法实时监控。此处配置 root logger：
# INFO 级别输出到 stderr；若外部已配置 handler（如生产环境）则不动。
if not logging.getLogger().handlers:
    _root = logging.getLogger()
    _root.setLevel(logging.INFO)
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s: %(message)s")
    )
    _root.addHandler(_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
