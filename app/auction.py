"""Live auction: in-memory state + SocketIO event handlers.

The auction state is transient (lives only while the server runs).
Sold/unsold outcomes are written to the database immediately.
"""
import threading

from flask import session, current_app
from flask_socketio import emit

from app import db, socketio
from app.models import Player, Team, auction_open

_lock = threading.Lock()

_state = {
    "active": False,
    "player_id": None,
    "player_name": None,
    "player_role": None,
    "base_price": None,
    "current_bid": None,
    "leading_team_id": None,
    "leading_team": None,
    "history": [],  # recent bid strings for the ticker
}


def get_state():
    return dict(_state)


def _reset_state():
    _state.update({
        "active": False,
        "player_id": None,
        "player_name": None,
        "player_role": None,
        "base_price": None,
        "current_bid": None,
        "leading_team_id": None,
        "leading_team": None,
        "history": [],
    })


@socketio.on("start_player")
def start_player(data):
    if not session.get("is_admin"):
        emit("auction_error", {"message": "Admin login not detected on this connection - refresh the page and log in as admin again."})
        return
    with _lock:
        player = Player.query.get(data.get("player_id"))
        if not player or player.status not in ("registered", "in_auction", "unsold"):
            emit("auction_error", {"message": "Player not available for auction."})
            return
        player.status = "in_auction"
        db.session.commit()
        _state.update({
            "active": True,
            "player_id": player.id,
            "player_name": player.name,
            "player_role": player.role,
            "base_price": player.base_price,
            "current_bid": None,
            "leading_team_id": None,
            "leading_team": None,
            "history": [f"{player.name} ({player.role}) up for auction at base price {player.base_price} L"],
        })
    emit("state_update", get_state(), broadcast=True)
    emit("auction_info", {"message": f"Bidding started for {player.name}."})


@socketio.on("place_bid")
def place_bid(data=None):
    if not auction_open():
        emit("auction_error", {"message": "The auction room is closed right now."})
        return
    team_id = session.get("bid_team_id")
    if not team_id:
        emit("auction_error", {"message": "Enter your team access code first."})
        return
    with _lock:
        if not _state["active"]:
            emit("auction_error", {"message": "No player is up for auction right now."})
            return
        team = Team.query.get(team_id)
        if not team:
            emit("auction_error", {"message": "Unknown team."})
            return
        if team.id == _state["leading_team_id"]:
            emit("auction_error", {"message": "You are already the highest bidder."})
            return

        increment = current_app.config["BID_INCREMENT"]
        next_bid = _state["base_price"] if _state["current_bid"] is None \
            else _state["current_bid"] + increment

        squad_size = Player.query.filter_by(team_id=team.id).count()
        if squad_size >= current_app.config["MAX_SQUAD_SIZE"]:
            emit("auction_error", {"message": "Your squad is already full."})
            return
        if team.purse < next_bid:
            emit("auction_error", {"message": "Not enough purse left for this bid."})
            return

        _state["current_bid"] = next_bid
        _state["leading_team_id"] = team.id
        _state["leading_team"] = team.name
        _state["history"].insert(0, f"{team.name} bids {next_bid} L")
        _state["history"] = _state["history"][:20]
    emit("state_update", get_state(), broadcast=True)


@socketio.on("mark_sold")
def mark_sold(data=None):
    if not session.get("is_admin"):
        emit("auction_error", {"message": "Admin login not detected on this connection - refresh the page and log in as admin again."})
        return
    with _lock:
        if not _state["active"] or _state["leading_team_id"] is None:
            emit("auction_error", {"message": "No bids yet - use Unsold instead."})
            return
        player = Player.query.get(_state["player_id"])
        team = Team.query.get(_state["leading_team_id"])
        price = _state["current_bid"]
        player.status = "sold"
        player.team_id = team.id
        player.sold_price = price
        team.purse -= price
        db.session.commit()
        result = {
            "message": f"SOLD! {player.name} goes to {team.name} for {price} L",
            "player_id": player.id,
        }
        _reset_state()
        _state["history"] = [result["message"]]
    emit("player_done", result, broadcast=True)
    emit("state_update", get_state(), broadcast=True)


@socketio.on("mark_unsold")
def mark_unsold(data=None):
    if not session.get("is_admin"):
        emit("auction_error", {"message": "Admin login not detected on this connection - refresh the page and log in as admin again."})
        return
    with _lock:
        if not _state["active"]:
            emit("auction_error", {"message": "No player is up for auction right now."})
            return
        player = Player.query.get(_state["player_id"])
        player.status = "unsold"
        db.session.commit()
        result = {"message": f"{player.name} goes UNSOLD", "player_id": player.id}
        _reset_state()
        _state["history"] = [result["message"]]
    emit("player_done", result, broadcast=True)
    emit("state_update", get_state(), broadcast=True)
