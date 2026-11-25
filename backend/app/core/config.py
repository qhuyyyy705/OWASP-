import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = ROOT.parent / "frontend" / "dist"
DB_PATH = Path(os.getenv("WEBSENTINEL_DB_PATH", str(ROOT / "websentinel.db"))).expanduser()
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
