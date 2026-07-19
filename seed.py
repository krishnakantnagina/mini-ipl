"""Reset the database and fill it with a demo tournament.

Run:  python seed.py
"""
import random
from datetime import date, timedelta
from itertools import combinations

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import PlayerProfile, Team, Match, Owner, slugify

random.seed(42)

TEAMS = [
    ("Mumbai Mavericks", "MM", "Rohit Enterprises"),
    ("Chennai Chargers", "CC", "Southern Sports Group"),
    ("Bangalore Blasters", "BB", "Garden City Holdings"),
    ("Kolkata Knights", "KK", "Eastern Star Media"),
    ("Delhi Daredevils", "DD", "Capital Ventures"),
]

FIRST = ["Arjun", "Rahul", "Vikram", "Suresh", "Ramesh", "Karan", "Aditya", "Manish",
         "Sanjay", "Deepak", "Nikhil", "Rohan", "Varun", "Ajay", "Pranav", "Kunal",
         "Siddharth", "Harsh", "Yash", "Dev", "Ishan", "Shubham", "Tejas", "Om",
         "Abhishek", "Gaurav", "Mohit", "Naveen", "Parth", "Ritesh"]
LAST = ["Sharma", "Patel", "Singh", "Kumar", "Verma", "Reddy", "Nair", "Iyer",
        "Chopra", "Malhotra", "Gupta", "Joshi", "Desai", "Mehta", "Rao", "Menon"]
SKILLS = ["Batsman", "Batsman", "Bowler", "Bowler", "All Rounder"]


def main():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        teams = []
        for name, short, owner in TEAMS:
            t = Team(name=name, short_name=short, owner_name=owner)
            db.session.add(t)
            teams.append(t)
        db.session.flush()

        # one owner login per team: id = short name lowercase, password = owner123
        for t in teams:
            db.session.add(Owner(
                username=t.short_name.lower(),
                password_hash=generate_password_hash("owner123"),
                team_id=t.id,
            ))

        # 25 players, 5 per team; every squad gets a captain and a vice-captain
        used_names = set()
        players = []
        while len(players) < 25:
            name = f"{random.choice(FIRST)} {random.choice(LAST)}"
            if name in used_names:
                continue
            used_names.add(name)
            p = PlayerProfile(
                name=name,
                slug=slugify(name),
                mobile=f"9{random.randint(100000000, 999999999)}",
                skill=random.choice(SKILLS),
                team_id=teams[len(players) % len(teams)].id,
            )
            db.session.add(p)
            players.append(p)
        db.session.flush()

        for t in teams:
            squad = [p for p in players if p.team_id == t.id]
            squad[0].is_captain = True
            squad[1].is_vice_captain = True

        # round-robin schedule: everyone plays everyone once, starting tomorrow
        fixtures = list(combinations(teams, 2))
        random.shuffle(fixtures)
        start = date.today() + timedelta(days=1)
        for i, (t1, t2) in enumerate(fixtures):
            db.session.add(Match(
                team1_id=t1.id, team2_id=t2.id,
                date=start + timedelta(days=i * 2),
                venue=f"{t1.short_name} Home Ground",
            ))

        db.session.commit()

        print("Database seeded!")
        print(f"  Teams   : {Team.query.count()}")
        print(f"  Players : {PlayerProfile.query.count()} (5 per team)")
        print(f"  Matches : {Match.query.count()} scheduled (round robin)")
        print("\nOwner logins (at /owner/login, password for all: owner123):")
        for t in Team.query.order_by(Team.name):
            print(f"  {t.short_name:4} {t.name:22} -> id: {t.short_name.lower()}")
        print("\nAdmin login -> username: admin  password: admin123")


if __name__ == "__main__":
    main()
