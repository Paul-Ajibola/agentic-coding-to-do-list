// All talk to the Python backend lives here, so components stay simple.
async function request(path = "", method = "GET", body) {
  const res = await fetch(`/api/todos${path}`, {
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
