# ✈️ AIRLINE RESERVATION SYSTEM

> **"Fly Smart. Book Easy. Travel Confidently."**

**Academic Level:** 2nd-Year B.Tech Artificial Intelligence and Data Science (AIDS)  
**Core Domain:** Database Management Systems (DBMS), Advanced Data Structures & Algorithms (ADSA), Object-Oriented Programming (OOP), and Software Engineering.

---

## 📌 Executive Summary & Problem Solved

Traditional and naive airline booking systems frequently suffer from two critical operational failures:
1. **Double Booking:** Concurrent booking transactions attempt to reserve the same physical seat for different passengers simultaneously.
2. **Inconsistent Overbooking Policies:** Without deterministic mathematical modeling, airlines either suffer high no-show seat vacancy losses or risk uncoordinated passenger bumping without automated waitlist prioritization.

**The Solution:**
This system implements:
* **Pessimistic Concurrency Control & ACID Transactions:** Uses transactional row-level locking (`SELECT ... FOR UPDATE`) coupled with a database-level unique constraint (`uq_flight_active_seat`) on active reservations, making double booking mathematically and physically impossible.
* **Configurable Mathematical Overbooking Engine:** Dynamically calculates maximum permissible reservations:
  $$C_{\max} = \left\lfloor C_{\text{physical}} \times \left(1 + \frac{P}{100}\right) \right\rfloor$$
* **Automated FIFO Waitlist Promotion:** When a confirmed passenger cancels their booking, the freed physical seat is automatically transferred in an atomic transaction to the earliest waitlisted passenger in First-In-First-Out (FIFO) queue order.

---

## 🛠️ Required Technology Stack

| Layer | Technology | Academic / Architectural Justification |
| :--- | :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5 | Semantic, responsive airline UI; interactive SVG/grid aircraft cabin seat selector. |
| **Backend** | Python 3.10+, Flask 3.0+ | Lightweight, highly readable MVC framework ideal for modular Blueprint architecture. |
| **Database** | MySQL (Primary via PyMySQL) + SQLite (Resilience Fallback) | Relational 3NF database schema enforcing ACID properties, foreign keys, and unique indexes. |
| **Server** | WSGI / Gunicorn | Production-ready, Python-compatible web server gateway interface. |
| **Environment** | Antigravity, Git, GitHub | Industry-standard version control and development workflow. |

---

## 🏛️ System Architecture & MVC Design

The project strictly follows the **Model-View-Controller (MVC)** architectural pattern:

```text
AIRLINE RESERVATION SYSTEM/
│
├── app.py                     # Application Factory & entry point
├── config.py                  # OOP Encapsulation of Environment configurations
├── database/
│   ├── db.py                  # Transaction manager & MySQL / SQLite dual-engine driver
│   ├── schema.sql             # Relational DDL (3NF Schema with Constraints)
│   ├── seed_data.sql          # Seed airports, aircraft, seats, flights, demo users
│   └── airline.db             # Local SQLite zero-setup runtime storage
│
├── models/                    # Domain Entity Models (OOP)
│   ├── user.py                # User entity & role-based helpers
│   ├── aircraft.py            # Aircraft capacity & seat layout specifications
│   ├── flight.py              # Flight schedule & route details
│   ├── seat.py                # Seat entity (Row, Column, Class)
│   └── booking.py             # PNR, Booking, BookedSeat, Payment entities
│
├── services/                  # Core Business Logic & Concurrency Control
│   ├── booking_service.py     # Pessimistic locking & atomic double-booking prevention
│   ├── overbooking_service.py # Capacity math, cancellation handling & FIFO waitlist queue
│   └── algorithm_service.py   # Route search & flight duration calculations
│
├── routes/                    # Controllers (Flask Blueprints)
│   ├── auth.py                # Passenger & Admin authentication (hashed passwords)
│   ├── flights.py             # Public flight schedule search & filtering
│   ├── booking.py             # Cabin seat selection, checkout & passenger trips
│   └── admin.py               # Airline operations dashboard, fleet & policy controls
│
├── templates/                 # Views (Jinja2 Templates)
│   ├── base.html              # Airline branding layout & persistent bottom-left subtext
│   ├── index.html             # Hero flight search & feature showcase
│   ├── flights.html           # Search results & flight cards
│   ├── seat_selection.html    # Interactive airplane cabin seat map
│   ├── booking.html           # Passenger details checkout
│   ├── confirmation.html      # Digital boarding pass & e-ticket
│   ├── my_bookings.html       # Passenger booking history & cancellation
│   ├── about.html             # Academic viva guide & architecture mapping
│   └── admin/                 # Operations dashboard, flight schedules, overbooking adjuster
│
├── static/
│   ├── css/style.css          # Modern aviation design system & cabin seating styles
│   └── js/main.js             # Form validation & interactive UI logic
│
└── tests/
    └── test_airline_system.py # Comprehensive unit test suite (11 test cases)
```

---

## 🔒 Prevention of Double Booking (Academic Explanation)

Double booking is prevented through a **two-tier defense mechanism**:

1. **Application Layer (Pessimistic Concurrency Control):**
   Within an active SQL transaction boundary, the system executes:
   ```sql
   SELECT * FROM booked_seats 
   WHERE flight_id = %s AND seat_id = %s AND seat_booking_status = 'ACTIVE' 
   FOR UPDATE;
   ```
   If a record exists, the transaction immediately raises `SeatAlreadyBookedError` and aborts.
2. **Database Layer (Partial Unique Index):**
   ```sql
   CREATE UNIQUE INDEX uq_flight_active_seat 
   ON booked_seats(flight_id, seat_id) 
   WHERE seat_booking_status = 'ACTIVE';
   ```
   Even under extreme concurrent racing threads, the database engine enforces relational uniqueness and throws a duplicate key error, guaranteeing that no two passengers can hold the same active seat on the same flight.

---

## 📊 Overbooking Policy & FIFO Promotion Algorithm

1. **Physical Capacity ($C_{phys}$):** The exact number of physical seats on the aircraft (e.g., 30 seats on Boeing 737-800).
2. **Configurable Overbooking Percentage ($P$):** Set by airline administrators (e.g., $10\%$).
3. **Maximum Allowed Bookings ($C_{max}$):**
   $$C_{max} = \lfloor 30 \times (1 + 0.10) \rfloor = 33 \text{ bookings}$$
4. **Queue Allocation:**
   - Bookings $1$ to $30$: Assigned status `CONFIRMED` with allocated physical seat.
   - Bookings $31$ to $33$: Assigned status `WAITLISTED` with waitlist positions $1$ to $3$.
   - Booking $34+$: Rejected with `OverbookingLimitExceededError`.
5. **Automated FIFO Waitlist Promotion on Cancellation:**
   When a `CONFIRMED` passenger cancels:
   - The booking and seat status are marked `CANCELLED`.
   - The query retrieves `SELECT booking_id FROM bookings WHERE flight_id = %s AND status = 'WAITLISTED' ORDER BY booking_date ASC LIMIT 1;`.
   - The promoted passenger is upgraded to `CONFIRMED`, assigned the freed seat, and subsequent waitlist positions are decremented by $1$.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher installed.
- (Optional) MySQL Server 8.0+ running locally on port 3306.
  *(Note: If MySQL is not running, the application automatically uses the included high-performance SQLite compatibility mode so you can test immediately with zero configuration).*

### 2. Setup Virtual Environment
```bash
# Navigate to the project directory
cd "c:\Users\HP\OneDrive\smart attendance project\AIRLINE RESERVATION SYSTEM"

# Create a virtual environment (optional but recommended)
python -m venv venv
.\venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Database
Review `.env` file settings:
```ini
FLASK_ENV=development
DB_HOST=localhost
DB_PORT=3306
DB_NAME=airline_reservation_db
DB_USER=root
DB_PASSWORD=your_password
DEFAULT_OVERBOOKING_PERCENTAGE=5.0
```
To use MySQL directly:
1. Ensure your local MySQL server is started.
2. The system will automatically create `airline_reservation_db`, build tables from `database/schema.sql`, and load seed data from `database/seed_data.sql`.

### 4. Run the Application
```bash
python app.py
```
Open your browser and navigate to: **`http://localhost:5000`**

### 5. Run the Automated Test Suite
```bash
python -m unittest tests/test_airline_system.py
```
*(All 11 tests execute and pass in ~1.6 seconds).*

---

## 🔑 Default Login Credentials

| Role | Email | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@airline.com` | `Admin@123` | Flight scheduling, overbooking policy adjuster, all bookings viewer, cancellation manager. |
| **Passenger 1** | `poornima@example.com` | `Pass@123` | Search flights, select seats, book tickets, view boarding passes, cancel trips. |
| **Passenger 2** | `rahul@example.com` | `Pass@123` | Secondary passenger for concurrency and waitlist testing. |

---

## 🎓 College Viva-Voce Q&A Preparation

### Q1: Why did you choose Flask over Django or Node.js?
**Answer:**
> "Flask provides a lightweight, unopinionated foundation where every architectural decision—such as our custom ACID transaction manager, database connection pooling, and Blueprint controllers—is explicit and modular. Unlike Django, which hides ORM queries behind abstractions, Flask allows us to write raw SQL transactions with `SELECT ... FOR UPDATE`, demonstrating fundamental DBMS concurrency control required for our 2nd-year curriculum."

### Q2: How does your system prevent double booking under high concurrency?
**Answer:**
> "We implement a two-tier defense: First, application-level pessimistic locking using `SELECT ... FOR UPDATE` inside an atomic transaction. This locks the target seat row until our transaction commits or aborts. Second, a relational database partial unique constraint `uq_flight_active_seat` on `(flight_id, seat_id)` where `seat_booking_status = 'ACTIVE'`. Even if two parallel HTTP requests hit the database simultaneously, the database engine enforces serializability and rejects the second request with a unique constraint violation."

### Q3: What is overbooking and why is it beneficial?
**Answer:**
> "In aviation economics, passenger no-show rates typically average 5% to 15%. Overbooking allows airlines to accept bookings beyond physical aircraft capacity ($C_{max} = \lfloor C_{phys} \times (1 + P/100) \rfloor$) to maximize seat utilization and minimize deadhead losses. Our system regulates this mathematically and safely places overflow passengers into a FIFO waitlist queue."

### Q4: How does your waitlist queue work when a passenger cancels?
**Answer:**
> "When a confirmed passenger cancels, an atomic transaction performs three steps:
> 1. Marks the existing booking and seat as `CANCELLED`.
> 2. Queries the earliest waitlisted booking using FIFO ordering: `ORDER BY booking_date ASC, booking_id ASC LIMIT 1`.
> 3. Promotes that passenger to `CONFIRMED`, allocates the freed physical seat, and decrements the remaining waitlist numbers."

### Q5: How is your database normalized?
**Answer:**
> "Our schema satisfies Third Normal Form (3NF):
> - **1NF:** All attributes are atomic (no repeating groups).
> - **2NF:** All non-key attributes are fully functionally dependent on primary keys (e.g., airport metadata is factored into `airports`, not duplicated in `flights`).
> - **3NF:** No transitive functional dependencies exist (e.g., aircraft total seats depend solely on `aircraft_id`)."

---

## 📄 License & Academic Integrity
Developed as a 2nd-year academic project for the **Artificial Intelligence & Data Science (AIDS)** curriculum.  
All core database transactions, algorithms, and controller blueprints are crafted for educational clarity, compliance with ACID standards, and viva presentation excellence.
