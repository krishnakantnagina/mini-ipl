from datetime import datetime, date, timedelta
from itertools import combinations
import random

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash

from app import db
from app.models import (PlayerProfile, Team, Match, Performance, Owner, SKILLS,
                        STAGE_LABELS, get_setting, set_setting, unique_slug)
from app.utils import admin_required, compute_points_table, delete_photo

admin_bp = Blueprint("admin", __name__)


# ---------- auth ----------

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        cfg = current_app.config
        if username == cfg["ADMIN_USERNAME"] and password == cfg["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            flash("Welcome, admin!", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Wrong username or password.", "danger")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("public.index"))


# ---------- dashboard ----------

@admin_bp.route("/")
@admin_required
def dashboard():
    counts = {
        "players": PlayerProfile.query.count(),
        "free": PlayerProfile.query.filter(PlayerProfile.team_id.is_(None)).count(),
        "signed": PlayerProfile.query.filter(PlayerProfile.team_id.isnot(None)).count(),
        "teams": Team.query.count(),
        "matches": Match.query.count(),
        "completed": Match.query.filter_by(status="completed").count(),
    }
    return render_template("admin/dashboard.html", counts=counts)


@admin_bp.route("/site", methods=["GET", "POST"])
@admin_required
def site_settings():
    if request.method == "POST":
        set_setting("site_name", request.form.get("site_name", "").strip() or "Mini IPL")
        set_setting("site_quote", request.form.get("site_quote", "").strip())
        set_setting("site_year", request.form.get("site_year", "").strip())
        flash("Home page settings saved.", "success")
        return redirect(url_for("admin.site_settings"))
    return render_template(
        "admin/site_settings.html",
        site_name=get_setting("site_name", "Mini IPL"),
        site_quote=get_setting("site_quote", "Players register. Owners bid. Teams battle. One cup."),
        site_year=get_setting("site_year", "2026"),
    )


# ---------- players ----------

def _team_from_form():
    """Return (team_or_None, ok) for the submitted team_id ('' = free agent)."""
    raw = request.form.get("team_id", "")
    if not raw:
        return None, True
    try:
        team = Team.query.get(int(raw))
    except ValueError:
        team = None
    return team, team is not None


@admin_bp.route("/players", methods=["GET", "POST"])
@admin_required
def players():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        skill = request.form.get("skill", "")
        mobile = request.form.get("mobile", "").strip()
        team, team_ok = _team_from_form()
        if not name or skill not in SKILLS:
            flash("Name and a valid skill are required.", "danger")
        else:
            db.session.add(PlayerProfile(name=name, slug=unique_slug(name),
                                         mobile=mobile, skill=skill,
                                         team_id=team.id if team else None))
            db.session.commit()
            flash(f"Player {name} added.", "success")
        return redirect(url_for("admin.players"))

    all_players = PlayerProfile.query.order_by(
        PlayerProfile.team_id.is_(None).desc(), PlayerProfile.name).all()
    return render_template("admin/players.html", players=all_players, skills=SKILLS,
                           teams=Team.query.order_by(Team.name).all())


@admin_bp.route("/players/<int:player_id>/edit", methods=["POST"])
@admin_required
def edit_player(player_id):
    p = PlayerProfile.query.get_or_404(player_id)
    name = request.form.get("name", p.name).strip() or p.name
    if name != p.name:
        p.slug = unique_slug(name, current_id=p.id)
    p.name = name
    skill = request.form.get("skill", p.skill)
    if skill in SKILLS:
        p.skill = skill
    p.mobile = request.form.get("mobile", p.mobile or "").strip()
    team, team_ok = _team_from_form()
    if team_ok:
        new_team_id = team.id if team else None
        if new_team_id != p.team_id and team \
                and len(team.players) >= current_app.config["MAX_SQUAD_SIZE"]:
            flash(f"{team.name} already has a full squad.", "danger")
            return redirect(url_for("admin.players"))
        if new_team_id != p.team_id:
            p.is_captain = p.is_vice_captain = False  # tags belong to the old team
        p.team_id = new_team_id
    db.session.commit()
    flash(f"Player {p.name} updated.", "success")
    return redirect(url_for("admin.players"))


@admin_bp.route("/players/<int:player_id>/delete", methods=["POST"])
@admin_required
def delete_player(player_id):
    p = PlayerProfile.query.get_or_404(player_id)
    Performance.query.filter_by(player_id=p.id).delete()
    delete_photo(p.photo)
    db.session.delete(p)
    db.session.commit()
    flash(f"Player {p.name} deleted.", "info")
    return redirect(url_for("admin.players"))


# ---------- teams ----------

@admin_bp.route("/teams", methods=["GET", "POST"])
@admin_required
def teams():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        short_name = request.form.get("short_name", "").strip().upper()
        owner_name = request.form.get("owner_name", "").strip()
        if not name or not short_name or not owner_name:
            flash("All team fields are required.", "danger")
        elif Team.query.filter_by(name=name).first():
            flash("A team with that name already exists.", "danger")
        else:
            db.session.add(Team(name=name, short_name=short_name,
                                owner_name=owner_name))
            db.session.commit()
            flash(f"Team {name} created.", "success")
        return redirect(url_for("admin.teams"))

    all_teams = Team.query.order_by(Team.name).all()
    return render_template("admin/teams.html", teams=all_teams)


@admin_bp.route("/teams/<int:team_id>/edit", methods=["POST"])
@admin_required
def edit_team(team_id):
    t = Team.query.get_or_404(team_id)
    t.name = request.form.get("name", t.name).strip() or t.name
    t.short_name = (request.form.get("short_name", t.short_name).strip() or t.short_name).upper()
    t.owner_name = request.form.get("owner_name", t.owner_name).strip() or t.owner_name
    db.session.commit()
    flash(f"Team {t.name} updated.", "success")
    return redirect(url_for("admin.teams"))


# ---------- owner accounts ----------

@admin_bp.route("/owners", methods=["GET", "POST"])
@admin_required
def owners():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        try:
            team_id = int(request.form.get("team_id", 0))
        except ValueError:
            team_id = 0
        team = Team.query.get(team_id)

        if not username or len(password) < 4:
            flash("Owner ID and a password of at least 4 characters are required.", "danger")
        elif not team:
            flash("Pick a valid team.", "danger")
        elif team.owner_account:
            flash(f"{team.name} already has an owner account.", "danger")
        elif Owner.query.filter_by(username=username).first():
            flash("That owner ID is already taken.", "danger")
        else:
            db.session.add(Owner(
                username=username,
                password_hash=generate_password_hash(password),
                team_id=team.id,
            ))
            db.session.commit()
            flash(f"Owner account '{username}' created for {team.name}. "
                  f"Share the ID and password with the owner.", "success")
        return redirect(url_for("admin.owners"))

    all_owners = Owner.query.order_by(Owner.username).all()
    free_teams = [t for t in Team.query.order_by(Team.name) if not t.owner_account]
    return render_template("admin/owners.html", owners=all_owners, free_teams=free_teams)


@admin_bp.route("/owners/<int:owner_id>/reset", methods=["POST"])
@admin_required
def reset_owner_password(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    password = request.form.get("password", "")
    if len(password) < 4:
        flash("New password must be at least 4 characters.", "danger")
    else:
        owner.password_hash = generate_password_hash(password)
        db.session.commit()
        flash(f"Password reset for '{owner.username}'.", "success")
    return redirect(url_for("admin.owners"))


@admin_bp.route("/owners/<int:owner_id>/delete", methods=["POST"])
@admin_required
def delete_owner(owner_id):
    owner = Owner.query.get_or_404(owner_id)
    db.session.delete(owner)
    db.session.commit()
    flash(f"Owner account '{owner.username}' deleted.", "info")
    return redirect(url_for("admin.owners"))


# ---------- matches ----------

@admin_bp.route("/matches", methods=["GET", "POST"])
@admin_required
def matches():
    all_teams = Team.query.order_by(Team.name).all()
    if request.method == "POST":
        try:
            team1_id = int(request.form.get("team1_id", 0))
            team2_id = int(request.form.get("team2_id", 0))
        except ValueError:
            team1_id = team2_id = 0
        venue = request.form.get("venue", "").strip()
        date_str = request.form.get("date", "")
        try:
            match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            match_date = None

        if team1_id == team2_id or not venue or not match_date:
            flash("Pick two different teams, a venue and a date.", "danger")
        elif not (Team.query.get(team1_id) and Team.query.get(team2_id)):
            flash("Unknown team selected.", "danger")
        else:
            db.session.add(Match(team1_id=team1_id, team2_id=team2_id,
                                 date=match_date, venue=venue))
            db.session.commit()
            flash("Match scheduled.", "success")
        return redirect(url_for("admin.matches"))

    all_matches = Match.query.order_by(Match.date).all()
    return render_template("admin/matches.html", matches=all_matches, teams=all_teams)


@admin_bp.route("/matches/generate", methods=["POST"])
@admin_required
def generate_round_robin():
    teams = Team.query.all()
    if len(teams) < 2:
        flash("Need at least 2 teams to generate fixtures.", "danger")
        return redirect(url_for("admin.matches"))

    venues = [f"{t.short_name} Home Ground" for t in teams]
    start = date.today() + timedelta(days=3)
    created = 0
    for i, (t1, t2) in enumerate(combinations(teams, 2)):
        exists = Match.query.filter(
            ((Match.team1_id == t1.id) & (Match.team2_id == t2.id))
            | ((Match.team1_id == t2.id) & (Match.team2_id == t1.id))
        ).first()
        if exists:
            continue
        db.session.add(Match(
            team1_id=t1.id, team2_id=t2.id,
            date=start + timedelta(days=i * 2),
            venue=random.choice(venues),
        ))
        created += 1
    db.session.commit()
    flash(f"Generated {created} round-robin fixtures.", "success")
    return redirect(url_for("admin.matches"))


def _loser(match):
    return match.team2 if match.winner_id == match.team1_id else match.team1


@admin_bp.route("/matches/generate-playoffs", methods=["POST"])
@admin_required
def generate_playoffs():
    """Real IPL format, one stage at a time:
    Qualifier 1 (1st v 2nd) + Eliminator (3rd v 4th) -> Qualifier 2
    (Q1 loser v Eliminator winner) -> Final (Q1 winner v Q2 winner)."""
    q1 = Match.query.filter_by(stage="qualifier1").first()
    elim = Match.query.filter_by(stage="eliminator").first()
    q2 = Match.query.filter_by(stage="qualifier2").first()
    final = Match.query.filter_by(stage="final").first()
    start = date.today() + timedelta(days=2)

    if not q1:
        if Match.query.filter_by(stage="league", status="scheduled").count():
            flash("Finish (or delete) all league matches before starting the playoffs.", "danger")
            return redirect(url_for("admin.matches"))
        table = compute_points_table()
        if len(table) < 4 or table[3]["played"] == 0:
            flash("Playoffs need at least 4 teams with completed league matches.", "danger")
            return redirect(url_for("admin.matches"))
        top = [r["team"] for r in table[:4]]
        db.session.add(Match(team1_id=top[0].id, team2_id=top[1].id, date=start,
                             venue="National Stadium", stage="qualifier1"))
        db.session.add(Match(team1_id=top[2].id, team2_id=top[3].id,
                             date=start + timedelta(days=1),
                             venue="National Stadium", stage="eliminator"))
        db.session.commit()
        flash(f"Playoffs started! Qualifier 1: {top[0].name} vs {top[1].name} · "
              f"Eliminator: {top[2].name} vs {top[3].name}", "success")
    elif not q2:
        if q1.status != "completed" or elim.status != "completed":
            flash("Enter the results of Qualifier 1 and the Eliminator first.", "danger")
        else:
            db.session.add(Match(team1_id=_loser(q1).id, team2_id=elim.winner_id,
                                 date=start, venue="National Stadium", stage="qualifier2"))
            db.session.commit()
            flash(f"Qualifier 2 created: {_loser(q1).name} vs {elim.winner.name}", "success")
    elif not final:
        if q2.status != "completed":
            flash("Enter the result of Qualifier 2 first.", "danger")
        else:
            db.session.add(Match(team1_id=q1.winner_id, team2_id=q2.winner_id,
                                 date=start, venue="National Stadium", stage="final"))
            db.session.commit()
            flash(f"THE FINAL is set: {q1.winner.name} vs {q2.winner.name} 🏆", "success")
    else:
        flash("All playoff matches are already created.", "info")
    return redirect(url_for("admin.matches"))


@admin_bp.route("/matches/<int:match_id>/delete", methods=["POST"])
@admin_required
def delete_match(match_id):
    m = Match.query.get_or_404(match_id)
    Performance.query.filter_by(match_id=m.id).delete()
    db.session.delete(m)
    db.session.commit()
    flash("Match deleted.", "info")
    return redirect(url_for("admin.matches"))


# ---------- result entry ----------

@admin_bp.route("/matches/<int:match_id>/result", methods=["GET", "POST"])
@admin_required
def result(match_id):
    m = Match.query.get_or_404(match_id)
    if request.method == "POST":
        try:
            m.team1_runs = int(request.form["team1_runs"])
            m.team1_wickets = int(request.form["team1_wickets"])
            m.team1_overs = float(request.form["team1_overs"])
            m.team2_runs = int(request.form["team2_runs"])
            m.team2_wickets = int(request.form["team2_wickets"])
            m.team2_overs = float(request.form["team2_overs"])
        except (KeyError, ValueError):
            flash("Please fill every score field with numbers.", "danger")
            return redirect(url_for("admin.result", match_id=m.id))

        winner = request.form.get("winner", "")
        if winner == str(m.team1_id):
            m.winner_id = m.team1_id
        elif winner == str(m.team2_id):
            m.winner_id = m.team2_id
        else:
            m.winner_id = None  # tie / no result

        if m.stage != "league" and m.winner_id is None:
            db.session.rollback()
            flash("A playoff match must have a winner — no ties allowed.", "danger")
            return redirect(url_for("admin.result", match_id=m.id))

        m.summary = request.form.get("summary", "").strip()
        m.status = "completed"
        db.session.commit()
        flash("Result saved. Points table updated.", "success")
        return redirect(url_for("admin.matches"))
    return render_template("admin/result_entry.html", m=m)


# ---------- performances ----------

@admin_bp.route("/matches/<int:match_id>/performances", methods=["GET", "POST"])
@admin_required
def performances(match_id):
    m = Match.query.get_or_404(match_id)
    squad = PlayerProfile.query.filter(
        PlayerProfile.team_id.in_([m.team1_id, m.team2_id])
    ).order_by(PlayerProfile.team_id, PlayerProfile.name).all()

    if request.method == "POST":
        Performance.query.filter_by(match_id=m.id).delete()
        saved = 0
        for p in squad:
            def val(field):
                try:
                    return max(0, int(request.form.get(f"{field}_{p.id}", 0) or 0))
                except ValueError:
                    return 0
            runs, balls = val("runs"), val("balls")
            wickets, conceded = val("wickets"), val("conceded")
            if runs or balls or wickets or conceded:
                db.session.add(Performance(
                    match_id=m.id, player_id=p.id, runs=runs, balls=balls,
                    wickets=wickets, runs_conceded=conceded,
                ))
                saved += 1
        db.session.commit()
        flash(f"Saved performances for {saved} players.", "success")
        return redirect(url_for("admin.matches"))

    existing = {perf.player_id: perf for perf in m.performances}
    return render_template("admin/performance_entry.html", m=m, squad=squad, existing=existing)
