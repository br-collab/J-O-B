"""
session_store.py

Disk-based persistence for analysis results and resume bytes.
Survives Streamlit page navigation within the same app instance.
Uses a fixed slot per app instance — single-user tool, no auth needed.
"""

import json
import pickle
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent / "logs"
RESULT_PATH = STORE_DIR / "session_result.json"
RESUME_PATH = STORE_DIR / "session_resume.pkl"


def save_result(result: dict) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    # Strip non-serializable objects before saving
    safe = {k: v for k, v in result.items() if _is_json_safe(v)}
    RESULT_PATH.write_text(json.dumps(safe, ensure_ascii=True), encoding="utf-8")


def load_result() -> dict | None:
    if not RESULT_PATH.exists():
        return None
    try:
        return json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_resume(uploaded_file) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    RESUME_PATH.write_bytes(pickle.dumps({
        "name": uploaded_file.name,
        "data": data,
    }))


def load_resume():
    if not RESUME_PATH.exists():
        return None
    try:
        payload = pickle.loads(RESUME_PATH.read_bytes())
        from io import BytesIO

        class _RestoredFile:
            def __init__(self, name, data):
                self.name = name
                self.size = len(data)
                self._buf = BytesIO(data)
            def read(self): return self._buf.read()
            def seek(self, p): return self._buf.seek(p)

        return _RestoredFile(payload["name"], payload["data"])
    except Exception:
        return None


def clear_store() -> None:
    for p in (RESULT_PATH, RESUME_PATH):
        if p.exists():
            p.unlink()


def _is_json_safe(value) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
