"""Reset the database and fill it with a demo tournament.

Run:  python seed.py
"""
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Player, Team, Match, Performance, Owner

random.seed(42)

TEAMS = [
    ("Mumbai Mavericks", "MM", "Rohit Enterprises"),
    ("Chennai Chargers", "CC", "Southern Sports Group"),
    ("Bangalore Blasters", "BB", "Garden City Holdings"),
    ("Kolkata Knights", "KK", "Eastern Star Media"),
    ("Delhi Daredevils", "DD", "Capital Ventures"),
    ("Punjab Panthers", "PP", "North Sports Co"),
    ("Rajasthan Royals", "RR", "Desert Kings Ltd"),
    ("Hyderabad Hawks", "HH", "Deccan Group"),
]

FIRST = ["Arjun", "Rahul", "Vikram", "Suresh", "Ramesh", "Karan", "Aditya", "Manish",
         "Sanjay", "Deepak", "Nikhil", "Rohan", "Varun", "Ajay", "Pranav", "Kunal",
         "Siddharth", "Harsh", "Yash", "Dev", "Ishan", "Shubham", "Tejas", "Om",
         "Abhishek", "Gaurav", "Mohit", "Naveen", "Parth", "Ritesh", "Sameer", "Tarun",
         "Umesh", "Vijay", "Akash", "Bharat", "Chirag", "Dhruv", "Eshan", "Farhan"]
LAST = ["Sharma", "Patel", "Singh", "Kumar", "Verma", "Reddy", "Nair", "Iyer",
        "Chopra", "Malhotra", "Gupta", "Joshi", "Desai", "Mehta", "Rao", "Menon"]
ROLES = ["Batsman", "Batsman", "Bowler", "Bowler", "All-rounder", "Wicketkeeper"]


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

        # 40 players; the first 32 join a team directly, the rest are free agents
        used_names = set()
        players = []
        while len(players) < 40:
            name = f"{random.choice(FIRST)} {random.choice(LAST)}"
            if name in used_names:
                continue
            used_names.add(name)
            p = Player(
                name=name,
                age=random.randint(18, 36),
                role=random.choice(ROLES),
            )
            db.session.add(p)
            players.append(p)
        db.session.flush()

        for i, p in enumerate(players[:32]):
            p.team_id = teams[i % len(teams)].id
        # rest stay free agents so the admin has someone to place

        # fixtures: everyone plays everyone once; first 6 matches completed
        from itertools import combinations
        start = date.today() - timedelta(days=12)
        fixtures = list(combinations(teams, 2))
        random.shuffle(fixtures)
        matches = []
        for i, (t1, t2) in enumerate(fixtures):
            m = Match(
                team1_id=t1.id, team2_id=t2.id,
                date=start + timedelta(days=i * 2),
                venue=f"{t1.short_name} Home Ground",
            )
            db.session.add(m)
            matches.append(m)
        db.session.flush()

        for m in matches[:6]:
            s1 = random.randint(130, 210)
            s2 = random.randint(120, 205)
            while s2 == s1:
                s2 = random.randint(120, 205)
            m.team1_runs, m.team1_wickets, m.team1_overs = s1, random.randint(3, 10), 20.0
            m.team2_runs, m.team2_wickets, m.team2_overs = s2, random.randint(3, 10), \
                20.0 if s2 < s1 else round(random.randint(17, 19) + random.randint(0, 5) / 10, 1)
            m.winner_id = m.team1_id if s1 > s2 else m.team2_id
            margin = abs(s1 - s2)
            m.summary = f"Won by {margin} runs" if s1 > s2 else f"Chased down with {margin} to spare"
            m.status = "completed"

            # performances for a few players from each side
            squad = Player.query.filter(Player.team_id.in_([m.team1_id, m.team2_id])).all()
            for p in random.sample(squad, min(6, len(squad))):
                runs = random.randint(0, 78)
                db.session.add(Performance(
                    match_id=m.id, player_id=p.id,
                    runs=runs, balls=max(1, int(runs / random.uniform(0.9, 1.8))),
                    wickets=random.choice([0, 0, 1, 1, 2, 3]),
                    runs_conceded=random.randint(12, 45),
                ))

        db.session.commit()

        print("Database seeded!")
        print(f"  Teams   : {Team.query.count()}")
        print(f"  Players : {Player.query.count()} (8 free agents)")
        print(f"  Matches : {Match.query.count()} (6 completed)")
        print("\nOwner logins (at /owner/login, password for all: owner123):")
        for t in Team.query.order_by(Team.name):
            print(f"  {t.short_name:4} {t.name:22} -> id: {t.short_name.lower()}")
        print("\nAdmin login -> username: admin  password: admin123")


if __name__ == "__main__":
    main()
