import re

from app import db

SKILLS = ["Batsman", "Bowler", "Both"]


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "player"


def unique_slug(name, current_id=None):
    """A URL slug from the player's name, made unique with -2, -3... if needed."""
    base = slugify(name)
    slug, n = base, 2
    while True:
        q = PlayerProfile.query.filter_by(slug=slug)
        if current_id is not None:
            q = q.filter(PlayerProfile.id != current_id)
        if q.first() is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


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


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    short_name = db.Column(db.String(8), nullable=False)
    owner_name = db.Column(db.String(80), nullable=False)

    players = db.relationship("PlayerProfile", backref="team", lazy=True)

    @property
    def captain(self):
        return next((p for p in self.players if p.is_captain), None)

    @property
    def vice_captain(self):
        return next((p for p in self.players if p.is_vice_captain), None)


class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False, unique=True)

    team = db.relationship("Team", backref=db.backref("owner_account", uselist=False))


class PlayerProfile(db.Model):
    __tablename__ = "player_profile"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # /players/<slug>
    mobile = db.Column(db.String(20))
    photo = db.Column(db.String(150))  # path under static/, e.g. uploads/players/x.jpg
    skill = db.Column(db.String(20), nullable=False, default="Batsman")  # SKILLS
    is_captain = db.Column(db.Boolean, nullable=False, default=False)
    is_vice_captain = db.Column(db.Boolean, nullable=False, default=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))

    performances = db.relationship("Performance", backref="player", lazy=True)

    @property
    def initials(self):
        parts = self.name.split()
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


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
    player_id = db.Column(db.Integer, db.ForeignKey("player_profile.id"), nullable=False)
    runs = db.Column(db.Integer, default=0)
    balls = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
