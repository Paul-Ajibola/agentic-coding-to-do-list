"""Todo list backend: FastAPI + SQLite."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# The database file sits next to this script, wherever you start the server from.
# (TODO_DB can override the location; the tests use that.)
DB_FILE = os.environ.get("TODO_DB", str(Path(__file__).with_name("todos.db")))
VALID_STATUSES = {"todo", "in_progress", "done"}
app = FastAPI(title="Todo API")


@contextmanager
def db():
    """Open a database connection, save changes, and always close it."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us read rows like dictionaries
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# Create the table the first time the app starts.
with db() as conn:
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
        rows = conn.execute("SELECT * FROM todos ORDER BY position").fetchall()
    return [to_dict(r) for r in rows]


@app.post("/api/todos", status_code=201)
def add_todo(body: NewTodo):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")
    with db() as conn:
        # New items go to the bottom: position = highest position + 1
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
    marks = ",".join("?" * len(ids))
    if body.status is not None:
        query = f"SELECT position FROM todos WHERE status = ? AND id IN ({marks}) ORDER BY position"
        params = [body.status, *ids]
    else:
        query = f"SELECT position FROM todos WHERE id IN ({marks}) ORDER BY position"
        params = ids

    with db() as conn:
        rows = conn.execute(query, params).fetchall()
        if len(rows) != len(ids):
            raise HTTPException(404, "Unknown todo id")
        for row, todo_id in zip(rows, ids):
            conn.execute("UPDATE todos SET position = ? WHERE id = ?", (row["position"], todo_id))
    return {"ok": True}


@app.delete("/api/todos", status_code=204)
def clear_done():
    """Delete every finished todo (the 'Clear all' button on the Done tab)."""
    with db() as conn:
        conn.execute("DELETE FROM todos WHERE status = 'done'")


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoUpdate):
    with db() as conn:
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
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

        conn.execute(
            "UPDATE todos SET text = ?, status = ?, done = ?, progress = ? WHERE id = ?",
            (text, status, int(status == "done"), progress, todo_id),
        )
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return to_dict(row)


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with db() as conn:
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
