import os
import secrets
from functools import wraps

from flask import session, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def save_photo(file, slug):
    """Save an uploaded player photo under static/uploads/players.

    Returns the path relative to static/ (for url_for('static', ...)),
    or None if nothing valid was uploaded.
    """
    if not file or not file.filename:
        return None
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in PHOTO_EXTENSIONS:
        return None
    folder = os.path.join(current_app.static_folder, "uploads", "players")
    os.makedirs(folder, exist_ok=True)
    filename = f"{slug}-{secrets.token_hex(4)}{ext}"
    file.save(os.path.join(folder, filename))
    return f"uploads/players/{filename}"


def delete_photo(photo):
    if not photo:
        return
    path = os.path.join(current_app.static_folder, *photo.split("/"))
    if os.path.isfile(path):
        os.remove(path)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please log in as admin first.", "warning")
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped


def compute_points_table():
    """Points table from completed matches: 2 pts win, 1 pt tie/no-result.

    Returns rows sorted by points, then NRR.
    """
    from app.models import Team, Match

    rows = {
        t.id: {
            "team": t,
            "played": 0,
            "won": 0,
            "lost": 0,
            "tied": 0,
            "points": 0,
            "runs_for": 0,
            "overs_for": 0.0,
            "runs_against": 0,
            "overs_against": 0.0,
            "form": [],  # 'W'/'L'/'T' per completed match, oldest first
        }
        for t in Team.query.all()
    }

    # playoffs don't count towards the league table
    for m in Match.query.filter_by(status="completed", stage="league").order_by(Match.date).all():
        if m.team1_id not in rows or m.team2_id not in rows:
            continue
        r1, r2 = rows[m.team1_id], rows[m.team2_id]
        r1["played"] += 1
        r2["played"] += 1

        r1["runs_for"] += m.team1_runs or 0
        r1["overs_for"] += overs_to_decimal(m.team1_overs)
        r1["runs_against"] += m.team2_runs or 0
        r1["overs_against"] += overs_to_decimal(m.team2_overs)

        r2["runs_for"] += m.team2_runs or 0
        r2["overs_for"] += overs_to_decimal(m.team2_overs)
        r2["runs_against"] += m.team1_runs or 0
        r2["overs_against"] += overs_to_decimal(m.team1_overs)

        if m.winner_id == m.team1_id:
            r1["won"] += 1
            r1["points"] += 2
            r2["lost"] += 1
            r1["form"].append("W")
            r2["form"].append("L")
        elif m.winner_id == m.team2_id:
            r2["won"] += 1
            r2["points"] += 2
            r1["lost"] += 1
            r2["form"].append("W")
            r1["form"].append("L")
        else:  # tie / no result
            r1["tied"] += 1
            r2["tied"] += 1
            r1["points"] += 1
            r2["points"] += 1
            r1["form"].append("T")
            r2["form"].append("T")

    table = list(rows.values())
    for r in table:
        nrr = 0.0
        if r["overs_for"] > 0 and r["overs_against"] > 0:
            nrr = (r["runs_for"] / r["overs_for"]) - (r["runs_against"] / r["overs_against"])
        r["nrr"] = nrr
        r["form"] = r["form"][-5:]

    table.sort(key=lambda r: (r["points"], r["nrr"]), reverse=True)
    return table


def overs_to_decimal(overs):
    """Convert cricket overs notation (e.g. 19.3 = 19 overs 3 balls) to decimal overs."""
    if not overs:
        return 0.0
    whole = int(overs)
    balls = round((overs - whole) * 10)
    return whole + balls / 6.0
