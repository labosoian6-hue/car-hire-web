import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Car, Renter, Booking, AdminUser, Payment

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///carhire.db"
db.init_app(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-fallback-key")

login_manager = LoginManager(app)
login_manager.login_view = "admin_login"

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

@app.route("/book/<int:car_id>", methods=["GET", "POST"])
def book_car(car_id):
    car = Car.query.get_or_404(car_id)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        start = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
        end = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

        if not car.is_available(start, end):
            return "Sorry, this car is already booked for part of that date range.", 409

        renter = Renter(name=name, email=email, phone=phone)
        db.session.add(renter)
        db.session.commit()

        booking = Booking(car_id=car.id, renter_id=renter.id, start_date=start, end_date=end)
        db.session.add(booking)
        db.session.commit()

        return f"Booking confirmed for {car.make} {car.model}, {start} to {end}!"

    return render_template("book.html", car=car)
@app.route("/")
def home():
    cars = Car.query.all()
    return render_template("home.html", cars=cars)
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin_home"))
        return "Invalid username or password", 401
    return render_template("admin_login.html")


@app.route("/admin")
@login_required
def admin_home():
    return render_template("admin_home.html")


@app.route("/admin/bookings")
@login_required
def admin_bookings():
    bookings = Booking.query.all()
    return render_template("admin_bookings.html", bookings=bookings)


@app.route("/admin/bookings/<int:booking_id>", methods=["GET", "POST"])
@login_required
def admin_booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if request.method == "POST":
        amount = float(request.form.get("amount"))
        payment = Payment(booking_id=booking.id, amount=amount)
        db.session.add(payment)
        db.session.commit()

    return render_template("admin_booking_detail.html", booking=booking)


@app.route("/admin/bookings/<int:booking_id>/approve", methods=["POST"])
@login_required
def admin_booking_approve(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "approved"
    db.session.commit()
    return redirect(url_for("admin_bookings"))

if __name__ == "__main__":
    app.run(debug=True)

