#!/usr/bin/env python3
"""Validate technical documentation against implemented backend code."""

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.main import app as fastapi_app  # noqa: E402
from app.models import Base  # noqa: E402


def load_env_values() -> set[str]:
    secrets = set()
    for env_path in (ROOT / ".env", BACKEND / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if not key or not value:
                continue
            if any(
                marker in key.upper()
                for marker in ("API_KEY", "TOKEN", "SECRET", "PASSWORD")
            ) and value not in {"", "change-me"}:
                secrets.add(value.strip())
    return secrets


def check_dsd_tables() -> list[str]:
    dsd = (ROOT / "Docs" / "03_Data" / "DSD.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^###\s+\d+\.\d+\s+([a-z_]+)\s*$", dsd, re.MULTILINE))
    implemented = set(Base.metadata.tables)
    errors = []
    for table in sorted(implemented - documented):
        errors.append(f"table in code but missing from DSD: {table}")
    for table in sorted(documented - implemented):
        errors.append(f"table in DSD but missing from code: {table}")
    return errors


def check_acs_routes() -> list[str]:
    acs = (ROOT / "Docs" / "02_Architecture" / "ACS.md").read_text(encoding="utf-8")
    documented = set()
    for line in acs.splitlines():
        match = re.match(r"^####\s+(GET|POST|PUT|DELETE)\s+(/api/\S+)\s*$", line.strip())
        if match:
            documented.add((match.group(1), match.group(2).rstrip("/")))

    implemented = set()
    for route in fastapi_app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/"):
            continue
        for method in getattr(route, "methods", set()):
            if method in {"GET", "POST", "PUT", "DELETE"}:
                implemented.add((method, path.rstrip("/")))

    errors = []
    for method, path in sorted(implemented - documented):
        errors.append(f"route in code but missing from ACS: {method} {path}")
    return errors


def check_secrets_in_docs() -> list[str]:
    secrets = load_env_values()
    if not secrets:
        return []
    errors = []
    for doc in (ROOT / "Docs").rglob("*.md"):
        if "ARCHIVE" in doc.parts:
            continue
        content = doc.read_text(encoding="utf-8")
        for secret in secrets:
            if secret in content:
                errors.append(f"secret value found in {doc.relative_to(ROOT)}")
    return errors


def main() -> int:
    errors = []
    errors.extend(check_dsd_tables())
    errors.extend(check_acs_routes())
    errors.extend(check_secrets_in_docs())

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("validate_docs_vs_code: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
