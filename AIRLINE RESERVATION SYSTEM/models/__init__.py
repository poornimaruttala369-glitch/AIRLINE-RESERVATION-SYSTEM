"""
Models Package Initializer
Exports all domain classes for clear, concise imports.
"""
from models.user import User, Passenger, Admin
from models.aircraft import Aircraft
from models.seat import Seat
from models.flight import Flight
from models.booking import Booking, BookedSeat, Payment

__all__ = [
    'User',
    'Passenger',
    'Admin',
    'Aircraft',
    'Seat',
    'Flight',
    'Booking',
    'BookedSeat',
    'Payment'
]
