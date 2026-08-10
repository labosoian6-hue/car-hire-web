from app import app
from models import db, Booking

client = app.test_client()

# 1. Homepage loads
response = client.get("/")
assert response.status_code == 200
print("Homepage loads OK")

# 2. Submit a booking for car 1
response = client.post("/book/1", data={
    "name": "Test User",
    "email": "test@example.com",
    "phone": "0400000000",
    "start_date": "2026-09-01",
    "end_date": "2026-09-05",
}, follow_redirects=True)
assert response.status_code == 200
assert b"Booking confirmed" in response.data
print("Booking submitted OK")

# 3. Confirm it actually landed in the database
with app.app_context():
    latest = Booking.query.order_by(Booking.id.desc()).first()
    assert latest.start_date.isoformat() == "2026-09-01"
    print(f"Booking #{latest.id} found in database, confirmed")

print("\nALL TESTS PASSED")