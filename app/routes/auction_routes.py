from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from app.models import Player, Team, auction_open
from app.utils import admin_required
from app import auction as auction_state

auction_bp = Blueprint("auction", __name__)


@auction_bp.route("/")
def live_view():
    if not auction_open():
        return render_template("auction/closed.html")
    recent = Player.query.filter(Player.status.in_(["sold", "unsold"])).order_by(Player.id.desc()).limit(15).all()
    return render_template("auction/live_view.html", state=auction_state.get_state(), recent=recent)


@auction_bp.route("/bid", methods=["GET", "POST"])
def bid_console():
    if not auction_open():
        return render_template("auction/closed.html")
    if request.method == "POST":
        code = request.form.get("access_code", "").strip().upper()
        team = Team.query.filter_by(access_code=code).first()
        if team:
            session["bid_team_id"] = team.id
            flash(f"Welcome, {team.owner_name}! You are bidding for {team.name}.", "success")
        else:
            flash("Invalid access code.", "danger")
        return redirect(url_for("auction.bid_console"))

    team = None
    if session.get("bid_team_id"):
        team = Team.query.get(session["bid_team_id"])
    return render_template("auction/bid_console.html", team=team, state=auction_state.get_state())


@auction_bp.route("/bid/leave")
def leave_bid_console():
    session.pop("bid_team_id", None)
    flash("Left the bidding console.", "info")
    return redirect(url_for("auction.bid_console"))


@auction_bp.route("/admin")
@admin_required
def admin_console():
    available = Player.query.filter_by(status="in_auction").order_by(Player.name).all()
    unsold = Player.query.filter_by(status="unsold").order_by(Player.name).all()
    pending = Player.query.filter_by(status="registered").count()
    teams = Team.query.order_by(Team.name).all()
    return render_template(
        "auction/admin_console.html",
        available=available, unsold=unsold, pending=pending, teams=teams,
        state=auction_state.get_state(),
    )
