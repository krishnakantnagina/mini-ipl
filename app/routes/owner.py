from datetime import date
from functools import wraps

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app)
from werkzeug.security import check_password_hash

from app import db
from app.models import Owner, Match, PlayerProfile, Performance, SKILLS, unique_slug
from app.utils import save_photo, delete_photo

owner_bp = Blueprint("owner", __name__)


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("owner_id"):
            flash("Please log in with your owner ID first.", "warning")
            return redirect(url_for("owner.login"))
        return view(*args, **kwargs)

    return wrapped


def _my_team():
    return Owner.query.get_or_404(session["owner_id"]).team


def _my_player_or_none(player_id):
    """The player only if they belong to the logged-in owner's team."""
    player = PlayerProfile.query.get_or_404(player_id)
    if player.team_id != session.get("owner_team_id"):
        flash("That player is not in your team.", "danger")
        return None
    return player


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
                           matches=matches, upcoming=upcoming[:3], record=record,
                           skills=SKILLS,
                           max_squad=current_app.config["MAX_SQUAD_SIZE"])


# ---------- squad management ----------

@owner_bp.route("/players/add", methods=["POST"])
@owner_required
def add_player():
    team = _my_team()
    if len(team.players) >= current_app.config["MAX_SQUAD_SIZE"]:
        flash(f"Your squad is already full ({current_app.config['MAX_SQUAD_SIZE']} players).", "danger")
        return redirect(url_for("owner.dashboard"))

    name = request.form.get("name", "").strip()
    mobile = request.form.get("mobile", "").strip()
    skill = request.form.get("skill", "")
    if not name or skill not in SKILLS:
        flash("Player name and a valid skill are required.", "danger")
        return redirect(url_for("owner.dashboard"))

    slug = unique_slug(name)
    player = PlayerProfile(name=name, slug=slug, mobile=mobile, skill=skill,
                           photo=save_photo(request.files.get("photo"), slug),
                           team_id=team.id)
    db.session.add(player)
    db.session.commit()
    flash(f"{name} added to {team.name}! Profile: /players/{slug}", "success")
    return redirect(url_for("owner.dashboard"))


@owner_bp.route("/players/<int:player_id>/edit", methods=["GET", "POST"])
@owner_required
def edit_player(player_id):
    player = _my_player_or_none(player_id)
    if player is None:
        return redirect(url_for("owner.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        skill = request.form.get("skill", "")
        if not name or skill not in SKILLS:
            flash("Player name and a valid skill are required.", "danger")
            return redirect(url_for("owner.edit_player", player_id=player.id))
        if name != player.name:
            player.slug = unique_slug(name, current_id=player.id)
        player.name = name
        player.mobile = request.form.get("mobile", "").strip()
        player.skill = skill
        new_photo = save_photo(request.files.get("photo"), player.slug)
        if new_photo:
            delete_photo(player.photo)
            player.photo = new_photo
        db.session.commit()
        flash(f"{player.name}'s profile updated.", "success")
        return redirect(url_for("owner.dashboard"))

    return render_template("owner/edit_player.html", player=player, skills=SKILLS)


@owner_bp.route("/players/<int:player_id>/captain", methods=["POST"])
@owner_required
def set_captain(player_id):
    player = _my_player_or_none(player_id)
    if player:
        was = player.is_captain
        for p in player.team.players:
            p.is_captain = False
        player.is_captain = not was
        if player.is_captain:
            player.is_vice_captain = False
        db.session.commit()
        flash(f"{player.name} is {'now the captain' if player.is_captain else 'no longer captain'}.", "success")
    return redirect(url_for("owner.dashboard"))


@owner_bp.route("/players/<int:player_id>/vice-captain", methods=["POST"])
@owner_required
def set_vice_captain(player_id):
    player = _my_player_or_none(player_id)
    if player:
        was = player.is_vice_captain
        for p in player.team.players:
            p.is_vice_captain = False
        player.is_vice_captain = not was
        if player.is_vice_captain:
            player.is_captain = False
        db.session.commit()
        flash(f"{player.name} is {'now the vice-captain' if player.is_vice_captain else 'no longer vice-captain'}.", "success")
    return redirect(url_for("owner.dashboard"))


@owner_bp.route("/players/<int:player_id>/delete", methods=["POST"])
@owner_required
def delete_player(player_id):
    player = _my_player_or_none(player_id)
    if player:
        Performance.query.filter_by(player_id=player.id).delete()
        delete_photo(player.photo)
        db.session.delete(player)
        db.session.commit()
        flash(f"{player.name} removed from your squad.", "info")
    return redirect(url_for("owner.dashboard"))
