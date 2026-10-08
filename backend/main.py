"""Todo list backend: FastAPI + SQLite or Postgres."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from fastapi.middleware.cors import CORSMiddleware
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - handled at runtime when DATABASE_URL is set
    psycopg = None
    dict_row = None

# The database file sits next to this script, wherever you start the server from.
# (TODO_DB can override the location; the tests use that.)
DB_FILE = os.environ.get("TODO_DB", str(Path(__file__).with_name("todos.db")))
VALID_STATUSES = {"todo", "in_progress", "done"}
app = FastAPI(title="Todo API")

# allow your frontend domains to talk to this backend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_database_url() -> str | None:
    return os.environ.get("DATABASE_URL")


def is_postgres_enabled() -> bool:
    return bool(get_database_url())


@contextmanager
def db():
    """Open a database connection, save changes, and always close it."""
    database_url = get_database_url()
    if database_url:
        if psycopg is None:
            raise RuntimeError("psycopg is required when DATABASE_URL is set")
        conn = psycopg.connect(database_url, autocommit=False)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us read rows like dictionaries
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def db_placeholder_count(count: int) -> str:
    if is_postgres_enabled():
        return ", ".join("%s" for _ in range(count))
    return ", ".join("?" for _ in range(count))


def fetch_all(conn, query: str, params=()):
    if is_postgres_enabled():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchall()
    return conn.execute(query, params).fetchall()


def fetch_one(conn, query: str, params=()):
    if is_postgres_enabled():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return cur.fetchone()
    return conn.execute(query, params).fetchone()


def insert_one(conn, query: str, params=()):
    if is_postgres_enabled():
        with conn.cursor() as cur:
            cur.execute(query + " RETURNING id", params)
            return cur.fetchone()[0]
    cur = conn.execute(query, params)
    return cur.lastrowid


# Create the table the first time the app starts.
with db() as conn:
    if is_postgres_enabled():
        with conn.cursor() as cur:
            cur.execute(
                """CREATE TABLE IF NOT EXISTS todos (
                    id       SERIAL PRIMARY KEY,
                    text     TEXT NOT NULL,
                    done     BOOLEAN NOT NULL DEFAULT FALSE,
                    status   TEXT NOT NULL DEFAULT 'todo',
                    progress INTEGER NOT NULL DEFAULT 0,
                    position INTEGER NOT NULL
                )"""
            )
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'todos'"
            )
            columns = {row[0] for row in cur.fetchall()}
            if "status" not in columns:
                cur.execute("ALTER TABLE todos ADD COLUMN status TEXT NOT NULL DEFAULT 'todo'")
            if "progress" not in columns:
                cur.execute("ALTER TABLE todos ADD COLUMN progress INTEGER NOT NULL DEFAULT 0")
            cur.execute(
                """
                UPDATE todos
                SET status = CASE
                    WHEN status IN ('todo', 'in_progress', 'done') THEN status
                    WHEN done = TRUE THEN 'done'
                    ELSE 'todo'
                END,
                progress = CASE
                    WHEN progress IS NULL THEN 0
                    ELSE progress
                END
                """
            )
    else:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS todos (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                text     TEXT    NOT NULL,
                done     INTEGER NOT NULL DEFAULT 0,
                status   TEXT    NOT NULL DEFAULT 'todo',
                progress INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL  -- smaller number = higher in the list
            )"""
        )
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(todos)").fetchall()}
        if "status" not in existing:
            conn.execute("ALTER TABLE todos ADD COLUMN status TEXT NOT NULL DEFAULT 'todo'")
        if "progress" not in existing:
            conn.execute("ALTER TABLE todos ADD COLUMN progress INTEGER NOT NULL DEFAULT 0")
        conn.execute(
            """
            UPDATE todos
            SET status = CASE
                WHEN status IN ('todo', 'in_progress', 'done') THEN status
                WHEN done = 1 THEN 'done'
                ELSE 'todo'
            END,
            progress = CASE
                WHEN progress IS NULL THEN 0
                ELSE progress
            END
            """
        )


# --- Shapes of the data the API accepts -----------------------------------
class NewTodo(BaseModel):
    text: str = Field(max_length=200)


class TodoUpdate(BaseModel):
    text: str | None = Field(default=None, max_length=200)
    done: bool | None = None
    status: Literal["todo", "in_progress", "done"] | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class NewOrder(BaseModel):
    ids: list[int]  # todo ids in the order they should appear
    status: Literal["todo", "in_progress", "done"] | None = None


def to_dict(row):
    status = row["status"] if "status" in row.keys() else ("done" if bool(row["done"]) else "todo")
    progress = int(row["progress"]) if "progress" in row.keys() else 0
    return {"id": row["id"], "text": row["text"], "done": status == "done", "status": status, "progress": progress}


# --- Endpoints ------------------------------------------------------------
@app.get("/api/todos")
def list_todos():
    with db() as conn:
        rows = fetch_all(conn, "SELECT * FROM todos ORDER BY position")
    return [to_dict(r) for r in rows]


@app.post("/api/todos", status_code=201)
def add_todo(body: NewTodo):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")
    with db() as conn:
        if is_postgres_enabled():
            last = fetch_one(conn, "SELECT COALESCE(MAX(position), 0) AS position FROM todos")["position"]
            new_id = insert_one(
                conn,
                "INSERT INTO todos (text, status, done, progress, position) VALUES (%s, %s, FALSE, 0, %s)",
                (text, "todo", last + 1),
            )
            row = fetch_one(conn, "SELECT * FROM todos WHERE id = %s", (new_id,))
        else:
            last = conn.execute("SELECT COALESCE(MAX(position), 0) FROM todos").fetchone()[0]
            cur = conn.execute(
                "INSERT INTO todos (text, status, done, progress, position) VALUES (?, ?, 0, 0, ?)",
                (text, "todo", last + 1),
            )
            row = conn.execute("SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)).fetchone()
    return to_dict(row)


# NOTE: "order" routes must come before "/api/todos/{todo_id}" so "order" isn't read as an id.
@app.put("/api/todos/order")
def reorder(body: NewOrder):
    """Rearrange the given todos in their current status list.

    Reusing the existing position values keeps items in other tabs fixed in place.
    """
    ids = body.ids
    if len(set(ids)) != len(ids):
        raise HTTPException(400, "Duplicate ids")
    if not ids:
        return {"ok": True}
    if is_postgres_enabled():
        marks = db_placeholder_count(len(ids))
        if body.status is not None:
            query = f"SELECT position FROM todos WHERE status = %s AND id IN ({marks}) ORDER BY position"
            params = [body.status, *ids]
        else:
            query = f"SELECT position FROM todos WHERE id IN ({marks}) ORDER BY position"
            params = list(ids)
    else:
        marks = ",".join("?" * len(ids))
        if body.status is not None:
            query = f"SELECT position FROM todos WHERE status = ? AND id IN ({marks}) ORDER BY position"
            params = [body.status, *ids]
        else:
            query = f"SELECT position FROM todos WHERE id IN ({marks}) ORDER BY position"
            params = ids

    with db() as conn:
        rows = fetch_all(conn, query, params)
        if len(rows) != len(ids):
            raise HTTPException(404, "Unknown todo id")
        for row, todo_id in zip(rows, ids):
            if is_postgres_enabled():
                conn.execute("UPDATE todos SET position = %s WHERE id = %s", (row["position"], todo_id))
            else:
                conn.execute("UPDATE todos SET position = ? WHERE id = ?", (row["position"], todo_id))
    return {"ok": True}


@app.delete("/api/todos", status_code=204)
def clear_done():
    """Delete every finished todo (the 'Clear all' button on the Done tab)."""
    with db() as conn:
        if is_postgres_enabled():
            conn.execute("DELETE FROM todos WHERE status = 'done'")
        else:
            conn.execute("DELETE FROM todos WHERE status = 'done'")


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    with db() as conn:
        row = fetch_one(conn, "SELECT * FROM todos WHERE id = %s", (todo_id,)) if is_postgres_enabled() else conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Todo not found")

        text = row["text"] if body.text is None else body.text.strip()
        if not text:
            raise HTTPException(400, "Text cannot be empty")

        status = body.status if body.status is not None else row["status"]
        progress = int(row["progress"]) if "progress" in row.keys() else 0
        if body.progress is not None:
            progress = body.progress
            if progress >= 100:
                status = "done"
            elif progress > 0:
                status = "in_progress"
            else:
                status = "todo"
        if body.done is not None:
            status = "done" if body.done else "todo"
        if status == "todo":
            progress = 0
        elif status == "done":
            progress = 100
        elif status == "in_progress" and body.status is not None and body.progress is None and progress == 0:
            progress = 25

        done_value = bool(status == "done") if is_postgres_enabled() else int(status == "done")
        if is_postgres_enabled():
            conn.execute(
                "UPDATE todos SET text = %s, status = %s, done = %s, progress = %s WHERE id = %s",
                (text, status, done_value, progress, todo_id),
            )
            row = fetch_one(conn, "SELECT * FROM todos WHERE id = %s", (todo_id,))
        else:
            conn.execute(
                "UPDATE todos SET text = ?, status = ?, done = ?, progress = ? WHERE id = ?",
                (text, status, done_value, progress, todo_id),
            )
            row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return to_dict(row)


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with db() as conn:
        if is_postgres_enabled():
            conn.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
        else:
            conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
