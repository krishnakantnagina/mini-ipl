from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func

from app import db
from app.models import (Player, Team, Match, Performance, ROLES, STAGE_LABELS,
                        registration_open, auction_open, get_setting)
from app.utils import compute_points_table, format_money

public_bp = Blueprint("public", __name__)


@public_bp.app_template_filter("money")
def money_filter(lakhs):
    return format_money(lakhs)


TEAM_PALETTE = ['#1d4e89', '#c8102e', '#7b2d8b', '#e6a817', '#0f7b6c', '#d35400', '#2e4057', '#5c821a']


@public_bp.app_context_processor
def inject_helpers():
    return {
        "team_color": lambda team: TEAM_PALETTE[team.id % len(TEAM_PALETTE)],
        "registration_on": registration_open(),
        "auction_on": auction_open(),
        "stage_labels": STAGE_LABELS,
        "site_name": get_setting("site_name", "Mini IPL"),
        "site_quote": get_setting("site_quote", "Players register. Owners bid. Teams battle. One cup."),
        "site_year": get_setting("site_year", "2026"),
    }


@public_bp.route("/")
def index():
    next_match = (
        Match.query.filter_by(status="scheduled")
        .filter(Match.date >= date.today())
        .order_by(Match.date)
        .first()
    )
    table = compute_points_table()[:4]
    top_scorers = (
        db.session.query(Player, func.sum(Performance.runs).label("total_runs"))
        .join(Performance)
        .group_by(Player.id)
        .order_by(func.sum(Performance.runs).desc())
        .limit(3)
        .all()
    )
    recent_results = (
        Match.query.filter_by(status="completed")
        .order_by(Match.date.desc())
        .limit(3)
        .all()
    )
    counts = {
        "teams": Team.query.count(),
        "players": Player.query.count(),
        "sold": Player.query.filter_by(status="sold").count(),
        "completed": Match.query.filter_by(status="completed").count(),
    }
    final = Match.query.filter_by(stage="final", status="completed").first()
    champion = final.winner if final else None
    return render_template(
        "public/index.html", next_match=next_match, table=table,
        top_scorers=top_scorers, recent_results=recent_results, counts=counts,
        champion=champion,
    )


@public_bp.route("/register", methods=["GET", "POST"])
def register():
    if not registration_open():
        if request.method == "POST":
            flash("Sorry, player registration is currently closed.", "danger")
        return render_template("public/register.html", roles=ROLES, closed=True)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "")
        try:
            age = int(request.form.get("age", 0))
            base_price = int(request.form.get("base_price", 20))
        except ValueError:
            age, base_price = 0, 0

        if not name or role not in ROLES or age < 14 or base_price < 1:
            flash("Please fill all fields correctly (age 14+, base price at least 1 lakh).", "danger")
        else:
            db.session.add(Player(name=name, age=age, role=role, base_price=base_price))
            db.session.commit()
            flash(f"Welcome {name}! You are registered for the auction.", "success")
            return redirect(url_for("public.players"))
    return render_template("public/register.html", roles=ROLES)


@public_bp.route("/players")
def players():
    role = request.args.get("role", "")
    status = request.args.get("status", "")
    q = Player.query
    if role:
        q = q.filter_by(role=role)
    if status:
        q = q.filter_by(status=status)
    all_players = q.order_by(Player.name).all()
    return render_template(
        "public/players.html", players=all_players, roles=ROLES,
        sel_role=role, sel_status=status,
    )


@public_bp.route("/teams")
def teams():
    all_teams = Team.query.order_by(Team.name).all()
    return render_template("public/teams.html", teams=all_teams)


@public_bp.route("/teams/<int:team_id>")
def team_detail(team_id):
    team = Team.query.get_or_404(team_id)
    matches = (
        Match.query.filter(
            (Match.team1_id == team_id) | (Match.team2_id == team_id)
        )
        .order_by(Match.date)
        .all()
    )
    return render_template("public/team_detail.html", team=team, matches=matches)


@public_bp.route("/schedule")
def schedule():
    stage_order = {"qualifier1": 0, "eliminator": 1, "qualifier2": 2, "final": 3}
    playoffs = sorted(
        Match.query.filter(Match.stage != "league").all(),
        key=lambda m: stage_order.get(m.stage, 9),
    )
    upcoming = (Match.query.filter_by(status="scheduled", stage="league")
                .order_by(Match.date).all())
    completed = (Match.query.filter_by(status="completed", stage="league")
                 .order_by(Match.date.desc()).all())
    next_id = upcoming[0].id if upcoming else None
    return render_template("public/schedule.html", playoffs=playoffs,
                           upcoming=upcoming, completed=completed, next_id=next_id)


@public_bp.route("/matches/<int:match_id>")
def match_detail(match_id):
    match = Match.query.get_or_404(match_id)
    return render_template("public/match_detail.html", match=match)


@public_bp.route("/points")
def points():
    return render_template("public/points_table.html", table=compute_points_table())


@public_bp.route("/stats")
def stats():
    orange = (
        db.session.query(
            Player,
            func.sum(Performance.runs).label("runs"),
            func.sum(Performance.balls).label("balls"),
            func.count(Performance.id).label("matches"),
        )
        .join(Performance)
        .group_by(Player.id)
        .order_by(func.sum(Performance.runs).desc())
        .limit(10)
        .all()
    )
    purple = (
        db.session.query(
            Player,
            func.sum(Performance.wickets).label("wickets"),
            func.sum(Performance.runs_conceded).label("conceded"),
            func.count(Performance.id).label("matches"),
        )
        .join(Performance)
        .filter(Performance.wickets > 0)
        .group_by(Player.id)
        .order_by(func.sum(Performance.wickets).desc(), func.sum(Performance.runs_conceded))
        .limit(10)
        .all()
    )
    best_figures = (
        Performance.query.filter(Performance.wickets > 0)
        .order_by(Performance.wickets.desc(), Performance.runs_conceded)
        .limit(5)
        .all()
    )
    return render_template(
        "public/stats.html", orange=orange, purple=purple, best_figures=best_figures
    )
