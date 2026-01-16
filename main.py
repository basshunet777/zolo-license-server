import re, secrets
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

PLAN = re.compile(r"^(\\d+)(D|Y)$")
licenses = {}

def calc_expire(start, plan):
    n, t = PLAN.match(plan).groups()
    n = int(n)
    return start + (timedelta(days=n) if t == "D" else timedelta(days=365*n))

def gen_code(plan):
    return f"ZOLO-{plan}-" + secrets.token_urlsafe(8)

class ActivateReq(BaseModel):
    code: str

@app.post("/admin/create/{plan}")
def create(plan: str):
    code = gen_code(plan)
    licenses[code] = {
        "plan": plan,
        "activated": None,
        "expires": None
    }
    return {"code": code}

@app.post("/activate")
def activate(req: ActivateReq):
    lic = licenses.get(req.code)
    if not lic:
        return {"status": "INVALID"}

    now = datetime.now(timezone.utc)

    if lic["activated"] is None:
        lic["activated"] = now
        lic["expires"] = calc_expire(now, lic["plan"])

    if now > lic["expires"]:
        return {"status": "EXPIRED"}

    return {
        "status": "OK",
        "expires": lic["expires"]
    }
