# AGENT.md

Instructions for any AI coding agent (or person) working on this project.
Read this before changing anything.

## What this project is
A simple todo list app with three tabs: To do, In Progress, and Done.
- **Backend:** Python + FastAPI + SQLite, in `backend/` (all code in `main.py`)
- **Frontend:** React (plain JavaScript) + Vite, in `frontend/src/`
- The frontend calls the backend at `/api/...`; Vite forwards those requests to
  `http://127.0.0.1:8000` (see `frontend/vite.config.js`).
- The author is a beginner. Keep code simple and commented. Prefer clarity over cleverness.
  Do not add libraries or frameworks unless really needed, and explain why if you do.

## Project layout
```
AGENT.md                   this file
README.md                  how a person runs the app
backend/
  main.py                  the whole API (FastAPI + SQLite)
  test_main.py             tests for every endpoint (pytest)
  check_endpoints.py       checks every endpoint on a RUNNING server
  requirements.txt
  todos.db                 the database (created automatically, not committed)
frontend/
  vite.config.js           dev server + the /api proxy
  src/main.jsx             entry point
  src/App.jsx              page, tabs, drag and drop
  src/TodoItem.jsx         one row (checkbox, edit, delete)
  src/api.js               every call to the backend
  src/styles.css           all styling (colours are CSS variables at the top)
```

## Data model
One table, `todos`: `id` (auto), `text` (required), `done` (0/1 for compatibility),
`status` (`todo`, `in_progress`, `done`), and `position` (smaller = higher in the list).
The API returns `{"id", "text", "done", "status"}`; `position` is never sent to the
frontend, the order of the list *is* the position.

## Commands
Backend (run from `backend/`, with the virtual environment active):
- Start server:   `uvicorn main:app --reload`   (port 8000)
- Run tests:      `pytest`
- Check a live server: `python check_endpoints.py`

Frontend (run from `frontend/`):
- Install: `npm install`
- Start:   `npm run dev`   (http://localhost:5173)
- Build check: `npm run build`

## The endpoints
| Method | Path                | What it does                                  |
|--------|---------------------|-----------------------------------------------|
| GET    | `/api/todos`        | List all todos in saved order                 |
| POST   | `/api/todos`        | Add a todo (`{"text": "..."}`, max 200 chars) |
| PATCH  | `/api/todos/{id}`   | Change `text` and/or `done`                   |
| DELETE | `/api/todos/{id}`   | Delete one todo                               |
| PUT    | `/api/todos/order`  | Reorder (`{"ids": [...]}`)                    |
| DELETE | `/api/todos`        | Delete every finished todo                    |

Route order matters in `main.py`: `/api/todos/order` must be declared **before**
`/api/todos/{todo_id}`, otherwise "order" is read as an id.

## Rules for endpoints (always follow these)
1. **Every endpoint has tests.** When you add or change an endpoint, add or update
   tests for it in `backend/test_main.py` in the same change. Cover the success case
   and each error case (blank text -> 400, unknown id -> 404, bad input -> 422, etc.).
2. **Always validate that the endpoints work before you say you're done.** Run all of:
   1. `pytest` in `backend/`: every test must pass.
   2. Start the server and run `python check_endpoints.py`: every check must pass.
   3. If the frontend or API shape changed, also run `npm run build` in `frontend/`.
   Report what you ran and the result. Never claim something works without running it.
3. **Add every new endpoint to `check_endpoints.py`** and to the table above.
4. If a test fails, fix the code or the test for a good reason. Never delete or
   weaken a test just to make it pass.
5. Tests must not touch the real database. `test_main.py` points `TODO_DB` at a
   temporary file and empties it before each test. Keep it that way.

## Code style
- Backend: type hints, short docstrings, comments for non-obvious choices.
- Frontend: function components with hooks; all backend calls go through `src/api.js`.
- Keep the **three-stage workflow**: a task starts in To do, can move to In Progress,
  and ends in Done. In Progress tasks may carry a progress value from 0 to 100, and
  a 100% value automatically marks a task as Done.
- Reordering only sends the visible To do ids; the backend reuses their existing
  positions so other statuses keep their place.

## How to add or change an endpoint
1. Write or update the function in `backend/main.py` (mind the route order above).
2. Add tests in `backend/test_main.py`: success case plus every error case.
3. Add checks in `backend/check_endpoints.py` and a row in the endpoint table above.
4. If the frontend needs it, add a function to `frontend/src/api.js` first, then use it.
5. Run the full validation (rule 2 above) and report the results.

## Changing the database
There are no migrations. `CREATE TABLE IF NOT EXISTS` does nothing when the table
already exists, so adding or changing a column in that statement will **not** update
an existing `todos.db`. If you change the schema, either write a small migration
(`ALTER TABLE ...`) that runs at startup, or tell the user clearly what they must do.
Never delete their `todos.db` without asking: it holds their real todos.

## Known gotchas (these have already bitten us)
- **Trailing slashes:** the API path is `/api/todos`, not `/api/todos/`. FastAPI answers
  the slash version with a 307 redirect, and httpx's `base_url` adds the slash for you.
  Build full URLs instead (see `check_endpoints.py`).
- **Test file names:** pytest collects any file named `test_*.py` or `*_test.py`. Name
  helper scripts something else (like `check_endpoints.py`) so they aren't run as tests.
- **Reordering:** the To do tab sends only unfinished ids to `PUT /api/todos/order`.
  Sending all ids would scramble finished items. Don't change this without updating tests.
- **Backend must be running** for the frontend to work. The Vite proxy only forwards
  `/api` requests; if the backend is down the page shows "Can't reach the server".
- **Fonts** come from Google Fonts, so they need internet. Offline, the page still works
  with fallback fonts.
- **Starting servers in a script or sandbox:** run them in the background, save the process
  id, and stop them by that id. `pkill -f "uvicorn main:app"` can kill the shell that ran it.

## Frontend checks
There are no automated frontend tests yet. For any UI change:
- Run `npm run build`; it must succeed.
- Actually use the page (add, tick, untick, edit, delete, drag, switch tabs), in a real
  browser or a headless one such as Playwright. Don't claim the UI works from reading code.
- Say clearly what you did and did not test. Drag and drop is the easiest thing to miss.
- Keep it usable by keyboard, with visible focus, and keep the `aria-` labels on the tabs
  and buttons. Colours and fonts come from the variables in `styles.css`; don't hard-code new ones.

## Security notes
This is a single-user, local app: no login, no authentication, and no CORS settings
(the dev proxy makes the browser see one origin). Do not expose it to the internet as is.
Always keep SQL parameterised (`?` placeholders), never build queries from user text.
Validate input on the backend even if the frontend already checks it.

## Working with the author
The author is a beginner. When you change something, say what you changed and why in
plain language, and give exact commands for anything they need to do (for example
`pip install -r requirements.txt` after a dependency changes). Ask before big or
destructive changes. If something is ambiguous, state your assumption clearly.

## Definition of done
A change is finished only when all of these are true:
- [ ] `pytest` passes (new behaviour has new tests)
- [ ] `python check_endpoints.py` passes against a running server
- [ ] `npm run build` passes (if the frontend or API shape changed)
- [ ] The UI was exercised if it changed, or you said it wasn't
- [ ] This file, `README.md` and the endpoint table are updated if anything above changed
- [ ] Your reply lists what you ran and what the results were

## Keeping this file current
If you add a command, endpoint, rule or gotcha, update this file in the same change.
A wrong instruction here is worse than a missing one.

## Things not to do
- Don't commit `backend/todos.db`, `node_modules/`, `venv/` or `__pycache__/`.
- Don't use browser `localStorage` for todos; the database is the source of truth.
- Don't wipe the user's `todos.db` or run `DELETE /api/todos` against their real
  server without asking (it removes all finished items).
