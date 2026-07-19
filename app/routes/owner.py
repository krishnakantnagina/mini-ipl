from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash

from app.models import Owner, Match

owner_bp = Blueprint("owner", __name__)


def owner_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("owner_id"):
            flash("Please log in with your owner ID first.", "warning")
            return redirect(url_for("owner.login"))
        return view(*args, **kwargs)

    return wrapped


@owner_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        owner = Owner.query.filter_by(username=username).first()
        if owner and check_password_hash(owner.password_hash, password):
            session["owner_id"] = owner.id
            session["owner_team_id"] = owner.team_id
            flash(f"Welcome back! You own {owner.team.name}.", "success")
            return redirect(url_for("owner.dashboard"))
        flash("Wrong owner ID or password.", "danger")
    return render_template("owner/login.html")


@owner_bp.route("/logout")
def logout():
    for key in ("owner_id", "owner_team_id"):
        session.pop(key, None)
    flash("Logged out.", "info")
    return redirect(url_for("public.index"))


@owner_bp.route("/")
@owner_required
def dashboard():
    owner = Owner.query.get_or_404(session["owner_id"])
    team = owner.team
    matches = (
        Match.query.filter((Match.team1_id == team.id) | (Match.team2_id == team.id))
        .order_by(Match.date)
        .all()
    )
    upcoming = [m for m in matches if m.status == "scheduled" and m.date >= date.today()]
    completed = [m for m in matches if m.status == "completed"]
    record = {
        "wins": sum(1 for m in completed if m.winner_id == team.id),
        "losses": sum(1 for m in completed if m.winner_id and m.winner_id != team.id),
        "ties": sum(1 for m in completed if not m.winner_id),
    }
    return render_template("owner/dashboard.html", owner=owner, team=team,
                           matches=matches, upcoming=upcoming[:3], record=record)
