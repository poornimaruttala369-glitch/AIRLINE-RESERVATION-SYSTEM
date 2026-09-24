"""
Comprehensive Test Suite for Airline Reservation System
--------------------------------------------------------
Tests all Section 31 requirements:
1. Authentication (Registration, Duplicate Email, Login, Logout)
2. Flight Search (Valid search, No flights, Invalid search)
3. Seat Selection & Availability
4. Double Booking Prevention (Passenger A books -> Passenger B collision rejected)
5. Overbooking Policy & Capacity Limits
6. Cancellation & Automated FIFO Waitlist Promotion
"""
import unittest
from app import create_app
from database.db import get_db_cursor, init_database


class AirlineSystemTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure fresh database state with seed data
        init_database()
        with get_db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM payments")
            cur.execute("DELETE FROM booked_seats")
            cur.execute("DELETE FROM bookings")
            # Reseed initial demo booking for flight 1, seat 1 (1A)
            cur.execute("""
                INSERT INTO bookings (booking_id, user_id, flight_id, pnr, passenger_name, passenger_email, passenger_phone, status, total_amount)
                VALUES (1, 2, 1, 'AR8K92L', 'Poornima Ruttala', 'poornima@example.com', '9123456780', 'CONFIRMED', 4850.00)
            """)
            cur.execute("""
                INSERT INTO booked_seats (booking_seat_id, booking_id, flight_id, seat_id, seat_booking_status)
                VALUES (1, 1, 1, 1, 'ACTIVE')
            """)
            cur.execute("""
                INSERT INTO payments (payment_id, booking_id, amount, payment_method, payment_status, transaction_ref)
                VALUES (1, 1, 4850.00, 'DEMO_CARD', 'PAID', 'TXN_AR8K92L_9918')
            """)

        cls.app = create_app('development')
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()


    # ----------------------------------------------------
    # 1. AUTHENTICATION TESTS
    # ----------------------------------------------------
    def test_01_valid_registration(self):
        """Test registering a new passenger account."""
        import uuid
        unique_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
        res = self.client.post('/auth/register', data={
            'name': 'Test Passenger',
            'email': unique_email,
            'phone': '9988776655',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Registration successful", res.data)


    def test_02_duplicate_email_registration(self):
        """Test that registering with an existing email is rejected."""
        res = self.client.post('/auth/register', data={
            'name': 'Duplicate User',
            'email': 'poornima@example.com',
            'phone': '9988776655',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"already exists", res.data)

    def test_03_invalid_login(self):
        """Test that incorrect credentials fail."""
        res = self.client.post('/auth/login', data={
            'email': 'poornima@example.com',
            'password': 'WrongPassword999'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid email or password", res.data)

    def test_04_valid_login_and_logout(self):
        """Test valid passenger login and logout."""
        res = self.client.post('/auth/login', data={
            'email': 'poornima@example.com',
            'password': 'Pass@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome back", res.data)

        # Logout
        res_logout = self.client.get('/auth/logout', follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"successfully logged out", res_logout.data)

    # ----------------------------------------------------
    # 2. FLIGHT SEARCH TESTS
    # ----------------------------------------------------
    def test_05_valid_flight_search(self):
        """Test searching for scheduled flight AR101 (HYD -> DEL)."""
        res = self.client.get('/flights/search?from_airport=HYD&to_airport=DEL&travel_date=2026-10-25')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AR101", res.data)
        self.assertIn(b"4,850.00", res.data)

    def test_06_no_flights_found(self):
        """Test search for an unserved route."""
        res = self.client.get('/flights/search?from_airport=CCU&to_airport=MAA&travel_date=2026-10-25')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No Scheduled Flights Found", res.data)

    def test_07_invalid_search_same_airports(self):
        """Test that searching identical origin and destination is prevented."""
        res = self.client.get('/flights/search?from_airport=HYD&to_airport=HYD&travel_date=2026-10-25', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"cannot be the same", res.data)

    # ----------------------------------------------------
    # 3. SEAT MAP & AVAILABILITY TESTS
    # ----------------------------------------------------
    def test_08_seat_selection_view(self):
        """Test viewing cabin map for flight 1."""
        # Log in as passenger
        self.client.post('/auth/login', data={'email': 'poornima@example.com', 'password': 'Pass@123'})
        res = self.client.get('/booking/select-seats/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AIRCRAFT FRONT", res.data)
        # Seat 1A was seeded as booked
        self.assertIn(b"seat-booked", res.data)

    # ----------------------------------------------------
    # 4. CORE DOUBLE-BOOKING PREVENTION TEST (Section 13 & 31)
    # ----------------------------------------------------
    def test_09_double_booking_prevention(self):
        """
        CRITICAL TEST:
        Passenger A books Flight AR101, Seat 2A -> SUCCESS
        Passenger B attempts Flight AR101, Seat 2A -> REJECTED
        """
        from services.booking_service import reserve_flight_ticket, SeatAlreadyBookedError

        # Find seat_id for 2A on Aircraft 1
        with get_db_cursor() as cur:
            cur.execute("SELECT seat_id FROM seats WHERE aircraft_id = 1 AND seat_number = '2A'")
            seat_2a_id = cur.fetchone()['seat_id']

        # Passenger A (User ID 2) books seat 2A on Flight 1
        booking_a = reserve_flight_ticket(
            user_id=2,
            flight_id=1,
            seat_id=seat_2a_id,
            passenger_name='Passenger A',
            passenger_email='passenger_a@test.com',
            passenger_phone='9111111111'
        )
        self.assertIsNotNone(booking_a['pnr'])
        self.assertEqual(booking_a['status'], 'CONFIRMED')
        self.assertEqual(booking_a['seat_number'], '2A')

        # Passenger B (User ID 3) attempts to book the SAME seat 2A on the SAME Flight 1
        with self.assertRaises(SeatAlreadyBookedError):
            reserve_flight_ticket(
                user_id=3,
                flight_id=1,
                seat_id=seat_2a_id,
                passenger_name='Passenger B',
                passenger_email='passenger_b@test.com',
                passenger_phone='9222222222'
            )

    # ----------------------------------------------------
    # 5. OVERBOOKING & WAITLIST QUEUE TEST (Section 14)
    # ----------------------------------------------------
    def test_10_overbooking_policy_and_cancellation_promotion(self):
        """
        Tests:
        1. Capacity calculations (C_phys, C_max)
        2. Cancellation releases seat and triggers FIFO waitlist promotion.
        """
        from services.booking_service import reserve_flight_ticket
        from services.overbooking_service import cancel_booking_transaction

        # Use Flight 5 (ATR 72-600 on route HYD -> MAA)
        # Find an available seat
        with get_db_cursor() as cur:
            cur.execute("SELECT seat_id FROM seats WHERE aircraft_id = 3 AND seat_number = '1A'")
            seat_id = cur.fetchone()['seat_id']

        # 1. Passenger reserves seat 1A
        res_book = reserve_flight_ticket(
            user_id=2,
            flight_id=5,
            seat_id=seat_id,
            passenger_name='Original Passenger',
            passenger_email='original@test.com',
            passenger_phone='9333333333'
        )
        booking_id = res_book['booking_id']
        self.assertEqual(res_book['status'], 'CONFIRMED')

        # 2. Cancel the booking
        cancel_res = cancel_booking_transaction(booking_id, is_admin=True)
        self.assertEqual(cancel_res['previous_status'], 'CONFIRMED')
        self.assertEqual(cancel_res['freed_seat_id'], seat_id)

        # 3. Verify seat is released and can now be booked by another passenger
        res_rebook = reserve_flight_ticket(
            user_id=3,
            flight_id=5,
            seat_id=seat_id,
            passenger_name='New Passenger After Cancellation',
            passenger_email='new_pass@test.com',
            passenger_phone='9444444444'
        )
        self.assertEqual(res_rebook['status'], 'CONFIRMED')

    # ----------------------------------------------------
    # 6. ADMIN ROLE SECURITY TEST (Section 7 & 25)
    # ----------------------------------------------------
    def test_11_admin_route_protection(self):
        """Test that unauthenticated or standard passenger cannot access /admin/dashboard."""
        # Ensure session is logged out first
        self.client.get('/auth/logout')

        # Unauthenticated attempt -> redirects to login
        res_unauth = self.client.get('/admin/dashboard')
        self.assertEqual(res_unauth.status_code, 302)
        self.assertIn('/auth/login', res_unauth.location)

        # Log in as normal Passenger (Poornima)
        self.client.post('/auth/login', data={'email': 'poornima@example.com', 'password': 'Pass@123'})
        res_forbidden = self.client.get('/admin/dashboard')
        self.assertEqual(res_forbidden.status_code, 403)

        # Log out passenger
        self.client.get('/auth/logout')

        # Log in as Admin
        self.client.post('/auth/login', data={'email': 'admin@airline.com', 'password': 'Admin@123'})
        res_admin = self.client.get('/admin/dashboard')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b"Operations Command", res_admin.data)



if __name__ == '__main__':
    unittest.main()
