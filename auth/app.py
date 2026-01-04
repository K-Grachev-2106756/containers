import os
import pymysql
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "db"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "auth_user"),
    "password": os.getenv("MYSQL_PASSWORD", "auth_pass"),
    "database": os.getenv("MYSQL_DB", "auth_db"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

app = FastAPI()


def get_conn():
    return pymysql.connect(**DB_CONFIG)


class User(BaseModel):
    email: str
    password: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sign_up")
def sign_up(user: User):
    conn = get_conn()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM users WHERE email = %s",
            (user.email,),
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")

        cur.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (user.email, user.password),
        )

    conn.close()
    return {"message": "user created"}


@app.post("/login")
def login(user: User):
    conn = get_conn()

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM users WHERE email = %s AND password = %s",
            (user.email, user.password),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        cur.execute(
            "INSERT INTO sessions (user_id) VALUES (%s)",
            (row["id"],),
        )

    conn.close()
    return {"message": "login successful"}
