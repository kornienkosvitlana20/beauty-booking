const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

let token = null;
export const setToken = (t) => { token = t; };

export async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(API + path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new Error("Немає зʼєднання з сервером");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "Перевірте введені дані" : data.detail;
    throw new Error(detail || "Помилка сервера");
  }
  return data;
}
