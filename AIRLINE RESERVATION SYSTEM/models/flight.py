"""
Flight Domain Model (OOPJ Concepts)
-----------------------------------
Encapsulates scheduled flights, airport associations, and time formatting.
"""
from datetime import datetime, timedelta


class Flight:
    """Represents a scheduled commercial flight service."""
    def __init__(self, flight_id, flight_number, source_airport_id, destination_airport_id,
                 aircraft_id, departure_time, arrival_time, travel_date, base_price,
                 status='SCHEDULED', source_code=None, source_city=None,
                 dest_code=None, dest_city=None, aircraft_name=None, available_seats=None):
        self.flight_id = flight_id
        self.flight_number = flight_number
        self.source_airport_id = source_airport_id
        self.destination_airport_id = destination_airport_id
        self.aircraft_id = aircraft_id
        self.departure_time = str(departure_time)
        self.arrival_time = str(arrival_time)
        self.travel_date = str(travel_date)
        self.base_price = float(base_price)
        self.status = status
        
        # Joined airport and aircraft details
        self.source_code = source_code
        self.source_city = source_city
        self.dest_code = dest_code
        self.dest_city = dest_city
        self.aircraft_name = aircraft_name
        self.available_seats = available_seats

    @property
    def formatted_price(self):
        """Format price in Indian Rupees (INR)."""
        return f"₹{self.base_price:,.2f}"

    @property
    def formatted_dep_time(self):
        """Returns 12-hour or neat 24-hour time."""
        try:
            parts = self.departure_time.split(':')
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        except Exception:
            return self.departure_time

    @property
    def formatted_arr_time(self):
        try:
            parts = self.arrival_time.split(':')
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        except Exception:
            return self.arrival_time

    @property
    def duration_display(self):
        """Computes human-readable duration between departure and arrival."""
        try:
            dep_parts = [int(p) for p in self.departure_time.split(':')[:2]]
            arr_parts = [int(p) for p in self.arrival_time.split(':')[:2]]
            dep_min = dep_parts[0] * 60 + dep_parts[1]
            arr_min = arr_parts[0] * 60 + arr_parts[1]
            diff = arr_min - dep_min
            if diff < 0:
                diff += 24 * 60  # Next-day arrival
            hrs = diff // 60
            mins = diff % 60
            return f"{hrs}h {mins}m"
        except Exception:
            return "2h 15m"

    def to_dict(self):
        return {
            'flight_id': self.flight_id,
            'flight_number': self.flight_number,
            'source_code': self.source_code,
            'source_city': self.source_city,
            'dest_code': self.dest_code,
            'dest_city': self.dest_city,
            'departure_time': self.formatted_dep_time,
            'arrival_time': self.formatted_arr_time,
            'travel_date': self.travel_date,
            'base_price': self.base_price,
            'formatted_price': self.formatted_price,
            'duration': self.duration_display,
            'status': self.status,
            'aircraft_name': self.aircraft_name,
            'available_seats': self.available_seats
        }
