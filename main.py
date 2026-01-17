from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(
    title="Zolo License Server",
    version="1.0.0"
)

# In-memory storage (will reset on server restart)
licenses = {}


class ActivateRequest(BaseModel):
    code: str


@app.get("/")
def root():
    return {"service": "zolo-license-server", "status": "ok"}


@app.post("/admin/license/create")
def create_license(plan: str):
    code = str(uuid.uuid4())
    licenses[code] = {
        "plan": plan,
        "active": False
    }
    return {
        "code": code,
        "plan": plan,
        "active": False
    }


@app.post("/activate")
def activate(request: ActivateRequest):
    license_data = licenses.get(request.code)

    if license_data is None:
        return {"status": "INVALID"}

    if license_data["active"]:
        return {"status": "ALREADY_ACTIVE", "plan": license_data["plan"]}

    license_data["active"] = True
    return {
        "status": "ACTIVATED",
        "plan": license_data["plan"]
    }
