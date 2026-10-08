# Todo app (FastAPI + React + SQLite)

You need two terminal windows.

## Terminal 1: backend (Python)
    cd backend
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn main:app --reload

## Terminal 2: frontend (React)
    cd frontend
    npm install
    npm run dev

Then open http://localhost:5173 in your browser.

- Three tabs: **To do**, **In Progress**, and **Done**. You can move tasks between them, edit them, drag items in the To do list, and adjust progress in the In Progress tab.
- Todos are stored in backend/todos.db (created automatically).
- Run the backend tests with `pytest` inside the backend folder.
- With the backend running, `python check_endpoints.py` (in the backend folder) checks every endpoint works.
- `AGENT.md` has the rules for AI assistants working on this project.
- Interactive API docs: http://127.0.0.1:8000/docs
