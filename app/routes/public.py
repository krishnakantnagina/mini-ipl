from datetime import date

from flask import Blueprint, render_template, request, session
from sqlalchemy import func

from app import db
from app.models import (PlayerProfile, Team, Match, Performance, SKILLS,
                        STAGE_LABELS, get_setting)
from app.utils import compute_points_table

public_bp = Blueprint("public", __name__)


TEAM_PALETTE = ['#1d4e89', '#c8102e', '#7b2d8b', '#e6a817', '#0f7b6c', '#d35400', '#2e4057', '#5c821a']


@public_bp.app_context_processor
def inject_helpers():
    return {
        "team_color": lambda team: TEAM_PALETTE[team.id % len(TEAM_PALETTE)],
        "stage_labels": STAGE_LABELS,
        "site_name": get_setting("site_name", "Mini IPL"),
        "site_quote": get_setting("site_quote", "Teams sign players. Rivals battle. One cup."),
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
        db.session.query(PlayerProfile, func.sum(Performance.runs).label("total_runs"))
        .join(Performance)
        .group_by(PlayerProfile.id)
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
        "players": PlayerProfile.query.count(),
        "signed": PlayerProfile.query.filter(PlayerProfile.team_id.isnot(None)).count(),
        "completed": Match.query.filter_by(status="completed").count(),
    }
    final = Match.query.filter_by(stage="final", status="completed").first()
    champion = final.winner if final else None
    return render_template(
        "public/index.html", next_match=next_match, table=table,
        top_scorers=top_scorers, recent_results=recent_results, counts=counts,
        champion=champion,
    )


@public_bp.route("/players")
def players():
    skill = request.args.get("skill", "")
    team_arg = request.args.get("team", "")
    q = PlayerProfile.query
    if skill:
        q = q.filter_by(skill=skill)
    if team_arg == "free":
        q = q.filter(PlayerProfile.team_id.is_(None))
    elif team_arg.isdigit():
        q = q.filter_by(team_id=int(team_arg))
    all_players = q.order_by(PlayerProfile.name).all()
    return render_template(
        "public/players.html", players=all_players, skills=SKILLS,
        teams=Team.query.order_by(Team.name).all(),
        sel_skill=skill, sel_team=team_arg,
    )


@public_bp.route("/players/<slug>")
def player_profile(slug):
    player = PlayerProfile.query.filter_by(slug=slug).first_or_404()
    totals = (
        db.session.query(
            func.count(Performance.id),
            func.sum(Performance.runs),
            func.sum(Performance.wickets),
        )
        .filter(Performance.player_id == player.id)
        .first()
    )
    stats = {"matches": totals[0] or 0, "runs": totals[1] or 0, "wickets": totals[2] or 0}
    recent = (
        Performance.query.filter_by(player_id=player.id)
        .join(Match).order_by(Match.date.desc()).limit(5).all()
    )
    # mobile number stays private: only the admin and the player's own owner see it
    can_see_mobile = bool(
        session.get("is_admin")
        or (player.team_id and session.get("owner_team_id") == player.team_id)
    )
    return render_template("public/player_profile.html", player=player,
                           stats=stats, recent=recent, can_see_mobile=can_see_mobile)


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
            PlayerProfile,
            func.sum(Performance.runs).label("runs"),
            func.sum(Performance.balls).label("balls"),
            func.count(Performance.id).label("matches"),
        )
        .join(Performance)
        .group_by(PlayerProfile.id)
        .order_by(func.sum(Performance.runs).desc())
        .limit(10)
        .all()
    )
    purple = (
        db.session.query(
            PlayerProfile,
            func.sum(Performance.wickets).label("wickets"),
            func.sum(Performance.runs_conceded).label("conceded"),
            func.count(Performance.id).label("matches"),
        )
        .join(Performance)
        .filter(Performance.wickets > 0)
        .group_by(PlayerProfile.id)
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
