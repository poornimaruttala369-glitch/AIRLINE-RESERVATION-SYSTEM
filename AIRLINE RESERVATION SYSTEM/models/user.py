"""
User Domain Models (OOPJ Concepts)
----------------------------------
Demonstrates:
- Base class 'User' and derived classes 'Passenger' and 'Admin' (Inheritance)
- Encapsulation of user attributes and role checks
- Polymorphism: specialized behavior per role
"""
from werkzeug.security import generate_password_hash, check_password_hash


class User:
    """Base User class representing any authenticated account."""
    def __init__(self, user_id, name, email, phone, role='PASSENGER', created_at=None):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.phone = phone
        self.role = role
        self.created_at = created_at

    def is_admin(self):
        """Check if user has administrative privileges."""
        return self.role == 'ADMIN'

    def is_passenger(self):
        """Check if user is a standard passenger."""
        return self.role == 'PASSENGER'

    def to_dict(self):
        """Encapsulate serialization to dictionary."""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'created_at': str(self.created_at) if self.created_at else None
        }

    @staticmethod
    def hash_password(plain_password):
        """Securely hash password using Werkzeug."""
        return generate_password_hash(plain_password)

    @staticmethod
    def verify_password(stored_hash, plain_password):
        """Verify plain password against stored hash."""
        return check_password_hash(stored_hash, plain_password)


class Passenger(User):
    """Passenger class inheriting from User."""
    def __init__(self, user_id, name, email, phone, created_at=None):
        super().__init__(user_id, name, email, phone, role='PASSENGER', created_at=created_at)

    def can_cancel_booking(self, booking_status):
        """Business logic for passenger cancellation rights."""
        return booking_status in ('CONFIRMED', 'WAITLISTED')


class Admin(User):
    """Administrator class inheriting from User with elevated privileges."""
    def __init__(self, user_id, name, email, phone, created_at=None):
        super().__init__(user_id, name, email, phone, role='ADMIN', created_at=created_at)

    def can_manage_fleet(self):
        return True

    def can_configure_overbooking(self):
        return True
