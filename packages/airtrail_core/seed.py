import os
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from packages.airtrail_core.models import Base, MonitoringSite, PollutionObservation

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://airtrail:password@localhost:5432/airtrail")

def seed_db():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    if session.query(MonitoringSite).count() > 0:
        print("Database already seeded.")
        return

    print("Seeding dummy data...")
    # Add a dummy monitoring site
    site = MonitoringSite(name="Downtown Station", location="SRID=4326;POINT(-122.4194 37.7749)")
    session.add(site)
    session.commit()

    # Add dummy observations for the last 24 hours
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for i in range(24):
        obs_time = now - timedelta(hours=i)
        obs = PollutionObservation(
            site_id=site.id,
            timestamp=obs_time,
            pollutant="PM2.5",
            value=random.uniform(5.0, 35.0),
            unit="ug/m3"
        )
        session.add(obs)

    session.commit()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()
