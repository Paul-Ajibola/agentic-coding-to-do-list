"""Checks every endpoint of a RUNNING server: a quick "is it really working?" test.

Start the backend first (uvicorn main:app), then in another terminal:
    python check_endpoints.py                         # checks http://127.0.0.1:8000
    python check_endpoints.py http://127.0.0.1:5173   # checks through the frontend proxy

It creates its own todos and removes them again. Exits 0 if all is well, 1 otherwise.
"""
import sys

import httpx

failures = []


def check(name, condition):
    print(("PASS  " if condition else "FAIL  ") + name)
    if not condition:
        failures.append(name)


class Todos:
    """Tiny client that builds exact URLs (httpx's base_url would add a trailing slash)."""

    def __init__(self, base):
        self.url, self.http = base + "/api/todos", httpx.Client(timeout=5)

    def __getattr__(self, method):  # c.get("/1"), c.post("", json=...), etc.
        return lambda path="", **kw: self.http.request(method.upper(), self.url + path, **kw)


def run(base):
    c = Todos(base)
    before = c.get("").json()
    start_ids = {t["id"] for t in before}
    check("GET    /api/todos", c.get("").status_code == 200)

    r = c.post("", json={"text": "check A"})
    check("POST   /api/todos", r.status_code == 201 and r.json()["text"] == "check A")
    a = r.json()["id"]
    b = c.post("", json={"text": "check B"}).json()["id"]
    check("POST   /api/todos rejects blank text -> 400", c.post("", json={"text": " "}).status_code == 400)

    r = c.patch(f"/{a}", json={"done": True})
    check("PATCH  /api/todos/{id} done", r.status_code == 200 and r.json()["done"] is True)
    r = c.patch(f"/{a}", json={"text": "check A2"})
    check("PATCH  /api/todos/{id} text", r.status_code == 200 and r.json()["text"] == "check A2")
    check("PATCH  /api/todos/{id} unknown id -> 404", c.patch("/999999", json={"done": True}).status_code == 404)

    check("PUT    /api/todos/order", c.put("/order", json={"ids": [b, a]}).status_code == 200)
    ours = [t["id"] for t in c.get("").json() if t["id"] in (a, b)]
    check("PUT    /api/todos/order changes the order", ours == [b, a])

    check("DELETE /api/todos/{id}", c.delete(f"/{b}").status_code == 204)
    check("DELETE /api/todos/{id} really removed it", b not in {t["id"] for t in c.get("").json()})

    # "Clear all done" deletes EVERY finished item, so only try it when there are
    # no finished items of yours that it could wipe (a is ours and is done).
    if any(t["done"] for t in before):
        print("SKIP  DELETE /api/todos (you have finished items; not touching them)")
    else:
        check("DELETE /api/todos (clear done)", c.delete("").status_code == 204)
        check("DELETE /api/todos removed finished items", a not in {t["id"] for t in c.get("").json()})

    c.delete(f"/{a}")  # tidy up (harmless if already gone)
    check("left your list as it found it", {t["id"] for t in c.get("").json()} == start_ids)


if __name__ == "__main__":
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    try:
        run(base)
    except httpx.HTTPError as err:
        print(f"Could not reach {base}: {err}\nIs the backend running?")
        sys.exit(1)
    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("All endpoint checks passed")
