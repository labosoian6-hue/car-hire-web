import os
from dotenv import load_dotenv
load_dotenv()

from app import app
from models import db, AdminUser

with app.app_context():
    db.create_all()

    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "changeme123")

    if AdminUser.query.filter_by(username=username).first():
        print("Admin user already exists.")
    else:
        user = AdminUser(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Created admin user '{username}' — password set from environment.")