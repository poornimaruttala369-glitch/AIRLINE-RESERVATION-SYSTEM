"""
Booking Blueprint (Routes)
--------------------------
Handles Seat Selection, Transactional Booking, Confirmation, and Passenger Trips.
Academic Context:
- ADSA: O(1) Seat lookup and matrix generation.
- DBMS: Concurrency control and ACID rollback on collision.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from database.db import get_db_cursor
from models.flight import Flight
from models.seat import Seat
from routes.auth_helpers import login_required, get_current_user
from services.algorithm_service import build_seat_matrix
from services.booking_service import (
    reserve_flight_ticket, SeatAlreadyBookedError, OverbookingLimitExceededError, BookingError
)
from services.overbooking_service import cancel_booking_transaction

booking_bp = Blueprint('booking', __name__, url_prefix='/booking')


@booking_bp.route('/select-seats/<int:flight_id>')
@login_required
def select_seats(flight_id):
    """
    Renders visual aircraft cabin seat map.
    Demonstrates ADSA O(1) seat status lookup and dynamic matrix grouping.
    """
    try:
        with get_db_cursor() as cur:
            # Fetch flight with airport & aircraft details
            cur.execute("""
                SELECT 
                    f.*, 
                    sa.airport_code AS source_code, sa.city AS source_city,
                    da.airport_code AS dest_code, da.city AS dest_city,
                    ac.aircraft_name, ac.total_seats, ac.overbooking_percentage
                FROM flights f
                JOIN airports sa ON f.source_airport_id = sa.airport_id
                JOIN airports da ON f.destination_airport_id = da.airport_id
                JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
                WHERE f.flight_id = %s
            """, (flight_id,))
            flight_data = cur.fetchone()

            if not flight_data:
                flash("Selected flight was not found.", "danger")
                return redirect(url_for('flights.search'))

            flight = Flight(
                flight_id=flight_data['flight_id'],
                flight_number=flight_data['flight_number'],
                source_airport_id=flight_data['source_airport_id'],
                destination_airport_id=flight_data['destination_airport_id'],
                aircraft_id=flight_data['aircraft_id'],
                departure_time=flight_data['departure_time'],
                arrival_time=flight_data['arrival_time'],
                travel_date=flight_data['travel_date'],
                base_price=flight_data['base_price'],
                source_code=flight_data['source_code'],
                source_city=flight_data['source_city'],
                dest_code=flight_data['dest_code'],
                dest_city=flight_data['dest_city'],
                aircraft_name=flight_data['aircraft_name']
            )

            # Fetch all physical seats for this aircraft
            cur.execute("""
                SELECT * FROM seats 
                WHERE aircraft_id = %s 
                ORDER BY seat_row ASC, seat_col ASC
            """, (flight_data['aircraft_id'],))
            seat_rows = cur.fetchall()

            seat_objects = [
                Seat(
                    seat_id=s['seat_id'],
                    aircraft_id=s['aircraft_id'],
                    seat_number=s['seat_number'],
                    seat_class=s['seat_class'],
                    seat_row=s['seat_row'],
                    seat_col=s['seat_col']
                ) for s in seat_rows
            ]

            # Fetch active booked seats for this flight (Double-booking prevention display)
            cur.execute("""
                SELECT seat_id FROM booked_seats 
                WHERE flight_id = %s AND seat_booking_status = 'ACTIVE'
            """, (flight_id,))
            booked_seat_rows = cur.fetchall()
            active_booked_ids = [r['seat_id'] for r in booked_seat_rows]

            # Build cabin matrix using algorithm service
            cabin_matrix = build_seat_matrix(seat_objects, active_booked_ids)

            # Check capacity state
            total_seats = int(flight_data['total_seats'])
            booked_count = len(active_booked_ids)
            available_count = max(0, total_seats - booked_count)
            is_waitlist_eligible = (available_count == 0)

            return render_template(
                'seat_selection.html',
                flight=flight,
                cabin_matrix=cabin_matrix,
                total_seats=total_seats,
                booked_count=booked_count,
                available_count=available_count,
                is_waitlist_eligible=is_waitlist_eligible
            )

    except Exception as e:
        flash("Unable to load cabin seat map. Please try again.", "danger")
        print(f"[SEAT MAP ERROR] {e}")
        return redirect(url_for('flights.search'))


@booking_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """Passenger details and reservation preview."""
    flight_id = request.form.get('flight_id')
    seat_id = request.form.get('seat_id')

    if not flight_id or not seat_id:
        flash("Please select an available seat first.", "warning")
        return redirect(url_for('flights.search'))

    current_user = get_current_user()

    try:
        with get_db_cursor() as cur:
            # Flight details
            cur.execute("""
                SELECT f.*, sa.city AS source_city, da.city AS dest_city,
                       sa.airport_code AS source_code, da.airport_code AS dest_code,
                       ac.aircraft_name
                FROM flights f
                JOIN airports sa ON f.source_airport_id = sa.airport_id
                JOIN airports da ON f.destination_airport_id = da.airport_id
                JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
                WHERE f.flight_id = %s
            """, (flight_id,))
            flight = cur.fetchone()

            # Seat details
            cur.execute("SELECT * FROM seats WHERE seat_id = %s", (seat_id,))
            seat = cur.fetchone()

            # Pre-booking check: ensure seat is not already booked
            cur.execute("""
                SELECT 1 FROM booked_seats 
                WHERE flight_id = %s AND seat_id = %s AND seat_booking_status = 'ACTIVE'
            """, (flight_id, seat_id))
            if cur.fetchone():
                flash(f"Seat {seat['seat_number']} has already been reserved. Please pick another seat.", "danger")
                return redirect(url_for('booking.select_seats', flight_id=flight_id))

            # Pricing calculation
            base_price = float(flight['base_price'])
            final_price = base_price * 1.20 if seat['seat_class'] == 'BUSINESS' else base_price

            return render_template(
                'booking.html',
                flight=flight,
                seat=seat,
                current_user=current_user,
                final_price=final_price
            )

    except Exception as e:
        flash("An error occurred during checkout setup.", "danger")
        print(f"[CHECKOUT ERROR] {e}")
        return redirect(url_for('flights.search'))


@booking_bp.route('/confirm', methods=['POST'])
@login_required
def confirm():
    """
    Executes transaction-safe reservation with double-booking prevention.
    """
    user_id = session.get('user_id')
    flight_id = int(request.form.get('flight_id'))
    seat_id = int(request.form.get('seat_id'))
    passenger_name = request.form.get('passenger_name', '').strip()
    passenger_email = request.form.get('passenger_email', '').strip()
    passenger_phone = request.form.get('passenger_phone', '').strip()
    payment_method = request.form.get('payment_method', 'DEMO_CARD').strip()

    if not passenger_name or not passenger_email or not passenger_phone:
        flash("All passenger fields are required.", "danger")
        return redirect(url_for('booking.select_seats', flight_id=flight_id))

    try:
        # Atomic ACID reservation with row-locking and DB unique constraints
        result = reserve_flight_ticket(
            user_id=user_id,
            flight_id=flight_id,
            seat_id=seat_id,
            passenger_name=passenger_name,
            passenger_email=passenger_email,
            passenger_phone=passenger_phone
            payment_method=payment_method
        )

        if result['status'] == 'WAITLISTED':
            flash(f"Booking registered under Overbooking Policy as WAITLISTED (Position #{result['waitlist_position']}). PNR: {result['pnr']}", "warning")
        else:
            flash(f"Booking Confirmed! Your PNR is {result['pnr']}.", "success")

        return redirect(url_for('booking.confirmation', pnr=result['pnr']))

    except SeatAlreadyBookedError as e:
        flash(f"Reservation Collision: {str(e)}", "danger")
        return redirect(url_for('booking.select_seats', flight_id=flight_id))
    except OverbookingLimitExceededError as e:
        flash(f"Flight Full: {str(e)}", "danger")
        return redirect(url_for('flights.search'))
    except BookingError as e:
        flash(f"Booking Error: {str(e)}", "danger")
        return redirect(url_for('booking.select_seats', flight_id=flight_id))
    except Exception as e:
        flash("An unexpected error occurred while securing your ticket. Transaction rolled back safely.", "danger")
        print(f"[CONFIRM EXCEPTION] {e}")
        return redirect(url_for('flights.search'))


@booking_bp.route('/confirmation/<pnr>')
@login_required
def confirmation(pnr):
    """Renders boarding pass confirmation card."""
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    b.*, f.flight_number, f.departure_time, f.arrival_time, f.travel_date, f.base_price,
                    sa.airport_code AS source_code, sa.city AS source_city, sa.airport_name AS source_name,
                    da.airport_code AS dest_code, da.city AS dest_city, da.airport_name AS dest_name,
                    ac.aircraft_name,
                    s.seat_number, s.seat_class,
                    p.transaction_ref, p.payment_status
                FROM bookings b
                JOIN flights f ON b.flight_id = f.flight_id
                JOIN airports sa ON f.source_airport_id = sa.airport_id
                JOIN airports da ON f.destination_airport_id = da.airport_id
                JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
                LEFT JOIN booked_seats bs ON b.booking_id = bs.booking_id AND bs.seat_booking_status = 'ACTIVE'
                LEFT JOIN seats s ON bs.seat_id = s.seat_id
                LEFT JOIN payments p ON b.booking_id = p.booking_id
                WHERE b.pnr = %s
            """, (pnr.upper(),))
            booking = cur.fetchone()

            if not booking:
                flash("Ticket not found.", "warning")
                return redirect(url_for('booking.my_bookings'))

            # Security check: passenger can only view their own bookings unless admin
            if session.get('user_role') != 'ADMIN' and booking['user_id'] != session.get('user_id'):
                abort(403)

            return render_template('confirmation.html', booking=booking)

    except Exception as e:
        flash("Error loading booking confirmation.", "danger")
        print(f"[CONFIRMATION VIEW ERROR] {e}")
        return redirect(url_for('booking.my_bookings'))


@booking_bp.route('/my-bookings')
@login_required
def my_bookings():
    """Passenger bookings history."""
    user_id = session.get('user_id')
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    b.*, f.flight_number, f.departure_time, f.arrival_time, f.travel_date,
                    sa.airport_code AS source_code, sa.city AS source_city,
                    da.airport_code AS dest_code, da.city AS dest_city,
                    s.seat_number, s.seat_class
                FROM bookings b
                JOIN flights f ON b.flight_id = f.flight_id
                JOIN airports sa ON f.source_airport_id = sa.airport_id
                JOIN airports da ON f.destination_airport_id = da.airport_id
                LEFT JOIN booked_seats bs ON b.booking_id = bs.booking_id AND bs.seat_booking_status = 'ACTIVE'
                LEFT JOIN seats s ON bs.seat_id = s.seat_id
                WHERE b.user_id = %s
                ORDER BY b.booking_date DESC
            """, (user_id,))
            bookings = cur.fetchall()

        return render_template('my_bookings.html', bookings=bookings)

    except Exception as e:
        flash("Unable to load booking history.", "danger")
        print(f"[MY BOOKINGS ERROR] {e}")
        return render_template('my_bookings.html', bookings=[])


@booking_bp.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel(booking_id):
    """
    Cancels passenger booking and triggers FIFO waitlist promotion.
    """
    user_id = session.get('user_id')
    is_admin = (session.get('user_role') == 'ADMIN')

    try:
        result = cancel_booking_transaction(booking_id, requesting_user_id=user_id, is_admin=is_admin)

        msg = f"Booking (PNR: {result['cancelled_pnr']}) has been successfully cancelled and seat released."
        if result['promoted_pnr']:
            msg += f" Overbooking policy automatically promoted waitlisted passenger {result['promoted_passenger']} (PNR: {result['promoted_pnr']}) to CONFIRMED!"

        flash(msg, "info")

    except PermissionError:
        flash("You are not authorized to cancel this booking.", "danger")
    except ValueError as ve:
        flash(str(ve), "warning")
    except Exception as e:
        flash("Cancellation failed. Transaction rolled back safely.", "danger")
        print(f"[CANCEL ERROR] {e}")

    return redirect(url_for('booking.my_bookings'))
