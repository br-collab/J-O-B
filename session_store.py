"""
session_store.py

Disk-based persistence for analysis results and resume bytes.
Namespaced by Streamlit session ID — safe for multiple concurrent users.
Each user gets their own isolated slot. Old sessions auto-expire after 24 hours.
"""

import json
import pickle
import time
from pathlib import Path

STORE_DIR = Path(__file__).resolve().parent / "logs" / "sessions"
SESSION_TTL_SECONDS = 60 * 60 * 24  # 24 hours


def _get_session_id() -> str:
    """Get a stable session ID from Streamlit's runtime context."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            return ctx.session_id
    except Exception:
        pass
    try:
        import streamlit as st
        if "session_id" not in st.session_state:
            import uuid
            st.session_state["session_id"] = str(uuid.uuid4())
        return st.session_state["session_id"]
    except Exception:
        return "default"


def _session_dir() -> Path:
    sid = _get_session_id()
    d = STORE_DIR / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _result_path() -> Path:
    return _session_dir() / "result.json"


def _resume_path() -> Path:
    return _session_dir() / "resume.pkl"


def _touch_session() -> None:
    """Update session timestamp for TTL tracking."""
    ts = _session_dir() / ".last_access"
    ts.write_text(str(time.time()))


def _expire_old_sessions() -> None:
    """Remove session dirs older than TTL. Runs opportunistically."""
    if not STORE_DIR.exists():
        return
    now = time.time()
    for session_dir in STORE_DIR.iterdir():
        if not session_dir.is_dir():
            continue
        ts_file = session_dir / ".last_access"
        try:
            last = float(ts_file.read_text()) if ts_file.exists() else session_dir.stat().st_mtime
            if now - last > SESSION_TTL_SECONDS:
                for f in session_dir.iterdir():
                    f.unlink(missing_ok=True)
                session_dir.rmdir()
        except Exception:
            pass


def save_result(result: dict) -> None:
    _touch_session()
    _expire_old_sessions()
    safe = {k: v for k, v in result.items() if _is_json_safe(v)}
    _result_path().write_text(json.dumps(safe, ensure_ascii=True), encoding="utf-8")


def load_result() -> dict | None:
    p = _result_path()
    if not p.exists():
        return None
    try:
        _touch_session()
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_resume(uploaded_file) -> None:
    _touch_session()
    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    _resume_path().write_bytes(pickle.dumps({
        "name": uploaded_file.name,
        "data": data,
    }))


def load_resume():
    p = _resume_path()
    if not p.exists():
        return None
    try:
        _touch_session()
        payload = pickle.loads(p.read_bytes())
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
    for p in (_result_path(), _resume_path()):
        if p.exists():
            p.unlink(missing_ok=True)


def _is_json_safe(value) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False

