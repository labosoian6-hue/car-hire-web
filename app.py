import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from models import db, Car, Renter, Booking, AdminUser, Payment, CarPhoto
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///carhire.db"
db.init_app(app)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-fallback-key")

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")
mail = Mail(app)

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", os.environ.get("MAIL_USERNAME"))

login_manager = LoginManager(app)
login_manager.login_view = "admin_login"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "avif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def send_booking_emails(car, renter, booking):
    if renter.email:
        customer_msg = Message(
            subject=f"Booking request received - {car.make} {car.model}",
            recipients=[renter.email],
            body=(
                f"Hi {renter.name},\n\n"
                f"We've received your booking request for the {car.make} {car.model} "
                f"from {booking.start_date} to {booking.end_date}.\n\n"
                f"We'll be in touch once it's reviewed.\n\n"
                f"Thanks,\nIan's Car Hire"
            ),
        )
        mail.send(customer_msg)

    if ADMIN_EMAIL:
        admin_msg = Message(
            subject=f"New booking request - {car.make} {car.model}",
            recipients=[ADMIN_EMAIL],
            body=(
                f"New booking request:\n\n"
                f"Car: {car.make} {car.model}\n"
                f"Renter: {renter.name} ({renter.email or 'no email'}, {renter.phone or 'no phone'})\n"
                f"Dates: {booking.start_date} to {booking.end_date}\n\n"
                f"Review it in the admin dashboard."
            ),
        )
        mail.send(admin_msg)

def send_approval_email(car, renter, booking):
    if renter.email:
        details = f"\n\n{booking.notes}" if booking.notes else ""
        msg = Message(
            subject=f"Booking approved - {car.make} {car.model}",
            recipients=[renter.email],
            body=(
                f"Hi {renter.name},\n\n"
                f"Good news — your booking for the {car.make} {car.model} "
                f"from {booking.start_date} to {booking.end_date} has been approved."
                f"{details}\n\n"
                f"Thanks,\nIan's Car Hire"
            ),
        )
        mail.send(msg)

def send_update_email(car, renter, booking):
    if renter.email and booking.notes:
        msg = Message(
            subject=f"Booking update - {car.make} {car.model}",
            recipients=[renter.email],
            body=(
                f"Hi {renter.name},\n\n"
                f"Here's an update on your booking for the {car.make} {car.model} "
                f"from {booking.start_date} to {booking.end_date}:\n\n"
                f"{booking.notes}\n\n"
                f"Thanks,\nIan's Car Hire"
            ),
        )
        mail.send(msg)

with app.app_context():
    db.create_all()

    if not Car.query.first():
        db.session.add(Car(make="Toyota", model="Corolla", week_rate=350))
        db.session.add(Car(make="Mazda", model="CX-5", week_rate=550))
        db.session.add(Car(make="Ford", model="Ranger", week_rate=700))
        db.session.commit()
        print("Seeded initial cars.")

    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "changeme123")
    if not AdminUser.query.filter_by(username=admin_username).first():
        user = AdminUser(username=admin_username)
        user.set_password(admin_password)
        db.session.add(user)
        db.session.commit()
        print(f"Created admin user '{admin_username}'.")

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

        try:
            send_booking_emails(car, renter, booking)
        except Exception as e:
            print(f"Failed to send booking emails: {e}")

        return f"Booking confirmed for {car.make} {car.model}, {start} to {end}!"

    today = datetime.now().date()
    booked_ranges = sorted(
        [b for b in car.bookings if b.end_date >= today],
        key=lambda b: b.start_date
    )

    return render_template("book.html", car=car, booked_ranges=booked_ranges)

@app.route("/")
def home():
    cars = Car.query.all()
    return render_template("home.html", cars=cars)

@app.route("/cars/<int:car_id>")
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    return render_template("car_detail.html", car=car)

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

@app.route("/admin/bookings/<int:booking_id>/notes", methods=["POST"])
@login_required
def admin_booking_notes(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.notes = request.form.get("notes")
    db.session.commit()

    if booking.status == "approved":
        try:
            send_update_email(booking.car, booking.renter, booking)
        except Exception as e:
            print(f"Failed to send update email: {e}")

    return redirect(url_for("admin_booking_detail", booking_id=booking.id))

@app.route("/admin/bookings/<int:booking_id>/approve", methods=["POST"])
@login_required
def admin_booking_approve(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = "approved"
    db.session.commit()

    try:
        send_approval_email(booking.car, booking.renter, booking)
    except Exception as e:
        print(f"Failed to send approval email: {e}")

    return redirect(url_for("admin_bookings"))

@app.route("/admin/cars")
@login_required
def admin_cars():
    cars = Car.query.all()
    return render_template("admin_cars.html", cars=cars)

@app.route("/admin/cars/new", methods=["GET", "POST"])
@login_required
def admin_car_new():
    if request.method == "POST":
        car = Car(
            make=request.form.get("make"),
            model=request.form.get("model"),
            week_rate=float(request.form.get("week_rate")),
        )
        db.session.add(car)
        db.session.commit()

        photos = request.files.getlist("photos")
        for i, photo in enumerate(photos):
            if photo and photo.filename and allowed_file(photo.filename):
                filename = f"{car.id}_{i}_{secure_filename(photo.filename)}"
                photo.save(os.path.join(UPLOAD_FOLDER, filename))
                db.session.add(CarPhoto(car_id=car.id, filename=filename))
        db.session.commit()

        return redirect(url_for("admin_cars"))

    return render_template("admin_car_form.html")

@app.route("/admin/cars/<int:car_id>/delete", methods=["POST"])
@login_required
def admin_car_delete(car_id):
    car = Car.query.get_or_404(car_id)

    if car.bookings:
        return "Can't delete a car that has booking history.", 400

    for photo in car.photos:
        db.session.delete(photo)

    db.session.delete(car)
    db.session.commit()
    return redirect(url_for("admin_cars"))

if __name__ == "__main__":
    app.run(debug=True)