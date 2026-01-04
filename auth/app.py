import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "db.json")

app = FastAPI()


# ---------- helpers ----------

def ensure_db_exists():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": [], "sessions": []}, f)


def load_db() -> Dict[str, Any]:
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db: Dict[str, Any]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


ensure_db_exists()


# ---------- models ----------

class User(BaseModel):
    email: str
    password: str


# ---------- routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sign_up")
def sign_up(user: User):
    db = load_db()

    if any(u["email"] == user.email for u in db["users"]):
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = {
        "id": len(db["users"]) + 1,
        "email": user.email,
        "password": user.password,
    }

    db["users"].append(new_user)
    save_db(db)

    return {"message": "user created"}


@app.post("/login")
def login(user: User):
    db = load_db()

    found_user = next(
        (
            u for u in db["users"]
            if u["email"] == user.email and u["password"] == user.password
        ),
        None,
    )

    if not found_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session = {
        "id": len(db["sessions"]) + 1,
        "user_id": found_user["id"],
    }

    db["sessions"].append(session)
    save_db(db)

    return {"message": "login successful"}
