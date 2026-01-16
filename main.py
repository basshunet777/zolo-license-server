import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field

app = FastAPI(title="ZOLO License Server")

PLAN = re.compile(r"^(\d+)(D|Y)$")

# ====== CONFIG (Render env vars) ======
ADMIN_KEY = os.getenv("ADMIN_KEY", "")  # set this in Render env vars
DB_PATH = os.getenv("DB_PATH", "/data/licenses.db")  # persistent disk: /data
ALLOW_MULTI_DEVICE = os.getenv("ALLOW_MULTI_DEVICE", "0") == "1"

# ====== DB helpers ======
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            code TEXT PRIMARY KEY,
            plan TEXT NOT NULL,
            created_at TEXT NOT NULL,
            activated_at TEXT,
            expires_at TEXT,
            revoked INTEGER NOT NULL DEFAULT 0,
            device_id TEXT
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON licenses(expires_at)")
        conn.commit()

@app.on_event("startup")
def on_startup():
    init_db()

# ====== core logic ======
def require_admin(x_admin_key: Optional[str]):
    if not ADMIN_KEY:
        # Safer: fail closed if not configured
        raise HTTPException(status_code=500, detail="ADMIN_KEY is not set on server")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def parse_plan(plan: str) -> tuple[int, str]:
    m = PLAN.match(plan)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid plan. Use like 30D or 1Y")
    n = int(m.group(1))
    t = m.group(2)
    if n <= 0 or n > 3650:
        raise HTTPException(status_code=400, detail="Plan duration out of range")
    return n, t

def calc_expire(start: datetime, plan: str) -> datetime:
    n, t = parse_plan(plan)
    # Note: Year = 365 days (simple). If you want calendar years, we can switch to relativedelta.
    return start + (timedelta(days=n) if t == "D" else timedelta(days=365 * n))

def gen_code(plan: str) -> str:
    # Validate plan first
    parse_plan(plan)
    return f"ZOLO-{plan}-" + secrets.token_urlsafe(8)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None

def from_iso(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None

# ====== API models ======
class ActivateReq(BaseModel):
    code: str = Field(..., min_length=5)
    device_id: Optional[str] = Field(default=None, max_length=128)

class CreateResp(BaseModel):
    code: str

# ====== ROUTES ======

@app.get("/")
def root():
    return {"ok": True, "service": "zolo-license-server"}

@app.get("/health")
def health():
    return {"status": "UP"}

@app.post("/admin/create/{plan}", response_model=CreateResp)
def create(plan: str, x_admin_key: Optional[str] = Header(default=None)):
    require_admin(x_admin_key)
    code = gen_code(plan)
    created = now_utc().isoformat()
    with db() as conn:
        conn.execute(
            "INSERT INTO licenses(code, plan, created_at) VALUES(?, ?, ?)",
            (code, plan, created),
        )
        conn.commit()
    return {"code": code}

@app.get("/admin/licenses")
def list_licenses(x_admin_key: Optional[str] = Header(default=None)):
    require_admin(x_admin_key)
    with db() as conn:
        rows = conn.execute(
            "SELECT code, plan, created_at, activated_at, expires_at, revoked, device_id FROM licenses ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

@app.post("/admin/revoke/{code}")
def revoke(code: str, x_admin_key: Optional[str] = Header(default=None)):
    require_admin(x_admin_key)
    with db() as conn:
        cur = conn.execute("UPDATE licenses SET revoked=1 WHERE code=?", (code,))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Code not found")
    return {"status": "REVOKED"}

@app.post("/activate")
def activate(req: ActivateReq):
    now = now_utc()

    with db() as conn:
        row = conn.execute(
            "SELECT code, plan, activated_at, expires_at, revoked, device_id FROM licenses WHERE code=?",
            (req.code,),
        ).fetchone()

        if not row:
            return {"status": "INVALID"}

        if row["revoked"] == 1:
            return {"status": "REVOKED"}

        activated_at = from_iso(row["activated_at"])
        expires_at = from_iso(row["expires_at"])
        saved_device = row["device_id"]

        # First activation
        if activated_at is None:
            activated_at = now
            expires_at = calc_expire(now, row["plan"])

            conn.execute(
                "UPDATE licenses SET activated_at=?, expires_at=?, device_id=? WHERE code=?",
                (iso(activated_at), iso(expires_at), req.device_id, req.code),
            )
            conn.commit()
            saved_device = req.device_id

        # Device binding check (if device_id provided)
        if req.device_id and saved_device and (req.device_id != saved_device) and not ALLOW_MULTI_DEVICE:
            return {"status": "DEVICE_MISMATCH"}

        if expires_at and now > expires_at:
            return {"status": "EXPIRED", "expires": iso(expires_at)}

        return {"status": "OK", "expires": iso(expires_at), "activated": iso(activated_at)}
