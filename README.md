# Beauty Booking

Кросплатформена інформаційна система для пошуку та онлайн-запису до фахівців індустрії краси
(манікюр, перукарі, брови та вії, макіяж, косметологія, масаж).

**Стек:** Python 3.12 · FastAPI · SQLAlchemy 2 · SQLite/PostgreSQL · JWT · React + Vite · Electron · Docker · GitHub Actions.

## Функціонал
- Реєстрація та вхід (ролі: клієнт, майстер), JWT
- Профіль майстра: категорія, місто, послуги з цінами та тривалістю, графік роботи
- Пошук і фільтри: місто, категорія, текст, ціна, рейтинг, пагінація
- Вільні слоти та онлайн-запис (подвійне бронювання неможливе)
- Скасування і перенесення запису, історія записів
- Відгуки та рейтинг майстра після візиту

## Швидкий старт

Потрібно: Python 3.12+, Node.js 20+ (для клієнта). Усі команди однакові на Windows, macOS і Linux, крім активації venv.

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
API: http://localhost:8000 · документація Swagger: http://localhost:8000/docs
За замовчуванням використовується SQLite (`beauty.db` створюється автоматично, категорії додаються при старті).

### 2. Клієнт (веб)
```bash
cd frontend
npm install
npm run dev
```

### 3. Клієнт (десктоп, Electron)
```bash
cd frontend
npm run build
npm run electron:dev
# інсталятор під поточну ОС:
npm run electron:build
```

### Альтернатива: Docker (PostgreSQL + API)
```bash
docker compose up --build
```

## Тести та якість
```bash
cd backend
pytest              # автотести + звіт покриття (≥80% обовʼязково)
pylint app          # статичний аналіз
```
CI (`.github/workflows/ci.yml`) ганяє pylint і pytest на Ubuntu та Windows.

## Змінні середовища
| Змінна | За замовчуванням | Опис |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./beauty.db` | рядок підключення до БД |
| `SECRET_KEY` | `dev-secret-change-me` | ключ підпису JWT (змініть у продакшені) |
| `TOKEN_TTL_MINUTES` | `120` | термін дії токена |
| `VITE_API_URL` | `http://localhost:8000` | адреса API для клієнта |

## Обмеження
Усі дати та час — локальні (без часових поясів). Слоти формуються з кроком 30 хв від початку зміни майстра.

## Документація
`docs/ROLES.md` · `docs/TEST_CASES.md` · `docs/EDGE_CASES.md` · `docs/DECISIONS.md` · `docs/schema.sql` · `docs/DEFENSE_A.md`

## Гілкова модель
`main` — стабільна. Нова робота — `feature/<issue>-<назва>`, злиття лише через PR з рев'ю.
