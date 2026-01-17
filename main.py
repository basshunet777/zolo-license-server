from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(title="Zolo License Server", version="1.0.0")

licenses = {}


class ActivateRequest(BaseModel):
    code: str


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/admin/create/{plan}")
def create_license(plan: str):
    code = f"ZOLO-{plan}-{uuid.uuid4().hex[:10]}"
    licenses[code] = {"plan": plan, "active": False}
    return {"code": code}


@app.post("/activate")
def activate(req: ActivateRequest):
    lic = licenses.get(req.code)

    if lic is None:
        return {"status": "INVALID"}

    if lic.get("active") is True:
        return {"status": "ALREADY_ACTIVE", "plan": lic["plan"]}

    lic["active"] = True
    return {"status": "ACTIVATED", "plan": lic["plan"]}
