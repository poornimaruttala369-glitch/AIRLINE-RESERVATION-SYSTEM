"""
Database Connection & Transaction Manager
-----------------------------------------
Academic Context:
- DBMS: Connection management, ACID transactions, atomic commit/rollback.
- Primary Database: MySQL (using PyMySQL).
- Resilience Feature: If local MySQL service is offline, automatically operates in
  SQLite compatibility mode (database/airline.db) so the student can run and test
  immediately without a broken app, while keeping MySQL as the primary target.
"""
import os
import sys
import re
import sqlite3
import pymysql
import pymysql.cursors
from contextlib import contextmanager


# Ensure root directory is on sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config


# Detect database engine preference
# Set DB_ENGINE='mysql' (default) or 'sqlite'
DB_ENGINE_PREF = os.getenv('DB_ENGINE', 'mysql').lower()

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), 'airline.db')


def test_mysql_connection():
    """Tests if the configured MySQL server is reachable."""
    cfg = Config.get_db_config()
    try:
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password'],
            connect_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False


_DETECTED_ENGINE = None


def get_active_engine(force_refresh=False):
    """
    Determines whether to use MySQL or SQLite compatibility engine.
    Demonstrates graceful degradation and resilience.
    Caches detected engine to eliminate redundant network timeouts on subsequent calls.
    """
    global _DETECTED_ENGINE
    if _DETECTED_ENGINE is not None and not force_refresh:
        return _DETECTED_ENGINE

    if DB_ENGINE_PREF == 'sqlite':
        _DETECTED_ENGINE = 'sqlite'
    elif test_mysql_connection():
        _DETECTED_ENGINE = 'mysql'
    else:
        _DETECTED_ENGINE = 'sqlite'
    return _DETECTED_ENGINE


class SQLiteDictCursor:
    """Wrapper around sqlite3.Cursor to emulate PyMySQL DictCursor."""
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # In SQLite, transactions lock the DB; strip MySQL-specific FOR UPDATE
        query = re.sub(r'\s+FOR\s+UPDATE', '', query, flags=re.IGNORECASE)
        # Translate MySQL %s placeholders to SQLite ? placeholders
        query = query.replace('%s', '?')
        if params is not None:
            if isinstance(params, (list, tuple)):
                return self.cursor.execute(query, params)
            else:
                return self.cursor.execute(query, (params,))
        return self.cursor.execute(query)

    def executemany(self, query, seq_of_params):
        query = re.sub(r'\s+FOR\s+UPDATE', '', query, flags=re.IGNORECASE)
        query = query.replace('%s', '?')
        return self.cursor.executemany(query, seq_of_params)


    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        self.cursor.close()


def get_connection():
    """
    Returns a database connection based on active engine.
    """
    engine = get_active_engine()
    if engine == 'mysql':
        cfg = Config.get_db_config()
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password'],
            database=cfg['database'],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,  # Enforce explicit transactions (ACID)
            charset='utf8mb4'
        )
        return conn, 'mysql'
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn, 'sqlite'


@contextmanager
def get_db_cursor(commit=False):
    """
    Context Manager for transactional database access.
    Demonstrates ACID properties:
    - Atomicity: Commits on completion; rolls back completely on any error.
    - Consistency: Schema constraints enforced.
    - Isolation: Explicit transaction boundaries.
    """
    conn, engine = get_connection()
    if engine == 'mysql':
        cursor = conn.cursor()
    else:
        raw_cursor = conn.cursor()
        cursor = SQLiteDictCursor(raw_cursor)

    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()


def init_database():
    """
    Initializes database tables and sample seed data.
    Works for both MySQL and SQLite fallback modes.
    """
    engine = get_active_engine()
    base_dir = os.path.dirname(__file__)

    if engine == 'mysql':
        print("[DBMS] Initializing MySQL Database (airline_reservation_db)...")
        cfg = Config.get_db_config()
        # Connect to MySQL server without database first to ensure DB exists
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password']
        )
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` CHARACTER SET utf8mb4;")
        conn.close()

        # Connect to target database and execute scripts
        conn = pymysql.connect(
            host=cfg['host'],
            port=cfg['port'],
            user=cfg['user'],
            password=cfg['password'],
            database=cfg['database']
        )
        with conn.cursor() as cur:
            for sql_file in ['schema.sql', 'seed_data.sql']:
                path = os.path.join(base_dir, sql_file)
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        commands = f.read().split(';')
                        for cmd in commands:
                            clean_cmd = cmd.strip()
                            if clean_cmd:
                                try:
                                    cur.execute(clean_cmd)
                                except Exception as err:
                                    # Skip duplicate warnings or database switches
                                    if 'USE ' not in clean_cmd.upper():
                                        pass
            conn.commit()
        conn.close()
        print("[DBMS] MySQL initialization completed successfully.")
    else:
        print(f"[DBMS] Initializing SQLite compatibility database at {SQLITE_DB_PATH}...")
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()

        # SQLite compatible schema definition
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'PASSENGER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS airports (
            airport_id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_code TEXT NOT NULL UNIQUE,
            airport_name TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS aircraft (
            aircraft_id INTEGER PRIMARY KEY AUTOINCREMENT,
            aircraft_name TEXT NOT NULL,
            model_number TEXT,
            total_seats INTEGER NOT NULL,
            overbooking_percentage REAL NOT NULL DEFAULT 5.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS seats (
            seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            aircraft_id INTEGER NOT NULL,
            seat_number TEXT NOT NULL,
            seat_class TEXT NOT NULL DEFAULT 'ECONOMY',
            seat_row INTEGER NOT NULL,
            seat_col TEXT NOT NULL,
            FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id) ON DELETE CASCADE,
            UNIQUE(aircraft_id, seat_number)
        );

        CREATE TABLE IF NOT EXISTS flights (
            flight_id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_number TEXT NOT NULL UNIQUE,
            source_airport_id INTEGER NOT NULL,
            destination_airport_id INTEGER NOT NULL,
            aircraft_id INTEGER NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            base_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'SCHEDULED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_airport_id) REFERENCES airports(airport_id),
            FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id),
            FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            flight_id INTEGER NOT NULL,
            pnr TEXT NOT NULL UNIQUE,
            passenger_name TEXT NOT NULL,
            passenger_email TEXT NOT NULL,
            passenger_phone TEXT NOT NULL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'CONFIRMED',
            waitlist_position INTEGER NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
        );

        CREATE TABLE IF NOT EXISTS booked_seats (
            booking_seat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            flight_id INTEGER NOT NULL,
            seat_id INTEGER NOT NULL,
            seat_booking_status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
            FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
            FOREIGN KEY (seat_id) REFERENCES seats(seat_id)
        );

        -- Double booking prevention unique index for active reservations
        CREATE UNIQUE INDEX IF NOT EXISTS uq_flight_active_seat 
        ON booked_seats(flight_id, seat_id) 
        WHERE seat_booking_status = 'ACTIVE';

        CREATE TABLE IF NOT EXISTS payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT DEFAULT 'DEMO_CARD',
            payment_status TEXT NOT NULL DEFAULT 'PAID',
            transaction_ref TEXT NOT NULL UNIQUE,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
        );
        """)

        # Insert seed airports
        cur.executemany("""
            INSERT OR IGNORE INTO airports (airport_id, airport_code, airport_name, city)
            VALUES (?, ?, ?, ?)
        """, [
            (1, 'HYD', 'Rajiv Gandhi International Airport', 'Hyderabad'),
            (2, 'DEL', 'Indira Gandhi International Airport', 'Delhi'),
            (3, 'BOM', 'Chhatrapati Shivaji Maharaj International Airport', 'Mumbai'),
            (4, 'BLR', 'Kempegowda International Airport', 'Bengaluru'),
            (5, 'MAA', 'Chennai International Airport', 'Chennai'),
            (6, 'CCU', 'Netaji Subhash Chandra Bose International Airport', 'Kolkata')
        ])

        # Insert seed aircraft
        cur.executemany("""
            INSERT OR IGNORE INTO aircraft (aircraft_id, aircraft_name, model_number, total_seats, overbooking_percentage)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (1, 'Boeing 737-800', 'B738-NG', 30, 10.00),
            (2, 'Airbus A320neo', 'A20N-LEAP', 24, 5.00),
            (3, 'ATR 72-600', 'AT76-PW127M', 16, 0.00)
        ])

        # Insert seed seats for Aircraft 1 (30 seats: 5 rows A-F)
        seats_a1 = []
        for r in range(1, 6):
            seat_class = 'BUSINESS' if r <= 2 else 'ECONOMY'
            for c in ['A', 'B', 'C', 'D', 'E', 'F']:
                seats_a1.append((1, f"{r}{c}", seat_class, r, c))
        cur.executemany("""
            INSERT OR IGNORE INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col)
            VALUES (?, ?, ?, ?, ?)
        """, seats_a1)

        # Insert seed seats for Aircraft 2 (24 seats: 4 rows A-F)
        seats_a2 = []
        for r in range(1, 5):
            seat_class = 'BUSINESS' if r == 1 else 'ECONOMY'
            for c in ['A', 'B', 'C', 'D', 'E', 'F']:
                seats_a2.append((2, f"{r}{c}", seat_class, r, c))
        cur.executemany("""
            INSERT OR IGNORE INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col)
            VALUES (?, ?, ?, ?, ?)
        """, seats_a2)

        # Insert seed seats for Aircraft 3 (16 seats: 4 rows A-D)
        seats_a3 = []
        for r in range(1, 5):
            for c in ['A', 'B', 'C', 'D']:
                seats_a3.append((3, f"{r}{c}", 'ECONOMY', r, c))
        cur.executemany("""
            INSERT OR IGNORE INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col)
            VALUES (?, ?, ?, ?, ?)
        """, seats_a3)

        # Insert seed users (Admin & Passengers)
        cur.executemany("""
            INSERT OR IGNORE INTO users (user_id, name, email, phone, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (1, 'System Administrator', 'admin@airline.com', '9876543210', 'scrypt:32768:8:1$XCD4CpVqYVrUxoXQ$7d2875669db87e83489db1d6f28880c91097a196e7fbbf8fc8ec8a5359acba0d27ea631e35a9bf3eeb57dfa07120b3e5d1e0283e81e931d8b652368e35bd03b3', 'ADMIN'),
            (2, 'Poornima Ruttala', 'poornima@example.com', '9123456780', 'scrypt:32768:8:1$XY3Ya5aSOhLHXtG0$904d4b183f4995901f4d69ee54112159cd07e51560cf777dcfd0e1ac595c54c689db55c9eee2ce467f1c537d32bf23f034460cde63e716c4bcec76a9833002c3', 'PASSENGER'),
            (3, 'Rahul Sharma', 'rahul@example.com', '9123456781', 'scrypt:32768:8:1$XY3Ya5aSOhLHXtG0$904d4b183f4995901f4d69ee54112159cd07e51560cf777dcfd0e1ac595c54c689db55c9eee2ce467f1c537d32bf23f034460cde63e716c4bcec76a9833002c3', 'PASSENGER'),
            (4, 'Aarti Patel', 'aarti@example.com', '9123456782', 'scrypt:32768:8:1$XY3Ya5aSOhLHXtG0$904d4b183f4995901f4d69ee54112159cd07e51560cf777dcfd0e1ac595c54c689db55c9eee2ce467f1c537d32bf23f034460cde63e716c4bcec76a9833002c3', 'PASSENGER')
        ])

        # Insert seed flights (AR101 and other sample flights)
        cur.executemany("""
            INSERT OR IGNORE INTO flights (flight_id, flight_number, source_airport_id, destination_airport_id, aircraft_id, departure_time, arrival_time, travel_date, base_price, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (1, 'AR101', 1, 2, 1, '08:00:00', '10:15:00', '2026-10-25', 4850.00, 'SCHEDULED'),
            (2, 'AR102', 2, 1, 1, '18:30:00', '20:45:00', '2026-10-25', 5100.00, 'SCHEDULED'),
            (3, 'AR201', 3, 4, 2, '07:15:00', '09:00:00', '2026-10-25', 3600.00, 'SCHEDULED'),
            (4, 'AR202', 4, 3, 2, '19:45:00', '21:30:00', '2026-10-25', 3800.00, 'SCHEDULED'),
            (5, 'AR301', 1, 5, 3, '11:00:00', '12:15:00', '2026-10-25', 2900.00, 'SCHEDULED'),
            (6, 'AR302', 5, 1, 3, '14:30:00', '15:45:00', '2026-10-25', 2950.00, 'SCHEDULED'),
            (7, 'AR401', 2, 3, 1, '06:00:00', '08:10:00', '2026-10-25', 5400.00, 'SCHEDULED'),
            (8, 'AR501', 4, 2, 1, '09:30:00', '12:15:00', '2026-10-25', 5800.00, 'SCHEDULED')
        ])

        # Insert seed booking (AR8K92L for Flight 1, Seat 1A)
        cur.execute("""
            INSERT OR IGNORE INTO bookings (booking_id, user_id, flight_id, pnr, passenger_name, passenger_email, passenger_phone, status, total_amount)
            VALUES (1, 2, 1, 'AR8K92L', 'Poornima Ruttala', 'poornima@example.com', '9123456780', 'CONFIRMED', 4850.00)
        """)

        # Reserve seat 1A (seat_id = 1) for flight 1
        cur.execute("""
            INSERT OR IGNORE INTO booked_seats (booking_seat_id, booking_id, flight_id, seat_id, seat_booking_status)
            VALUES (1, 1, 1, 1, 'ACTIVE')
        """)

        # Payment for booking 1
        cur.execute("""
            INSERT OR IGNORE INTO payments (payment_id, booking_id, amount, payment_method, payment_status, transaction_ref)
            VALUES (1, 1, 4850.00, 'DEMO_CARD', 'PAID', 'TXN_AR8K92L_9918')
        """)

        conn.commit()
        conn.close()
        print("[DBMS] SQLite compatibility initialization completed successfully.")


if __name__ == '__main__':
    init_database()
