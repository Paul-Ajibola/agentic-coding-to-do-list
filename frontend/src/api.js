// All communication with the Python backend lives here, so components stay simple.
const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request(path = "", method = "GET", body) {
  const url = `${API_BASE_URL}/api/todos${path}`;

  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.status === 204 ? null : res.json();
}

export const api = {
  list: () => request(),
  add: (text) => request("", "POST", { text }),
  update: (id, changes) => request(`/${id}`, "PATCH", changes),
  remove: (id) => request(`/${id}`, "DELETE"),
  reorder: (ids, status = "todo") => request("/order", "PUT", { ids, status }),
  clearDone: () => request("", "DELETE"),
};
