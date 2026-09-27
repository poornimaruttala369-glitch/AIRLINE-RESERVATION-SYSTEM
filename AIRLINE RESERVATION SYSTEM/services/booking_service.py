"""
Booking Service (Transaction Management & Double-Booking Prevention)
-------------------------------------------------------------------
Academic Context:
- DBMS: ACID Transactions (Atomicity, Consistency, Isolation, Durability)
- Concurrency Control: Pessimistic Row Locking (SELECT ... FOR UPDATE)
- Cryptographic / Unique PNR generation
"""
import random
import string
from database.db import get_db_cursor
from models.booking import Booking, BookedSeat, Payment


class BookingError(Exception):
    """Base exception for booking domain errors."""
    pass


class SeatAlreadyBookedError(BookingError):
    """Raised when a concurrent request attempts to reserve an occupied seat."""
    pass


class OverbookingLimitExceededError(BookingError):
    """Raised when total reservations exceed configured physical + overbooking capacity."""
    pass


def generate_unique_pnr(cursor):
    """
    Generates a unique 7-character airline PNR (e.g., 'AR8K92L').
    Ensures absolute uniqueness by querying the database.
    """
    chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'  # Excludes easily confused chars (0, O, 1, I)
    for _ in range(50):
        random_suffix = ''.join(random.choices(chars, k=5))
        pnr_candidate = f"AR{random_suffix}"
        cursor.execute("SELECT 1 FROM bookings WHERE pnr = %s", (pnr_candidate,))
        if not cursor.fetchone():
            return pnr_candidate
    raise BookingError("Unable to allocate a unique PNR. Please retry.")

def reserve_flight_ticket(
    user_id,
    flight_id,
    seat_id,
    passenger_name,
    passenger_email,
    passenger_phone,
    payment_method='DEMO_CARD'
):
    """
    Executes atomic, transaction-safe seat reservation.
    Follows Section 36 Strict Transaction Workflow:
    1. Start database transaction.
    2. Verify flight exists and is scheduled.
    3. Check aircraft capacity & overbooking policy.
    4. Verify seat belongs to the flight's aircraft.
    5. Verify seat is not already actively booked (Row Lock).
    6. Insert into bookings.
    7. Insert into booked_seats.
    8. Insert demo payment record.
    9. Commit transaction. If any failure occurs -> ROLL BACK.
    """
    with get_db_cursor(commit=True) as cur:
        # Step 2: Verify flight exists
        cur.execute("""
            SELECT f.*, a.aircraft_id, a.total_seats, a.overbooking_percentage
            FROM flights f
            JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            WHERE f.flight_id = %s AND f.status = 'SCHEDULED'
        """, (flight_id,))
        flight = cur.fetchone()
        if not flight:
            raise BookingError("Selected flight is unavailable or cancelled.")

        # Step 3: Check capacity & overbooking policy
        total_seats = int(flight['total_seats'])
        overbooking_pct = float(flight['overbooking_percentage'])
        max_allowed_capacity = int(total_seats * (1.0 + (overbooking_pct / 100.0)))

        # Count active bookings for this flight
        cur.execute("""
            SELECT COUNT(*) AS active_count 
            FROM bookings 
            WHERE flight_id = %s AND status IN ('CONFIRMED', 'WAITLISTED')
        """, (flight_id,))
        count_res = cur.fetchone()
        active_bookings = count_res['active_count'] if count_res else 0

        # Also count confirmed bookings specifically
        cur.execute("""
            SELECT COUNT(*) AS confirmed_count 
            FROM bookings 
            WHERE flight_id = %s AND status = 'CONFIRMED'
        """, (flight_id,))
        conf_res = cur.fetchone()
        confirmed_count = conf_res['confirmed_count'] if conf_res else 0

        if active_bookings >= max_allowed_capacity:
            raise OverbookingLimitExceededError(
                f"Flight is fully booked under the maximum capacity policy ({max_allowed_capacity} max allowed)."
            )

        # Step 4: Verify seat belongs to aircraft
        cur.execute("""
            SELECT * FROM seats 
            WHERE seat_id = %s AND aircraft_id = %s
        """, (seat_id, flight['aircraft_id']))
        seat = cur.fetchone()
        if not seat:
            raise BookingError("The selected seat does not exist on this aircraft.")

        # Step 5: CORE DOUBLE-BOOKING PREVENTION CHECK (Pessimistic lock)
        # Lock existing active record for this seat on this flight
        cur.execute("""
            SELECT * FROM booked_seats 
            WHERE flight_id = %s AND seat_id = %s AND seat_booking_status = 'ACTIVE'
            FOR UPDATE
        """, (flight_id, seat_id))
        existing_active = cur.fetchone()

        if existing_active:
            raise SeatAlreadyBookedError(
                f"Seat {seat['seat_number']} was just secured by another passenger. Please select another seat."
            )

        # Determine Booking Status (CONFIRMED vs WAITLISTED)
        # If confirmed count < total physical seats: CONFIRMED
        # Else: WAITLISTED
        if confirmed_count < total_seats:
            booking_status = 'CONFIRMED'
            waitlist_pos = None
        else:
            booking_status = 'WAITLISTED'
            # Waitlist position is active_bookings - total_seats + 1
            waitlist_pos = (active_bookings - total_seats) + 1

        # Step 6: Create Booking record with unique PNR
        pnr = generate_unique_pnr(cur)
        total_amount = float(flight['base_price'])
        # Add 20% surcharge for Business class
        if seat['seat_class'] == 'BUSINESS':
            total_amount *= 1.20

        cur.execute("""
            INSERT INTO bookings (user_id, flight_id, pnr, passenger_name, passenger_email, passenger_phone, status, waitlist_position, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, flight_id, pnr, passenger_name, passenger_email, passenger_phone, booking_status, waitlist_pos, total_amount))
        booking_id = cur.lastrowid

        # Step 7: Create BookedSeat record
        # Note: If status is CONFIRMED, seat is ACTIVE.
        # If waitlisted, seat record is created with ACTIVE or held in queue.
        # In our architecture, the specific physical seat is linked actively:
        try:
            cur.execute("""
                INSERT INTO booked_seats (booking_id, flight_id, seat_id, seat_booking_status)
                VALUES (%s, %s, %s, 'ACTIVE')
            """, (booking_id, flight_id, seat_id))
        except Exception as db_err:
            # Caught MySQL duplicate entry (1062) or SQLite unique constraint failure
            raise SeatAlreadyBookedError(
                f"Concurrent collision: Seat {seat['seat_number']} was claimed. Transaction rolled back safely."
            )

        # Step 8: Demo Payment settlement
        # Academic project only - no real financial transaction occurs.

        allowed_payment_methods = ('DEMO_CARD', 'DEMO_UPI')

        if payment_method not in allowed_payment_methods:
            raise BookingError("Invalid payment method selected.")

        txn_ref = f"TXN_{pnr}_{random.randint(1000, 9999)}"

        cur.execute("""
            INSERT INTO payments (
                booking_id,
                amount,
                payment_method,
                payment_status,
                transaction_ref
            )
            VALUES (%s, %s, %s, 'PAID', %s)
        """, (
            booking_id,
            total_amount,
            payment_method,
            txn_ref
        ))
        # Return booking summary dictionary
        return {
            'booking_id': booking_id,
            'pnr': pnr,
            'status': booking_status,
            'waitlist_position': waitlist_pos,
            'seat_number': seat['seat_number'],
            'seat_class': seat['seat_class'],
            'total_amount': total_amount,
            'flight_number': flight['flight_number'],
            'transaction_ref': txn_ref
        }
