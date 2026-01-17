from fastapi import FastAPI
import random
import string

app = FastAPI(title="Zolo License Server", version="1.0.0")


def generate_license_key(plan: str) -> str:
    """
    Generates a license key like: ZOLO-7D-Lx9SnktWFdqO
    """
    random_part = "".join(
        random.choices(string.ascii_letters + string.digits, k=11)
    )
    return f"ZOLO-{plan}-{random_part}"


@app.post("/admin/create/{plan}")
def create_license(plan: str):
    code = generate_license_key(plan)
    return {
        "code": code
    }
