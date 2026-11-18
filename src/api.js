const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8001/api";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
    });
  } catch {
    throw new Error("Can't reach ResolveAI right now. Check that the backend is running.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail || "The request could not be completed.");
  }
  return body;
}

export const api = {
  transactions: (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    return request(`/transactions${params.size ? `?${params}` : ""}`);
  },
  transaction: (id) => request(`/transactions/${encodeURIComponent(id)}`),
  refunds: () => request("/refunds"),
  refund: (reference) => request(`/refunds/${encodeURIComponent(reference)}`),
  complaints: () => request("/complaints"),
  complaint: (reference) => request(`/complaints/${encodeURIComponent(reference)}`),
  createComplaint: (payload) => request("/complaints", { method: "POST", body: JSON.stringify(payload) }),
  updateComplaintStatus: (reference, payload) => request(`/complaints/${encodeURIComponent(reference)}/status`, { method: "PATCH", body: JSON.stringify(payload) }),
  chat: (payload) => request("/assistant/chat", { method: "POST", body: JSON.stringify(payload) }),
};
