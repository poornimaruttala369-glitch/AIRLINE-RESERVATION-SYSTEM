-- ============================================================
-- ✈️ AIRLINE RESERVATION SYSTEM - SEED DATA
-- Provides realistic initial data for demonstration & viva testing:
-- - Airports across key Indian metro hubs
-- - Aircraft with distinct cabin configurations
-- - Complete seat matrices (Rows & Columns)
-- - Demo Admin and Passenger accounts
-- - Sample scheduled flights
-- - Pre-existing sample bookings to showcase booked vs available seats
-- ============================================================

USE airline_reservation_db;

-- 1. Insert Airports (Graph Vertices)
INSERT INTO airports (airport_id, airport_code, airport_name, city) VALUES
(1, 'HYD', 'Rajiv Gandhi International Airport', 'Hyderabad'),
(2, 'DEL', 'Indira Gandhi International Airport', 'Delhi'),
(3, 'BOM', 'Chhatrapati Shivaji Maharaj International Airport', 'Mumbai'),
(4, 'BLR', 'Kempegowda International Airport', 'Bengaluru'),
(5, 'MAA', 'Chennai International Airport', 'Chennai'),
(6, 'CCU', 'Netaji Subhash Chandra Bose International Airport', 'Kolkata')
ON DUPLICATE KEY UPDATE airport_code=VALUES(airport_code);

-- 2. Insert Aircraft Fleet
-- Aircraft 1: Boeing 737-800 (30 seats: 5 rows x 6 cols, 10% overbooking -> max 33)
-- Aircraft 2: Airbus A320neo (24 seats: 4 rows x 6 cols, 5% overbooking -> max 25)
-- Aircraft 3: ATR 72-600 (16 seats: 4 rows x 4 cols, 0% overbooking -> max 16)
INSERT INTO aircraft (aircraft_id, aircraft_name, model_number, total_seats, overbooking_percentage) VALUES
(1, 'Boeing 737-800', 'B738-NG', 30, 10.00),
(2, 'Airbus A320neo', 'A20N-LEAP', 24, 5.00),
(3, 'ATR 72-600', 'AT76-PW127M', 16, 0.00)
ON DUPLICATE KEY UPDATE aircraft_name=VALUES(aircraft_name);

-- 3. Insert Seats for Aircraft 1 (30 Seats: 5 rows A-F; Rows 1-2 Business, Rows 3-5 Economy)
INSERT INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col) VALUES
(1, '1A', 'BUSINESS', 1, 'A'), (1, '1B', 'BUSINESS', 1, 'B'), (1, '1C', 'BUSINESS', 1, 'C'),
(1, '1D', 'BUSINESS', 1, 'D'), (1, '1E', 'BUSINESS', 1, 'E'), (1, '1F', 'BUSINESS', 1, 'F'),
(1, '2A', 'BUSINESS', 2, 'A'), (1, '2B', 'BUSINESS', 2, 'B'), (1, '2C', 'BUSINESS', 2, 'C'),
(1, '2D', 'BUSINESS', 2, 'D'), (1, '2E', 'BUSINESS', 2, 'E'), (1, '2F', 'BUSINESS', 2, 'F'),
(1, '3A', 'ECONOMY', 3, 'A'), (1, '3B', 'ECONOMY', 3, 'B'), (1, '3C', 'ECONOMY', 3, 'C'),
(1, '3D', 'ECONOMY', 3, 'D'), (1, '3E', 'ECONOMY', 3, 'E'), (1, '3F', 'ECONOMY', 3, 'F'),
(1, '4A', 'ECONOMY', 4, 'A'), (1, '4B', 'ECONOMY', 4, 'B'), (1, '4C', 'ECONOMY', 4, 'C'),
(1, '4D', 'ECONOMY', 4, 'D'), (1, '4E', 'ECONOMY', 4, 'E'), (1, '4F', 'ECONOMY', 4, 'F'),
(1, '5A', 'ECONOMY', 5, 'A'), (1, '5B', 'ECONOMY', 5, 'B'), (1, '5C', 'ECONOMY', 5, 'C'),
(1, '5D', 'ECONOMY', 5, 'D'), (1, '5E', 'ECONOMY', 5, 'E'), (1, '5F', 'ECONOMY', 5, 'F')
ON DUPLICATE KEY UPDATE seat_class=VALUES(seat_class);

-- Insert Seats for Aircraft 2 (24 Seats: 4 rows A-F; Row 1 Business, Rows 2-4 Economy)
INSERT INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col) VALUES
(2, '1A', 'BUSINESS', 1, 'A'), (2, '1B', 'BUSINESS', 1, 'B'), (2, '1C', 'BUSINESS', 1, 'C'),
(2, '1D', 'BUSINESS', 1, 'D'), (2, '1E', 'BUSINESS', 1, 'E'), (2, '1F', 'BUSINESS', 1, 'F'),
(2, '2A', 'ECONOMY', 2, 'A'), (2, '2B', 'ECONOMY', 2, 'B'), (2, '2C', 'ECONOMY', 2, 'C'),
(2, '2D', 'ECONOMY', 2, 'D'), (2, '2E', 'ECONOMY', 2, 'E'), (2, '2F', 'ECONOMY', 2, 'F'),
(2, '3A', 'ECONOMY', 3, 'A'), (2, '3B', 'ECONOMY', 3, 'B'), (2, '3C', 'ECONOMY', 3, 'C'),
(2, '3D', 'ECONOMY', 3, 'D'), (2, '3E', 'ECONOMY', 3, 'E'), (2, '3F', 'ECONOMY', 3, 'F'),
(2, '4A', 'ECONOMY', 4, 'A'), (2, '4B', 'ECONOMY', 4, 'B'), (2, '4C', 'ECONOMY', 4, 'C'),
(2, '4D', 'ECONOMY', 4, 'D'), (2, '4E', 'ECONOMY', 4, 'E'), (2, '4F', 'ECONOMY', 4, 'F')
ON DUPLICATE KEY UPDATE seat_class=VALUES(seat_class);

-- Insert Seats for Aircraft 3 (16 Seats: 4 rows A-D; All Economy 2-2 layout)
INSERT INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col) VALUES
(3, '1A', 'ECONOMY', 1, 'A'), (3, '1B', 'ECONOMY', 1, 'B'), (3, '1C', 'ECONOMY', 1, 'C'), (3, '1D', 'ECONOMY', 1, 'D'),
(3, '2A', 'ECONOMY', 2, 'A'), (3, '2B', 'ECONOMY', 2, 'B'), (3, '2C', 'ECONOMY', 2, 'C'), (3, '2D', 'ECONOMY', 2, 'D'),
(3, '3A', 'ECONOMY', 3, 'A'), (3, '3B', 'ECONOMY', 3, 'B'), (3, '3C', 'ECONOMY', 3, 'C'), (3, '3D', 'ECONOMY', 3, 'D'),
(3, '4A', 'ECONOMY', 4, 'A'), (3, '4B', 'ECONOMY', 4, 'B'), (3, '4C', 'ECONOMY', 4, 'C'), (3, '4D', 'ECONOMY', 4, 'D')
ON DUPLICATE KEY UPDATE seat_class=VALUES(seat_class);

-- 4. Insert Users (Admin & Sample Passengers)
-- Default passwords:
-- Admin: Admin@123
-- Passengers: Pass@123
INSERT INTO users (user_id, name, email, phone, password_hash, role) VALUES
(1, 'System Administrator', 'admin@airline.com', '9876543210', 'scrypt:32768:8:1$XCD4CpVqYVrUxoXQ$7d2875669db87e83489db1d6f28880c91097a196e7fbbf8fc8ec8a5359acba0d27ea631e35a9bf3eeb57dfa07120b3e5d1e0283e81e931d8b652368e35bd03b3', 'ADMIN'),
(2, 'Poornima Ruttala', 'poornima@example.com', '9123456780', 'scrypt:32768:8:1$XY3Ya5aSOhLHXtG0$904d4b183f4995901f4d69ee54112159cd07e51560cf777dcfd0e1ac595c54c689db55c9eee2ce467f1c537d32bf23f034460cde63e716c4bcec76a9833002c3', 'PASSENGER'),
(3, 'Rahul Sharma', 'rahul@example.com', '9123456781', 'scrypt:32768:8:1$XY3Ya5aSOhLHXtG0$904d4b183f4995901f4d69ee54112159cd07e51560cf777dcfd0e1ac595c54c689db55c9eee2ce467f1c537d32bf23f034460cde63e716c4bcec76a9833002c3', 'PASSENGER'),
(4, 'Aarti Patel', 'aarti@example.com', '9123456782', 'scrypt:32768:8:1$XY3Ya5aSOhLHXtG0$904d4b183f4995901f4d69ee54112159cd07e51560cf777dcfd0e1ac595c54c689db55c9eee2ce467f1c537d32bf23f034460cde63e716c4bcec76a9833002c3', 'PASSENGER')
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 5. Insert Flights
-- Includes exact reference flight AR101 (Hyderabad -> Delhi on 2026-10-25 at 08:00)
-- Plus popular routes on dynamic/demonstration dates
INSERT INTO flights (flight_id, flight_number, source_airport_id, destination_airport_id, aircraft_id, departure_time, arrival_time, travel_date, base_price, status) VALUES
(1, 'AR101', 1, 2, 1, '08:00:00', '10:15:00', '2026-10-25', 4850.00, 'SCHEDULED'),
(2, 'AR102', 2, 1, 1, '18:30:00', '20:45:00', '2026-10-25', 5100.00, 'SCHEDULED'),
(3, 'AR201', 3, 4, 2, '07:15:00', '09:00:00', '2026-10-25', 3600.00, 'SCHEDULED'),
(4, 'AR202', 4, 3, 2, '19:45:00', '21:30:00', '2026-10-25', 3800.00, 'SCHEDULED'),
(5, 'AR301', 1, 5, 3, '11:00:00', '12:15:00', '2026-10-25', 2900.00, 'SCHEDULED'),
(6, 'AR302', 5, 1, 3, '14:30:00', '15:45:00', '2026-10-25', 2950.00, 'SCHEDULED'),
(7, 'AR401', 2, 3, 1, '06:00:00', '08:10:00', '2026-10-25', 5400.00, 'SCHEDULED'),
(8, 'AR501', 4, 2, 1, '09:30:00', '12:15:00', '2026-10-25', 5800.00, 'SCHEDULED')
ON DUPLICATE KEY UPDATE base_price=VALUES(base_price);

-- 6. Insert Demonstration Booking for AR101
-- Pre-book seat 1A and 1B for passenger Poornima to demonstrate booked seats on the seat map
INSERT INTO bookings (booking_id, user_id, flight_id, pnr, passenger_name, passenger_email, passenger_phone, status, total_amount) VALUES
(1, 2, 1, 'AR8K92L', 'Poornima Ruttala', 'poornima@example.com', '9123456780', 'CONFIRMED', 4850.00)
ON DUPLICATE KEY UPDATE pnr=VALUES(pnr);

-- Reserve seat 1A (seat_id = 1) for flight 1 in booked_seats
INSERT INTO booked_seats (booking_seat_id, booking_id, flight_id, seat_id, seat_booking_status) VALUES
(1, 1, 1, 1, 'ACTIVE')
ON DUPLICATE KEY UPDATE seat_booking_status=VALUES(seat_booking_status);

-- Payment record for booking 1
INSERT INTO payments (payment_id, booking_id, amount, payment_method, payment_status, transaction_ref) VALUES
(1, 1, 4850.00, 'DEMO_CARD', 'PAID', 'TXN_AR8K92L_9918')
ON DUPLICATE KEY UPDATE payment_status=VALUES(payment_status);
