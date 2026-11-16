import { useEffect, useState } from "react";
import { api, setToken } from "./api.js";

// ПОЧАТКОВИЙ КАРКАС для Людини B: вхід + пошук майстрів.
// TODO(B): реєстрація, сторінка майстра, вибір слота, мої записи, відгуки.

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async () => {
    try {
      const { access_token } = await api("/auth/login", { method: "POST", body: { email, password } });
      setToken(access_token);
      onLogin(await api("/auth/me"));
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div>
      <h2>Вхід</h2>
      <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="Пароль" value={password}
             onChange={(e) => setPassword(e.target.value)} />
      <button onClick={submit}>Увійти</button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

function Search() {
  const [city, setCity] = useState("");
  const [masters, setMasters] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const qs = city ? `?city=${encodeURIComponent(city)}` : "";
      setMasters(await api(`/masters${qs}`));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  };
  useEffect(() => { load(); }, []);

  return (
    <div>
      <h2>Пошук майстрів</h2>
      <input placeholder="Місто" value={city} onChange={(e) => setCity(e.target.value)} />
      <button onClick={load}>Знайти</button>
      {error && <p role="alert">{error}</p>}
      {masters && masters.length === 0 && <p>Нічого не знайдено. Спробуйте інше місто.</p>}
      <ul>
        {(masters || []).map((m) => (
          <li key={m.id}>
            {m.full_name} — {m.category_name}, {m.city}
            {m.rating !== null && ` ★ ${m.rating}`}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  return (
    <main>
      <h1>Beauty Booking</h1>
      {user ? <p>Вітаємо, {user.full_name}!</p> : <Login onLogin={setUser} />}
      <Search />
    </main>
  );
}
