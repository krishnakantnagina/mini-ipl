from app import db

ROLES = ["Batsman", "Bowler", "All-rounder", "Wicketkeeper"]


class Setting(db.Model):
    key = db.Column(db.String(40), primary_key=True)
    value = db.Column(db.String(200), nullable=False)


def get_setting(key, default=""):
    s = db.session.get(Setting, key)
    return s.value if s is not None else default


def set_setting(key, value):
    s = db.session.get(Setting, key)
    if s is None:
        s = Setting(key=key, value="")
        db.session.add(s)
    s.value = value
    db.session.commit()


def registration_open():
    return get_setting("registration_open", "1") == "1"


def set_registration_open(is_open):
    set_setting("registration_open", "1" if is_open else "0")


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    short_name = db.Column(db.String(8), nullable=False)
    owner_name = db.Column(db.String(80), nullable=False)

    players = db.relationship("Player", backref="team", lazy=True)


class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False, unique=True)

    team = db.relationship("Team", backref=db.backref("owner_account", uselist=False))


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    age = db.Column(db.Integer)
    role = db.Column(db.String(20), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))  # None = free agent

    performances = db.relationship("Performance", backref="player", lazy=True)


MATCH_STAGES = ["league", "qualifier1", "eliminator", "qualifier2", "final"]
STAGE_LABELS = {
    "qualifier1": "Qualifier 1",
    "eliminator": "Eliminator",
    "qualifier2": "Qualifier 2",
    "final": "FINAL",
}


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    stage = db.Column(db.String(20), nullable=False, default="league")

    team1_runs = db.Column(db.Integer)
    team1_wickets = db.Column(db.Integer)
    team1_overs = db.Column(db.Float)
    team2_runs = db.Column(db.Integer)
    team2_wickets = db.Column(db.Integer)
    team2_overs = db.Column(db.Float)
    winner_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    summary = db.Column(db.String(200))

    team1 = db.relationship("Team", foreign_keys=[team1_id])
    team2 = db.relationship("Team", foreign_keys=[team2_id])
    winner = db.relationship("Team", foreign_keys=[winner_id])
    performances = db.relationship("Performance", backref="match", lazy=True)


class Performance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("match.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("player.id"), nullable=False)
    runs = db.Column(db.Integer, default=0)
    balls = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
