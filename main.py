from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(
    title="Zolo License Server",
    version="0.1.0"
)

# Vaqtinchalik storage (RAM)
licenses = {}


# --------- MODELS ---------
class ActivateReq(BaseModel):
    code: str


# --------- ENDPOINTS ---------

@app.get("/")
def root():
    return {"service": "zolo-license-server", "status": "ok"}


@app.post("/admin/license/create")
def create_license(plan: str):
    """
    Admin license yaratadi
    """
    code = str(uuid.uuid4())
    licenses[code] = {
        "plan": plan,
        "active": False
    }
    return {
        "code": code,
        "plan": plan
    }


@app.post("/activate")
def activate(req: ActivateReq):
    """
    License activate qilish
    """
    lic = licenses.get(req.code)

    if not lic:
        return {"status": "INVALID"}

    if lic["active"]:
        return {"status": "ALREADY_ACTIVE"}

    lic["active"] = True
    return {
        "status": "ACTIVATED",
        "plan": lic["plan"]
    }
