import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api.js";
import TodoItem from "./TodoItem.jsx";
import paIcon from "./assets/Screenshot 2026-10-08 054402.png";

export default function App() {
  const particles = useMemo(
    () =>
      Array.from({ length: 84 }, () => {
        const driftX = (Math.random() - 0.5) * 520;
        const driftY = (Math.random() - 0.5) * 520;
        const duration = 6 + Math.random() * 18;
        const delay = -Math.random() * duration;
        const size = (Math.random() * 3.2 + 1.8).toFixed(2);
        const alpha = (Math.random() * 0.16 + 0.04).toFixed(3);

        return {
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
          size: `${size}px`,
          alpha,
          duration: `${duration.toFixed(2)}s`,
          delay: `${delay.toFixed(2)}s`,
          tx1: `${(driftX * 0.28).toFixed(1)}px`,
          ty1: `${(driftY * 0.28).toFixed(1)}px`,
          tx2: `${(driftX * 0.65).toFixed(1)}px`,
          ty2: `${(driftY * 0.65).toFixed(1)}px`,
          tx3: `${(driftX * 0.92).toFixed(1)}px`,
          ty3: `${(driftY * 0.92).toFixed(1)}px`,
          tx4: `${(driftX * 1.18).toFixed(1)}px`,
          ty4: `${(driftY * 1.18).toFixed(1)}px`,
        };
      }),
    []
  );

  const [todos, setTodos] = useState([]);
  const [tab, setTab] = useState("todo"); // "todo" or "done"
  const [newText, setNewText] = useState("");
  const [dragId, setDragId] = useState(null);
  const [clock, setClock] = useState(new Date());
  const orderBeforeDrag = useRef(null); // lets us undo a drag if saving fails
  const [error, setError] = useState("");
  const [protectedLinkOpen, setProtectedLinkOpen] = useState(false);
  const [protectedLinkTarget, setProtectedLinkTarget] = useState(null);
  const [protectedLinkPassword, setProtectedLinkPassword] = useState("");
  const [protectedLinkError, setProtectedLinkError] = useState("");

  useEffect(() => {
    api.list().then(setTodos).catch(() => setError("Can't reach the server. Is the backend running?"));
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Runs an action and shows a friendly message if it fails.
  async function run(action) {
    try {
      setError("");
      await action();
    } catch {
      setError("Something went wrong. Check that the backend is running.");
    }
  }

  const replace = (updated) => setTodos((list) => list.map((t) => (t.id === updated.id ? updated : t)));

  const addTodo = (e) => {
    e.preventDefault();
    if (!newText.trim()) return;
    run(async () => {
      const todo = await api.add(newText);
      setTodos((list) => [...list, todo]);
      setNewText("");
      setTab("todo");
    });
  };

  const updateStatus = (todo, status) => run(async () => replace(await api.update(todo.id, { status })));
  const updateProgress = (todo, progress) =>
    run(async () => {
      const nextStatus = progress >= 100 ? "done" : "in_progress";
      replace(await api.update(todo.id, { status: nextStatus, progress }));
    });
  const toggle = (todo) => {
    if (todo.status === "todo") {
      return updateStatus(todo, "in_progress");
    }
    if (todo.status === "in_progress") {
      return updateStatus(todo, "done");
    }
    return updateStatus(todo, "in_progress");
  };
  const saveText = (todo, text) => run(async () => replace(await api.update(todo.id, { text })));
  const remove = (id) =>
    run(async () => {
      await api.remove(id);
      setTodos((list) => list.filter((t) => t.id !== id));
    });
  const clearDone = () =>
    run(async () => {
      await api.clearDone();
      setTodos((list) => list.filter((t) => t.status !== "done"));
    });

  // --- Drag and drop (To do tab only) ---
  function startDrag(id) {
    orderBeforeDrag.current = todos;
    setDragId(id);
  }

  function dragOver(e, overId) {
    e.preventDefault();
    if (dragId === null || dragId === overId) return;
    const from = todos.findIndex((t) => t.id === dragId);
    const to = todos.findIndex((t) => t.id === overId);
    const copy = [...todos];
    copy.splice(to, 0, copy.splice(from, 1)[0]);
    setTodos(copy);
  }

  async function endDrag() {
    setDragId(null);
    const unfinished = todos.filter((t) => t.status === "todo").map((t) => t.id);
    try {
      await api.reorder(unfinished, "todo");
    } catch {
      setTodos(orderBeforeDrag.current); // put the list back the way it was
      setError("Couldn't save the new order.");
    }
  }

  const todoItems = todos.filter((t) => t.status === "todo");
  const inProgressItems = todos.filter((t) => t.status === "in_progress");
  const doneItems = todos.filter((t) => t.status === "done");
  const items = tab === "todo" ? todoItems : tab === "in_progress" ? inProgressItems : doneItems;

  const tabs = [
    { id: "todo", label: "To do", count: todoItems.length },
    { id: "in_progress", label: "In Progress", count: inProgressItems.length },
    { id: "done", label: "Done", count: doneItems.length },
  ];

  const openProtectedLink = (target) => {
    setProtectedLinkTarget(target);
    setProtectedLinkPassword("");
    setProtectedLinkError("");
    setProtectedLinkOpen(true);
  };

  const handleProtectedLinkSubmit = (e) => {
    e.preventDefault();

    if (protectedLinkPassword === "PAUL193231") {
      setProtectedLinkOpen(false);
      setProtectedLinkPassword("");
      setProtectedLinkError("");
      window.open(protectedLinkTarget, "_blank", "noopener,noreferrer");
      return;
    }

    setProtectedLinkError("Incorrect password. Please try again.");
  };

  return (
    <>
      <div className="particle-field" aria-hidden="true">
        {particles.map((particle, index) => (
          <span
            key={index}
            className="particle"
            style={{
              left: particle.left,
              top: particle.top,
              width: particle.size,
              height: particle.size,
              opacity: particle.alpha,
              "--duration": particle.duration,
              "--delay": particle.delay,
              "--tx1": particle.tx1,
              "--ty1": particle.ty1,
              "--tx2": particle.tx2,
              "--ty2": particle.ty2,
              "--tx3": particle.tx3,
              "--ty3": particle.ty3,
              "--tx4": particle.tx4,
              "--ty4": particle.ty4,
              "--alpha": particle.alpha,
            }}
          />
        ))}
      </div>

      <div className="app-brand-mark" aria-label="PA app icon">
        <img src={paIcon} alt="PA brand icon" />
      </div>

      <main className="page">
        <div className="page-header">
          <h1>Today</h1>
          <div className="clock-widget" aria-live="polite" aria-label="Current time">
            <span className="clock-time">{clock.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</span>
            <span className="clock-date">{clock.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}</span>
          </div>
        </div>

      <form className="add" onSubmit={addTodo}>
        <input
          value={newText}
          onChange={(e) => setNewText(e.target.value)}
          maxLength={200}
          placeholder="What needs doing?"
          aria-label="New todo"
        />
        <button type="submit">Add</button>
      </form>

      <div className="tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls="panel"
            className={tab === t.id ? "tab active" : "tab"}
            onClick={() => setTab(t.id)}
          >
            {t.label} <span className="badge">{t.count}</span>
          </button>
        ))}
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <section id="panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {items.length === 0 ? (
          <p className="empty">
            {tab === "todo"
              ? "Nothing left to do. Add something above."
              : tab === "in_progress"
                ? "No tasks are in progress right now."
                : "Nothing finished yet. Check an item off and it lands here."}
          </p>
        ) : (
          <div className="list-scroll">
            <ul className="list">
              {items.map((todo) => (
                <TodoItem
                  key={todo.id}
                  todo={todo}
                  sortable={tab === "todo"}
                  dragging={dragId === todo.id}
                  onToggle={() => toggle(todo)}
                  onStatusChange={(status) => updateStatus(todo, status)}
                  onProgressChange={(progress) => updateProgress(todo, progress)}
                  onDelete={() => remove(todo.id)}
                  onSave={(text) => saveText(todo, text)}
                  dragHandlers={{
                    onDragStart: () => startDrag(todo.id),
                    onDragOver: (e) => dragOver(e, todo.id),
                    onDragEnd: endDrag,
                  }}
                />
              ))}
            </ul>
          </div>
        )}

        {tab === "todo" && items.length > 1 && (
          <p className="hint">Drag the dots to reorder. Double-click a todo to edit it.</p>
        )}
        {tab === "done" && items.length > 0 && (
          <button className="clear" onClick={clearDone}>Clear all done</button>
        )}
      </section>
      </main>

      <div className="utility-buttons">
        <button className="utility-button" type="button" onClick={() => openProtectedLink("https://docs.google.com/document/d/18VJnxqABdXmvFYNvy0Ptoe1cPFHo5pYJ1CJ2b-Hxo8A/edit?tab=t.0")}>
          Diary
        </button>
        <button className="utility-button" type="button" onClick={() => openProtectedLink("https://docs.google.com/document/d/1vAipwB4vY1sIQP3kR2pimqXDKDokzdc1cELCFrNale8/edit?usp=sharing")}>
          Gratitude Journal
        </button>
      </div>

      <aside className="quote-panel" aria-label="Daily inspiration quotes">
        <blockquote>
          “Your time is limited, so don't waste it living someone else's life.”
          <footer>— Steve Jobs</footer>
        </blockquote>
        <blockquote>
          “Dost thou love life? Then do not squander time, for that is the stuff life is made of.”
          <footer>— Benjamin Franklin</footer>
        </blockquote>
      </aside>

      {protectedLinkOpen && (
        <div className="diary-modal-backdrop" onClick={() => setProtectedLinkOpen(false)}>
          <div className="diary-modal" role="dialog" aria-modal="true" aria-labelledby="diary-dialog-title" onClick={(e) => e.stopPropagation()}>
            <h2 id="diary-dialog-title">Protected page</h2>
            <p>Enter the password to continue.</p>
            <form onSubmit={handleProtectedLinkSubmit}>
              <label className="sr-only" htmlFor="diary-password">Password</label>
              <input
                id="diary-password"
                type="password"
                value={protectedLinkPassword}
                onChange={(e) => {
                  setProtectedLinkPassword(e.target.value);
                  if (protectedLinkError) setProtectedLinkError("");
                }}
                placeholder="Password"
                autoFocus
              />
              {protectedLinkError && <p className="diary-error">{protectedLinkError}</p>}
              <div className="diary-actions">
                <button type="button" className="secondary" onClick={() => setProtectedLinkOpen(false)}>Cancel</button>
                <button type="submit" className="primary">Open</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
