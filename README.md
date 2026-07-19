# Mini IPL Management System

A Flask web app for running a mini IPL-style tournament: player registration,
a live real-time auction where team owners bid from their own devices, match
scheduling, result entry, a points table with NRR, player stats (Orange/Purple
Cap), and real-IPL-style playoffs (Qualifier 1, Eliminator, Qualifier 2, Final).

## Run locally

```
pip install -r requirements.txt
python seed.py        # optional: demo teams, players, fixtures, owner logins
python run.py
```

Open http://127.0.0.1:5000 — other devices on the same WiFi can use
`http://<your-pc-ip>:5000`.

- Admin login: `admin` / `admin123` (change via `ADMIN_USERNAME` / `ADMIN_PASSWORD` env vars)
- Owner logins are created by the admin under **Admin → Owners**
  (seed data uses the team short name in lowercase / `owner123`)

## Deploy (Render / Railway)

The included `Procfile` starts the app with gunicorn:

```
web: gunicorn -w 1 --threads 100 --bind 0.0.0.0:$PORT run:app
```

Set these environment variables on the host:

- `SECRET_KEY` — any long random string
- `ADMIN_PASSWORD` — a real password (don't keep `admin123` on the public internet)
- `DATABASE_URL` — optional Postgres URL; without it the app uses a local SQLite
  file, which is **wiped on every redeploy** on most free tiers

Keep it to **one** gunicorn worker (`-w 1`) — the live auction state is held in
process memory.
