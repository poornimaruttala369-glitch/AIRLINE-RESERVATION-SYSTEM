"""
Admin Blueprint (Routes)
------------------------
Handles Fleet Management, Flight Scheduling, Overbooking Configuration,
Booking Oversight, and Revenue Reporting.
Academic Context:
- Security: Role-Based Authorization (@admin_required)
- DBMS: Aggregation queries (SUM, COUNT, GROUP BY), relational joins, administrative transactions.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.db import get_db_cursor
from routes.auth_helpers import admin_required
from services.overbooking_service import cancel_booking_transaction

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Main administrative dashboard with summary analytics."""
    try:
        with get_db_cursor() as cur:
            # 1. Metric: Total Flights
            cur.execute("SELECT COUNT(*) AS total_flights FROM flights")
            total_flights = cur.fetchone()['total_flights']

            # 2. Metric: Total Passengers
            cur.execute("SELECT COUNT(*) AS total_users FROM users WHERE role = 'PASSENGER'")
            total_users = cur.fetchone()['total_users']

            # 3. Booking Metrics
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_bookings,
                    COUNT(CASE WHEN status = 'CONFIRMED' THEN 1 END) AS confirmed_count,
                    COUNT(CASE WHEN status = 'WAITLISTED' THEN 1 END) AS waitlisted_count,
                    COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) AS cancelled_count,
                    COALESCE(SUM(CASE WHEN status = 'CONFIRMED' THEN total_amount ELSE 0 END), 0) AS total_revenue
                FROM bookings
            """)
            b_stats = cur.fetchone()

            # 4. Recent Bookings for quick table
            cur.execute("""
                SELECT b.*, f.flight_number, sa.airport_code AS source_code, da.airport_code AS dest_code
                FROM bookings b
                JOIN flights f ON b.flight_id = f.flight_id
                JOIN airports sa ON f.source_airport_id = sa.airport_id
                JOIN airports da ON f.destination_airport_id = da.airport_id
                ORDER BY b.booking_date DESC
                LIMIT 6
            """)
            recent_bookings = cur.fetchall()

            # 5. Overbooking Overview across scheduled flights
            cur.execute("""
                SELECT 
                    f.flight_id, f.flight_number, f.travel_date,
                    a.aircraft_name, a.total_seats, a.overbooking_percentage,
                    COUNT(CASE WHEN b.status = 'CONFIRMED' THEN 1 END) AS confirmed,
                    COUNT(CASE WHEN b.status = 'WAITLISTED' THEN 1 END) AS waitlisted
                FROM flights f
                JOIN aircraft a ON f.aircraft_id = a.aircraft_id
                LEFT JOIN bookings b ON f.flight_id = b.flight_id
                WHERE f.status = 'SCHEDULED'
                GROUP BY f.flight_id, f.flight_number, f.travel_date, a.aircraft_name, a.total_seats, a.overbooking_percentage
            """)
            flight_overbooking_stats = []
            for r in cur.fetchall():
                phys = int(r['total_seats'])
                pct = float(r['overbooking_percentage'])
                max_cap = int(phys * (1.0 + (pct / 100.0)))
                conf = int(r['confirmed'])
                wait = int(r['waitlisted'])
                flight_overbooking_stats.append({
                    'flight_number': r['flight_number'],
                    'travel_date': str(r['travel_date']),
                    'aircraft_name': r['aircraft_name'],
                    'physical_capacity': phys,
                    'overbooking_percentage': pct,
                    'max_capacity': max_cap,
                    'confirmed': conf,
                    'waitlisted': wait,
                    'utilization': round((conf / phys * 100) if phys > 0 else 0, 1)
                })

        return render_template(
            'admin/dashboard.html',
            total_flights=total_flights,
            total_users=total_users,
            stats=b_stats,
            recent_bookings=recent_bookings,
            overbooking_overview=flight_overbooking_stats
        )

    except Exception as e:
        flash("Error loading administrative metrics.", "danger")
        print(f"[ADMIN DASHBOARD ERROR] {e}")
        return render_template('admin/dashboard.html', total_flights=0, total_users=0, stats={}, recent_bookings=[], overbooking_overview=[])


@admin_bp.route('/flights', methods=['GET', 'POST'])
@admin_required
def manage_flights():
    """Flight Schedule Management (Create, View, Status Update)."""
    with get_db_cursor(commit=True) as cur:
        if request.method == 'POST':
            # Add new flight
            flight_number = request.form.get('flight_number', '').strip().upper()
            source_id = request.form.get('source_airport_id')
            dest_id = request.form.get('destination_airport_id')
            aircraft_id = request.form.get('aircraft_id')
            dep_time = request.form.get('departure_time')
            arr_time = request.form.get('arrival_time')
            travel_date = request.form.get('travel_date')
            base_price = request.form.get('base_price')

            if source_id == dest_id:
                flash("Source and destination airports cannot be identical.", "warning")
            else:
                try:
                    cur.execute("""
                        INSERT INTO flights (flight_number, source_airport_id, destination_airport_id, aircraft_id, departure_time, arrival_time, travel_date, base_price, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'SCHEDULED')
                    """, (flight_number, source_id, dest_id, aircraft_id, dep_time, arr_time, travel_date, base_price))
                    flash(f"Flight {flight_number} successfully added to operational schedule!", "success")
                except Exception as err:
                    flash(f"Failed to add flight: {err}", "danger")

        # Fetch list of flights
        cur.execute("""
            SELECT 
                f.*, 
                sa.airport_code AS source_code, sa.city AS source_city,
                da.airport_code AS dest_code, da.city AS dest_city,
                ac.aircraft_name, ac.total_seats
            FROM flights f
            JOIN airports sa ON f.source_airport_id = sa.airport_id
            JOIN airports da ON f.destination_airport_id = da.airport_id
            JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
            ORDER BY f.travel_date DESC, f.departure_time ASC
        """)
        flight_list = cur.fetchall()

        # Fetch airports and aircraft for dropdowns
        cur.execute("SELECT * FROM airports ORDER BY city ASC")
        airports = cur.fetchall()

        cur.execute("SELECT * FROM aircraft ORDER BY aircraft_name ASC")
        fleet = cur.fetchall()

    return render_template(
        'admin/flights.html',
        flights=flight_list,
        airports=airports,
        fleet=fleet
    )


@admin_bp.route('/flights/status/<int:flight_id>', methods=['POST'])
@admin_required
def update_flight_status(flight_id):
    """Updates operational status of a flight (SCHEDULED, DELAYED, CANCELLED)."""
    new_status = request.form.get('status')
    if new_status in ('SCHEDULED', 'DELAYED', 'CANCELLED', 'COMPLETED'):
        with get_db_cursor(commit=True) as cur:
            cur.execute("UPDATE flights SET status = %s WHERE flight_id = %s", (new_status, flight_id))
        flash(f"Flight status updated to {new_status}.", "info")
    return redirect(url_for('admin.manage_flights'))


@admin_bp.route('/aircraft', methods=['GET', 'POST'])
@admin_required
def manage_aircraft():
    """Fleet configuration and seating layout overview."""
    with get_db_cursor(commit=True) as cur:
        if request.method == 'POST':
            name = request.form.get('aircraft_name', '').strip()
            model = request.form.get('model_number', '').strip()
            rows = int(request.form.get('rows', 5))
            cols = request.form.get('layout', '6')  # 6 = 3-3, 4 = 2-2
            overbooking_pct = float(request.form.get('overbooking_percentage', 5.0))
            
            total_seats = rows * (6 if cols == '6' else 4)

            try:
                # 1. Insert Aircraft
                cur.execute("""
                    INSERT INTO aircraft (aircraft_name, model_number, total_seats, overbooking_percentage)
                    VALUES (%s, %s, %s, %s)
                """, (name, model, total_seats, overbooking_pct))
                new_aircraft_id = cur.lastrowid

                # 2. Automatically generate physical seat records (ADSA matrix generation)
                seat_columns = ['A', 'B', 'C', 'D', 'E', 'F'] if cols == '6' else ['A', 'B', 'C', 'D']
                seat_records = []
                for r in range(1, rows + 1):
                    seat_class = 'BUSINESS' if r <= 1 else 'ECONOMY'
                    for c in seat_columns:
                        seat_records.append((new_aircraft_id, f"{r}{c}", seat_class, r, c))

                cur.executemany("""
                    INSERT INTO seats (aircraft_id, seat_number, seat_class, seat_row, seat_col)
                    VALUES (%s, %s, %s, %s, %s)
                """, seat_records)

                flash(f"Aircraft '{name}' ({total_seats} seats) and physical seat matrix added successfully!", "success")
            except Exception as e:
                flash(f"Error adding aircraft: {e}", "danger")

        # Fetch fleet with seats and overbooking policy
        cur.execute("""
            SELECT a.*, COUNT(s.seat_id) AS generated_seats
            FROM aircraft a
            LEFT JOIN seats s ON a.aircraft_id = s.aircraft_id
            GROUP BY a.aircraft_id, a.aircraft_name, a.model_number, a.total_seats, a.overbooking_percentage, a.created_at
            ORDER BY a.aircraft_id ASC
        """)
        fleet = cur.fetchall()

    return render_template('admin/aircraft.html', fleet=fleet)


@admin_bp.route('/overbooking', methods=['GET', 'POST'])
@admin_required
def overbooking_policy():
    """Configures overbooking percentages across fleet."""
    with get_db_cursor(commit=True) as cur:
        if request.method == 'POST':
            aircraft_id = request.form.get('aircraft_id')
            new_pct = float(request.form.get('overbooking_percentage', 5.0))

            if 0.0 <= new_pct <= 50.0:
                cur.execute("""
                    UPDATE aircraft 
                    SET overbooking_percentage = %s 
                    WHERE aircraft_id = %s
                """, (new_pct, aircraft_id))
                flash(f"Overbooking policy updated to {new_pct:.1f}% for selected aircraft.", "success")
            else:
                flash("Overbooking percentage must be between 0% and 50%.", "warning")

        # Fetch current fleet overbooking configuration
        cur.execute("""
            SELECT 
                a.*,
                FLOOR(a.total_seats * (1.0 + (a.overbooking_percentage / 100.0))) AS max_allowed_capacity
            FROM aircraft a
            ORDER BY a.aircraft_id ASC
        """)
        aircraft_policies = cur.fetchall()

        # Fetch active waitlisted bookings across all flights
        cur.execute("""
            SELECT 
                b.booking_id, b.pnr, b.passenger_name, b.passenger_email, b.passenger_phone,
                b.booking_date, b.waitlist_position,
                f.flight_number, f.travel_date, sa.city AS source_city, da.city AS dest_city
            FROM bookings b
            JOIN flights f ON b.flight_id = f.flight_id
            JOIN airports sa ON f.source_airport_id = sa.airport_id
            JOIN airports da ON f.destination_airport_id = da.airport_id
            WHERE b.status = 'WAITLISTED'
            ORDER BY b.flight_id ASC, b.waitlist_position ASC
        """)
        waitlisted_passengers = cur.fetchall()

    return render_template(
        'admin/overbooking.html',
        policies=aircraft_policies,
        waitlist=waitlisted_passengers
    )


@admin_bp.route('/bookings')
@admin_required
def manage_bookings():
    """All passenger reservations with filters & administrative cancellation."""
    status_filter = request.args.get('status', '').strip().upper()
    search_q = request.args.get('q', '').strip()

    query = """
        SELECT 
            b.*, f.flight_number, f.travel_date, f.departure_time,
            sa.airport_code AS source_code, da.airport_code AS dest_code,
            s.seat_number, s.seat_class
        FROM bookings b
        JOIN flights f ON b.flight_id = f.flight_id
        JOIN airports sa ON f.source_airport_id = sa.airport_id
        JOIN airports da ON f.destination_airport_id = da.airport_id
        LEFT JOIN booked_seats bs ON b.booking_id = bs.booking_id AND bs.seat_booking_status = 'ACTIVE'
        LEFT JOIN seats s ON bs.seat_id = s.seat_id
        WHERE 1=1
    """
    params = []

    if status_filter in ('CONFIRMED', 'WAITLISTED', 'CANCELLED'):
        query += " AND b.status = %s"
        params.append(status_filter)

    if search_q:
        query += " AND (b.pnr LIKE %s OR b.passenger_name LIKE %s OR b.passenger_email LIKE %s)"
        like_term = f"%{search_q}%"
        params.extend([like_term, like_term, like_term])

    query += " ORDER BY b.booking_date DESC"

    with get_db_cursor() as cur:
        cur.execute(query, params)
        bookings = cur.fetchall()

    return render_template(
        'admin/bookings.html',
        bookings=bookings,
        status_filter=status_filter,
        search_q=search_q
    )


@admin_bp.route('/bookings/cancel/<int:booking_id>', methods=['POST'])
@admin_required
def admin_cancel_booking(booking_id):
    """Admin cancel booking with automatic waitlist queue promotion."""
    try:
        result = cancel_booking_transaction(booking_id, is_admin=True)
        msg = f"Reservation {result['cancelled_pnr']} cancelled by Administrator."
        if result['promoted_pnr']:
            msg += f" Waitlisted passenger {result['promoted_passenger']} (PNR: {result['promoted_pnr']}) automatically promoted!"
        flash(msg, "info")
    except Exception as e:
        flash(f"Cancellation error: {e}", "danger")
    return redirect(url_for('admin.manage_bookings'))


@admin_bp.route('/users')
@admin_required
def manage_users():
    """Registered passengers directory."""
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                u.user_id, u.name, u.email, u.phone, u.role, u.created_at,
                COUNT(b.booking_id) AS total_bookings
            FROM users u
            LEFT JOIN bookings b ON u.user_id = b.user_id
            GROUP BY u.user_id, u.name, u.email, u.phone, u.role, u.created_at
            ORDER BY u.created_at DESC
        """)
        users = cur.fetchall()

    return render_template('admin/users.html', users=users)
