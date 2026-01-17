def gen_code(plan: str) -> str:
    parse_plan(plan)

    import string
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(12))

    return f"ZOLO-{plan}-{random_part}"
@app.post("/admin/license/create")
def create_license(plan: str):
    code = str(uuid.uuid4())
    licenses[code] = {
        "plan": plan,
        "active": False
    }
    return {"code": code}
