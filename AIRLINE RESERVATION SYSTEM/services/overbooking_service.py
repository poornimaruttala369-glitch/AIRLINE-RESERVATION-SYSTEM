"""
Overbooking & Cancellation Policy Engine
----------------------------------------
Academic Context:
- ADSA: FIFO Priority Queue for waitlist promotion
- DBMS: Cascading updates, seat status reclamation, and transaction safety
"""
from database.db import get_db_cursor


def cancel_booking_transaction(booking_id, requesting_user_id=None, is_admin=False):
    """
    Cancels a booking, releases the seat, and automatically promotes
    the next waitlisted passenger in FIFO order.
    Returns:
        dict: Result summary with status and whether promotion occurred.
    """
    with get_db_cursor(commit=True) as cur:
        # Fetch booking details
        cur.execute("""
            SELECT b.*, f.flight_number, f.flight_id, f.aircraft_id
            FROM bookings b
            JOIN flights f ON b.flight_id = f.flight_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        booking = cur.fetchone()

        if not booking:
            raise ValueError("Booking record not found.")

        # Permission check: If not admin, requesting_user_id must match booking.user_id
        if not is_admin and requesting_user_id and booking['user_id'] != requesting_user_id:
            raise PermissionError("You are not authorized to cancel this booking.")

        if booking['status'] == 'CANCELLED':
            raise ValueError("This booking is already cancelled.")

        previous_status = booking['status']
        flight_id = booking['flight_id']

        # Find the seat associated with this booking
        cur.execute("""
            SELECT * FROM booked_seats 
            WHERE booking_id = %s AND seat_booking_status = 'ACTIVE'
        """, (booking_id,))
        booked_seat_record = cur.fetchone()
        freed_seat_id = booked_seat_record['seat_id'] if booked_seat_record else None

        # 1. Update Booking status to CANCELLED
        cur.execute("""
            UPDATE bookings 
            SET status = 'CANCELLED' 
            WHERE booking_id = %s
        """, (booking_id,))

        # 2. Update booked_seats status to CANCELLED (releases unique constraint)
        if booked_seat_record:
            cur.execute("""
                UPDATE booked_seats 
                SET seat_booking_status = 'CANCELLED' 
                WHERE booking_seat_id = %s
            """, (booked_seat_record['booking_seat_id'],))

        # 3. Mark payment as REFUNDED
        cur.execute("""
            UPDATE payments 
            SET payment_status = 'REFUNDED' 
            WHERE booking_id = %s
        """, (booking_id,))

        promoted_pnr = None
        promoted_passenger = None

        # 4. FIFO WAITLIST PROMOTION:
        # If the cancelled booking held a physical seat (CONFIRMED) and freed a seat,
        # locate the earliest active WAITLISTED booking for this flight.
        if previous_status == 'CONFIRMED' and freed_seat_id:
            cur.execute("""
                SELECT booking_id, pnr, passenger_name 
                FROM bookings 
                WHERE flight_id = %s AND status = 'WAITLISTED'
                ORDER BY booking_date ASC, booking_id ASC 
                LIMIT 1
            """, (flight_id,))
            next_waitlisted = cur.fetchone()

            if next_waitlisted:
                promoted_id = next_waitlisted['booking_id']
                promoted_pnr = next_waitlisted['pnr']
                promoted_passenger = next_waitlisted['passenger_name']

                # Promote to CONFIRMED and clear waitlist position
                cur.execute("""
                    UPDATE bookings 
                    SET status = 'CONFIRMED', waitlist_position = NULL 
                    WHERE booking_id = %s
                """, (promoted_id,))

                # Allocate the newly freed seat to the promoted passenger
                cur.execute("""
                    INSERT INTO booked_seats (booking_id, flight_id, seat_id, seat_booking_status)
                    VALUES (%s, %s, %s, 'ACTIVE')
                """, (promoted_id, flight_id, freed_seat_id))

                # Update waitlist positions for remaining waitlisted passengers (decrement by 1)
                cur.execute("""
                    UPDATE bookings 
                    SET waitlist_position = waitlist_position - 1 
                    WHERE flight_id = %s AND status = 'WAITLISTED' AND waitlist_position > 1
                """, (flight_id,))

        return {
            'cancelled_pnr': booking['pnr'],
            'previous_status': previous_status,
            'freed_seat_id': freed_seat_id,
            'promoted_pnr': promoted_pnr,
            'promoted_passenger': promoted_passenger
        }


def get_flight_capacity_stats(flight_id):
    """
    Computes capacity and overbooking statistics for a flight.
    Used in Admin Dashboard & Flight management.
    """
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                f.flight_id, f.flight_number, f.base_price,
                a.aircraft_name, a.total_seats, a.overbooking_percentage,
                COUNT(CASE WHEN b.status = 'CONFIRMED' THEN 1 END) AS confirmed_count,
                COUNT(CASE WHEN b.status = 'WAITLISTED' THEN 1 END) AS waitlisted_count,
                COUNT(CASE WHEN b.status = 'CANCELLED' THEN 1 END) AS cancelled_count
            FROM flights f
            JOIN aircraft a ON f.aircraft_id = a.aircraft_id
            LEFT JOIN bookings b ON f.flight_id = b.flight_id
            WHERE f.flight_id = %s
            GROUP BY f.flight_id, f.flight_number, f.base_price, a.aircraft_name, a.total_seats, a.overbooking_percentage
        """, (flight_id,))
        row = cur.fetchone()

        if not row:
            return None

        total_seats = int(row['total_seats'])
        overbooking_pct = float(row['overbooking_percentage'])
        max_allowed = int(total_seats * (1.0 + (overbooking_pct / 100.0)))
        confirmed = int(row['confirmed_count'])
        waitlisted = int(row['waitlisted_count'])
        cancelled = int(row['cancelled_count'])
        total_active = confirmed + waitlisted
        available_seats = max(0, total_seats - confirmed)

        return {
            'flight_id': row['flight_id'],
            'flight_number': row['flight_number'],
            'aircraft_name': row['aircraft_name'],
            'physical_seats': total_seats,
            'overbooking_percentage': overbooking_pct,
            'max_allowed_reservations': max_allowed,
            'confirmed_bookings': confirmed,
            'waitlisted_bookings': waitlisted,
            'cancelled_bookings': cancelled,
            'total_active_reservations': total_active,
            'available_physical_seats': available_seats,
            'utilization_percent': round((confirmed / total_seats * 100) if total_seats > 0 else 0, 1),
            'is_fully_booked': total_active >= max_allowed
        }
