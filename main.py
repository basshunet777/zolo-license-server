from fastapi import FastAPI
from pydantic import BaseModel
import re
import random
import string

app = FastAPI(title="Zolo License Server", version="1.0.0")


def generate_license_key(plan: str) -> str:
    random_part = "".join(
        random.choices(string.ascii_letters + string.digits, k=11)
    )
    return f"ZOLO-{plan}-{random_part}"


class ValidateRequest(BaseModel):
    code: str


@app.post("/admin/create/{plan}")
def create_license(plan: str):
    return {
        "code": generate_license_key(plan)
    }


@app.post("/validate")
def validate_license(req: ValidateRequest):
    """
    Validates license format: ZOLO-7D-XXXXXXXXXXX
    """
    pattern = r"^ZOLO-[A-Z0-9]+-[A-Za-z0-9]{11}$"

    if re.match(pattern, req.code):
        return {
            "valid": True,
            "plan": req.code.split("-")[1]
        }

    return {
        "valid": False
    }
