# Mini IPL Management System

A Flask web app for running a mini IPL-style tournament: team owners build
their squads with rich player profiles (photo, mobile, skill, captain and
vice-captain tags, name-based profile URLs), match scheduling, result entry,
a points table with NRR, player stats (Orange/Purple Cap), and real-IPL-style
playoffs (Qualifier 1, Eliminator, Qualifier 2, Final).

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
- Owners add players to their team from the owner dashboard: name, mobile,
  photo, skill (Batsman/Bowler/Both) and captain/vice-captain tags. Each
  player gets a profile page at `/players/<name-slug>`. Mobile numbers are
  shown only to the admin and that player's own team owner.
- Photo uploads land in `static/uploads/players/` (not tracked by git; on
  free cloud tiers they are lost on redeploy)

## Deploy (Render / Railway)

The included `Procfile` starts the app with gunicorn:

```
web: gunicorn --bind 0.0.0.0:$PORT run:app
```

Set these environment variables on the host:

- `SECRET_KEY` — any long random string
- `ADMIN_PASSWORD` — a real password (don't keep `admin123` on the public internet)
- `DATABASE_URL` — optional Postgres URL; without it the app uses a local SQLite
  file, which is **wiped on every redeploy** on most free tiers
