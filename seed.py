from app import app
from models import db, Car

with app.app_context():
    db.create_all()

    db.session.add(Car(make="Toyota", model="Corolla", day_rate=75))
    db.session.add(Car(make="Mazda", model="CX-5", day_rate=110))
    db.session.add(Car(make="Ford", model="Ranger", day_rate=140))
    db.session.commit()

    print("Database seeded!")