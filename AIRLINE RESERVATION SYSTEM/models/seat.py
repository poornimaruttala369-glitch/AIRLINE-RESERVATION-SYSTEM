"""
Seat Domain Model (OOPJ Concepts)
---------------------------------
Encapsulates individual seat properties, cabin positions, and cabin class.
"""


class Seat:
    """Represents a physical passenger seat on an aircraft."""
    def __init__(self, seat_id, aircraft_id, seat_number, seat_class='ECONOMY', seat_row=1, seat_col='A', status='AVAILABLE'):
        self.seat_id = seat_id
        self.aircraft_id = aircraft_id
        self.seat_number = seat_number
        self.seat_class = seat_class
        self.seat_row = int(seat_row)
        self.seat_col = str(seat_col).upper()
        self.status = status  # AVAILABLE, BOOKED, SELECTED

    def is_available(self):
        return self.status == 'AVAILABLE'

    def is_booked(self):
        return self.status == 'BOOKED'

    def is_window(self):
        return self.seat_col in ('A', 'F')

    def is_aisle(self):
        return self.seat_col in ('C', 'D')

    def to_dict(self):
        return {
            'seat_id': self.seat_id,
            'aircraft_id': self.aircraft_id,
            'seat_number': self.seat_number,
            'seat_class': self.seat_class,
            'seat_row': self.seat_row,
            'seat_col': self.seat_col,
            'status': self.status,
            'is_window': self.is_window(),
            'is_aisle': self.is_aisle()
        }
