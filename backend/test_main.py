"""Tests for every endpoint. Run with:  pytest   (from the backend folder)

Endpoints covered:
  GET    /api/todos          list
  POST   /api/todos          add
  PATCH  /api/todos/{id}     update text and/or done
  DELETE /api/todos/{id}     delete one
  PUT    /api/todos/order    reorder
  DELETE /api/todos          clear all done
"""
import os
import tempfile

os.environ["TODO_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app, db  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def empty_database():
    """Every test starts with an empty list, so tests can't affect each other."""
    with db() as conn:
        conn.execute("DELETE FROM todos")
    yield


def add(text):
    res = client.post("/api/todos", json={"text": text})
    assert res.status_code == 201
    return res.json()


def texts():
    return [t["text"] for t in client.get("/api/todos").json()]


def statuses():
    return [t["status"] for t in client.get("/api/todos").json()]


def progresses():
    return [t["progress"] for t in client.get("/api/todos").json()]


# --- GET /api/todos ---------------------------------------------------------
def test_list_empty():
    res = client.get("/api/todos")
    assert res.status_code == 200 and res.json() == []


def test_list_returns_items_in_order_added():
    add("a"), add("b"), add("c")
    assert texts() == ["a", "b", "c"]
    assert statuses() == ["todo", "todo", "todo"]


# --- POST /api/todos --------------------------------------------------------
def test_add_returns_new_todo_and_trims_text():
    res = client.post("/api/todos", json={"text": "  Buy milk "})
    assert res.status_code == 201
    body = res.json()
    assert body["text"] == "Buy milk"
    assert body["status"] == "todo"
    assert body["done"] is False
    assert body["progress"] == 0
    assert isinstance(body["id"], int)
    assert texts() == ["Buy milk"]
    assert statuses() == ["todo"]
    assert progresses() == [0]


@pytest.mark.parametrize("bad", ["", "   "])
def test_add_rejects_blank_text(bad):
    assert client.post("/api/todos", json={"text": bad}).status_code == 400
    assert texts() == []


def test_add_rejects_too_long_text():
    assert client.post("/api/todos", json={"text": "x" * 201}).status_code == 422


def test_add_rejects_missing_text():
    assert client.post("/api/todos", json={}).status_code == 422


# --- PATCH /api/todos/{id} --------------------------------------------------
def test_patch_done_and_back():
    todo = add("task")
    res = client.patch(f"/api/todos/{todo['id']}", json={"done": True})
    assert res.json()["done"] is True and res.json()["status"] == "done"

    res = client.patch(f"/api/todos/{todo['id']}", json={"done": False})
    assert res.json()["done"] is False and res.json()["status"] == "todo"


def test_patch_status_moves_between_tabs():
    todo = add("task")
    res = client.patch(f"/api/todos/{todo['id']}", json={"status": "in_progress"})
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"
    assert res.json()["done"] is False
    assert res.json()["progress"] == 25

    res = client.patch(f"/api/todos/{todo['id']}", json={"status": "done"})
    assert res.status_code == 200
    assert res.json()["status"] == "done"
    assert res.json()["done"] is True
    assert res.json()["progress"] == 100


def test_patch_progress_updates_value():
    todo = add("task")
    res = client.patch(f"/api/todos/{todo['id']}", json={"status": "in_progress", "progress": 75})
    assert res.status_code == 200
    assert res.json()["progress"] == 75

    res = client.patch(f"/api/todos/{todo['id']}", json={"progress": 100})
    assert res.status_code == 200
    assert res.json()["progress"] == 100
    assert res.json()["status"] == "done"


def test_patch_text_keeps_status():
    todo = add("typo")
    client.patch(f"/api/todos/{todo['id']}", json={"status": "in_progress"})
    res = client.patch(f"/api/todos/{todo['id']}", json={"text": " fixed "})
    assert res.status_code == 200
    assert res.json() == {"id": todo["id"], "text": "fixed", "done": False, "status": "in_progress", "progress": 25}


def test_patch_rejects_blank_text():
    todo = add("keep me")
    assert client.patch(f"/api/todos/{todo['id']}", json={"text": "  "}).status_code == 400
    assert texts() == ["keep me"]


def test_patch_rejects_unknown_status():
    todo = add("keep me")
    assert client.patch(f"/api/todos/{todo['id']}", json={"status": "blocked"}).status_code == 422


def test_patch_unknown_id_is_404():
    assert client.patch("/api/todos/9999", json={"done": True}).status_code == 404


# --- DELETE /api/todos/{id} -------------------------------------------------
def test_delete_one():
    a, b = add("a"), add("b")
    assert client.delete(f"/api/todos/{a['id']}").status_code == 204
    assert texts() == ["b"]


def test_delete_unknown_id_is_harmless():
    add("a")
    assert client.delete("/api/todos/9999").status_code == 204
    assert texts() == ["a"]


# --- PUT /api/todos/order ---------------------------------------------------
def test_reorder_all():
    a, b, c = (add(t)["id"] for t in "abc")
    assert client.put("/api/todos/order", json={"ids": [c, a, b]}).json() == {"ok": True}
    assert texts() == ["c", "a", "b"]


def test_reorder_only_visible_items_keeps_done_items_in_place():
    a, b, c = (add(t)["id"] for t in "abc")
    client.patch(f"/api/todos/{b}", json={"done": True})  # b is on the Done tab
    client.put("/api/todos/order", json={"ids": [c, a]})  # To do tab shows c, a
    assert texts() == ["c", "b", "a"]


def test_reorder_empty_list_is_ok():
    add("a")
    assert client.put("/api/todos/order", json={"ids": []}).status_code == 200


def test_reorder_duplicate_ids_is_400():
    a = add("a")["id"]
    assert client.put("/api/todos/order", json={"ids": [a, a]}).status_code == 400


def test_reorder_unknown_id_is_404_and_changes_nothing():
    a, b = add("a")["id"], add("b")["id"]
    assert client.put("/api/todos/order", json={"ids": [b, 9999, a]}).status_code == 404
    assert texts() == ["a", "b"]


def test_order_route_is_not_mistaken_for_an_id():
    """'/order' must hit the reorder route, not PATCH/DELETE '/{todo_id}'."""
    assert client.put("/api/todos/order", json={"ids": []}).status_code == 200


# --- DELETE /api/todos (clear done) -----------------------------------------
def test_clear_done_only_removes_finished_items():
    a, b, c = (add(t)["id"] for t in "abc")
    client.patch(f"/api/todos/{a}", json={"status": "done"})
    client.patch(f"/api/todos/{c}", json={"status": "done"})
    assert client.delete("/api/todos").status_code == 204
    assert texts() == ["b"]
    assert statuses() == ["todo"]


def test_clear_done_with_nothing_done():
    add("a")
    assert client.delete("/api/todos").status_code == 204
    assert texts() == ["a"]
