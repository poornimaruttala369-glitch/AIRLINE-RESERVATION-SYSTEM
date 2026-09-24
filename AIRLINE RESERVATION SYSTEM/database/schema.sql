-- ============================================================
-- ✈️ AIRLINE RESERVATION SYSTEM - DATABASE SCHEMA (3NF)
-- DBMS Concepts:
-- 1. Normalization (3NF)
-- 2. Primary Keys (PK) & Foreign Keys (FK) with Referential Integrity
-- 3. Check Constraints & Enums
-- 4. Unique Constraints & Composite Indexes
-- 5. Database-Level Double-Booking Prevention using Virtual Generated Column
-- ============================================================

CREATE DATABASE IF NOT EXISTS airline_reservation_db
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE airline_reservation_db;

-- ------------------------------------------------------------
-- Table 1: USERS
-- Stores credentials for both PASSENGER and ADMIN roles.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('PASSENGER', 'ADMIN') NOT NULL DEFAULT 'PASSENGER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_email (email),
    INDEX idx_user_role (role)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 2: AIRPORTS
-- Represents vertices V in the DMGT Route Graph.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS airports (
    airport_id INT AUTO_INCREMENT PRIMARY KEY,
    airport_code VARCHAR(10) NOT NULL UNIQUE,
    airport_name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    INDEX idx_airport_code (airport_code),
    INDEX idx_airport_city (city)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 3: AIRCRAFT
-- Defines physical fleet and configurable overbooking policies.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS aircraft (
    aircraft_id INT AUTO_INCREMENT PRIMARY KEY,
    aircraft_name VARCHAR(100) NOT NULL,
    model_number VARCHAR(50),
    total_seats INT NOT NULL,
    overbooking_percentage DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_total_seats CHECK (total_seats > 0),
    CONSTRAINT chk_overbooking_pct CHECK (overbooking_percentage >= 0.00 AND overbooking_percentage <= 50.00)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 4: SEATS
-- Physical seats mapped to each aircraft.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seats (
    seat_id INT AUTO_INCREMENT PRIMARY KEY,
    aircraft_id INT NOT NULL,
    seat_number VARCHAR(10) NOT NULL,
    seat_class ENUM('ECONOMY', 'BUSINESS') NOT NULL DEFAULT 'ECONOMY',
    seat_row INT NOT NULL,
    seat_col VARCHAR(2) NOT NULL,
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
    UNIQUE KEY uq_aircraft_seat (aircraft_id, seat_number),
    INDEX idx_seat_aircraft (aircraft_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 5: FLIGHTS
-- Scheduled flight routes connecting source and destination.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    flight_number VARCHAR(20) NOT NULL UNIQUE,
    source_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    aircraft_id INT NOT NULL,
    departure_time TIME NOT NULL,
    arrival_time TIME NOT NULL,
    travel_date DATE NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    status ENUM('SCHEDULED', 'DELAYED', 'COMPLETED', 'CANCELLED') NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id),
    CONSTRAINT chk_airports_diff CHECK (source_airport_id <> destination_airport_id),
    CONSTRAINT chk_base_price CHECK (base_price > 0),
    INDEX idx_flight_search (source_airport_id, destination_airport_id, travel_date),
    INDEX idx_flight_status (status)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 6: BOOKINGS
-- Reservation records with unique PNR and lifecycle status.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    flight_id INT NOT NULL,
    pnr VARCHAR(10) NOT NULL UNIQUE,
    passenger_name VARCHAR(100) NOT NULL,
    passenger_email VARCHAR(150) NOT NULL,
    passenger_phone VARCHAR(20) NOT NULL,
    booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('CONFIRMED', 'WAITLISTED', 'CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
    waitlist_position INT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE RESTRICT,
    INDEX idx_booking_pnr (pnr),
    INDEX idx_booking_user (user_id),
    INDEX idx_booking_flight (flight_id),
    INDEX idx_booking_status (status)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 7: BOOKED_SEATS
-- CORE DOUBLE-BOOKING PREVENTION MECHANISM:
-- Uses a virtual generated column `active_seat_flag`:
-- If status is 'ACTIVE', active_seat_flag = seat_id.
-- If status is 'CANCELLED', active_seat_flag = NULL.
-- Since MySQL unique keys allow multiple NULL values, cancelling releases
-- the seat immediately for re-booking while preserving the historical row!
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS booked_seats (
    booking_seat_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    flight_id INT NOT NULL,
    seat_id INT NOT NULL,
    seat_booking_status ENUM('ACTIVE', 'CANCELLED') NOT NULL DEFAULT 'ACTIVE',
    active_seat_flag INT GENERATED ALWAYS AS (IF(seat_booking_status = 'ACTIVE', seat_id, NULL)) VIRTUAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id) ON DELETE RESTRICT,
    FOREIGN KEY (seat_id) REFERENCES seats(seat_id) ON DELETE RESTRICT,
    UNIQUE KEY uq_flight_active_seat (flight_id, active_seat_flag),
    INDEX idx_booked_seat_flight (flight_id),
    INDEX idx_booked_seat_booking (booking_id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Table 8: PAYMENTS
-- Academic demonstration payment entity.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'DEMO_CARD',
    payment_status ENUM('PAID', 'PENDING', 'REFUNDED') NOT NULL DEFAULT 'PAID',
    transaction_ref VARCHAR(50) NOT NULL UNIQUE,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    INDEX idx_payment_booking (booking_id)
) ENGINE=InnoDB;
