"""
Booking, BookedSeat, and Payment Domain Models (OOPJ Concepts)
--------------------------------------------------------------
Encapsulates passenger reservation lifecycle and financial state.
"""


class Booking:
    """Represents a passenger reservation with unique PNR."""
    def __init__(self, booking_id, user_id, flight_id, pnr, passenger_name, passenger_email,
                 passenger_phone, status='CONFIRMED', total_amount=0.0, waitlist_position=None,
                 booking_date=None, flight=None, seats=None):
        self.booking_id = booking_id
        self.user_id = user_id
        self.flight_id = flight_id
        self.pnr = str(pnr).upper()
        self.passenger_name = passenger_name
        self.passenger_email = passenger_email
        self.passenger_phone = passenger_phone
        self.status = status  # CONFIRMED, WAITLISTED, CANCELLED
        self.total_amount = float(total_amount)
        self.waitlist_position = waitlist_position
        self.booking_date = str(booking_date) if booking_date else None
        
        # Associated flight and seat objects
        self.flight = flight
        self.seats = seats or []

    def is_confirmed(self):
        return self.status == 'CONFIRMED'

    def is_waitlisted(self):
        return self.status == 'WAITLISTED'

    def is_cancelled(self):
        return self.status == 'CANCELLED'

    @property
    def status_badge_class(self):
        """CSS class mapping for presentation."""
        mapping = {
            'CONFIRMED': 'badge-success',
            'WAITLISTED': 'badge-warning',
            'CANCELLED': 'badge-danger'
        }
        return mapping.get(self.status, 'badge-secondary')

    def to_dict(self):
        return {
            'booking_id': self.booking_id,
            'user_id': self.user_id,
            'flight_id': self.flight_id,
            'pnr': self.pnr,
            'passenger_name': self.passenger_name,
            'passenger_email': self.passenger_email,
            'passenger_phone': self.passenger_phone,
            'status': self.status,
            'waitlist_position': self.waitlist_position,
            'total_amount': self.total_amount,
            'booking_date': self.booking_date,
            'status_badge_class': self.status_badge_class
        }


class BookedSeat:
    """Represents the relationship between a booking, flight, and allocated physical seat."""
    def __init__(self, booking_seat_id, booking_id, flight_id, seat_id, seat_number=None, seat_class=None, seat_booking_status='ACTIVE'):
        self.booking_seat_id = booking_seat_id
        self.booking_id = booking_id
        self.flight_id = flight_id
        self.seat_id = seat_id
        self.seat_number = seat_number
        self.seat_class = seat_class
        self.seat_booking_status = seat_booking_status

    def is_active(self):
        return self.seat_booking_status == 'ACTIVE'


class Payment:
    """Academic demonstration payment entity."""
    def __init__(self, payment_id, booking_id, amount, transaction_ref, payment_status='PAID', payment_method='DEMO_CARD', payment_date=None):
        self.payment_id = payment_id
        self.booking_id = booking_id
        self.amount = float(amount)
        self.transaction_ref = transaction_ref
        self.payment_status = payment_status
        self.payment_method = payment_method
        self.payment_date = str(payment_date) if payment_date else None
