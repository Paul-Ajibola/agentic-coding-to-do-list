import { useState } from "react";

// One row in the list. Editing state lives here because only this row cares about it.
export default function TodoItem({ todo, sortable, dragging, onToggle, onStatusChange, onProgressChange, onDelete, onSave, dragHandlers }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  function startEditing() {
    setDraft(todo.text);
    setEditing(true);
  }

  function finishEditing(save) {
    setEditing(false);
    if (save && draft.trim() && draft.trim() !== todo.text) onSave(draft);
  }

  const classes = ["item", todo.status === "done" && "done", dragging && "dragging"].filter(Boolean).join(" ");
  const canStart = todo.status === "todo";
  const canFinish = todo.status === "in_progress";
  const progress = Math.min(100, Math.max(0, Number(todo.progress) || 0));

  return (
    <li className={classes} draggable={sortable && !editing} {...(sortable ? dragHandlers : {})}>
      {sortable && <span className="grip" aria-hidden="true">⠿</span>}
      {editing ? (
        <input
          className="edit"
          autoFocus
          maxLength={200}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => finishEditing(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter") finishEditing(true);
            if (e.key === "Escape") finishEditing(false);
          }}
        />
      ) : (
        <span className="text" onDoubleClick={startEditing} title="Double-click to edit">
          {todo.text}
        </span>
      )}

      <div className="status-actions">
        {canStart && (
          <button className="status-btn" onClick={() => onStatusChange("in_progress")}>
            Start
          </button>
        )}
        {canFinish && (
          <button className="status-btn done-btn" onClick={() => onStatusChange("done")}>
            Done
          </button>
        )}
        {todo.status === "done" && (
          <button className="status-btn" onClick={() => onStatusChange("in_progress")}>
            Reopen
          </button>
        )}
      </div>

      <button className="delete" onClick={onDelete} aria-label={`Delete "${todo.text}"`}>
        Delete
      </button>
    </li>
  );
}
