"""
Aircraft Domain Model (OOPJ Concepts)
-------------------------------------
Demonstrates encapsulation of fleet configuration and overbooking capacity logic.
"""
import math


class Aircraft:
    """Represents an airplane in the airline fleet."""
    def __init__(self, aircraft_id, aircraft_name, total_seats, overbooking_percentage=5.0, model_number=None):
        self.aircraft_id = aircraft_id
        self.aircraft_name = aircraft_name
        self.total_seats = int(total_seats)
        self.overbooking_percentage = float(overbooking_percentage)
        self.model_number = model_number

    @property
    def physical_capacity(self):
        """The actual physical seat count on the aircraft."""
        return self.total_seats

    @property
    def max_booking_capacity(self):
        """
        The maximum number of reservations permitted under configured overbooking policy.
        Formula: floor(physical_capacity * (1 + overbooking_percentage / 100))
        """
        return math.floor(self.total_seats * (1.0 + (self.overbooking_percentage / 100.0)))

    @property
    def max_overbooked_seats(self):
        """Number of seats permitted beyond physical capacity."""
        return self.max_booking_capacity - self.physical_capacity

    def to_dict(self):
        return {
            'aircraft_id': self.aircraft_id,
            'aircraft_name': self.aircraft_name,
            'model_number': self.model_number,
            'total_seats': self.total_seats,
            'overbooking_percentage': self.overbooking_percentage,
            'physical_capacity': self.physical_capacity,
            'max_booking_capacity': self.max_booking_capacity,
            'max_overbooked_seats': self.max_overbooked_seats
        }
