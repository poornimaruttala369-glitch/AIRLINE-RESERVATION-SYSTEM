"""
Flights Blueprint (Routes)
--------------------------
Handles Flight Search, Filtering, Sorting (ADSA), and Flight Details.
Academic Context:
- ADSA: Search algorithms, sorting by multiple attributes (Price, Time, Seat Availability).
- DBMS: Multi-table joins (flights, airports, aircraft, bookings).
"""
from datetime import datetime, date
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from database.db import get_db_cursor
from models.flight import Flight
from services.algorithm_service import sort_flights

flights_bp = Blueprint('flights', __name__, url_prefix='/flights')


def get_all_airports():
    """Helper to fetch list of all airports for search dropdowns."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM airports ORDER BY city ASC")
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch airports: {e}")
        return []


@flights_bp.route('/search', methods=['GET'])
def search():
    """
    Flight Search & Results view.
    Demonstrates ADSA Searching & Sorting.
    """
    airports = get_all_airports()
    
    from_code = request.args.get('from_airport', '').strip().upper()
    to_code = request.args.get('to_airport', '').strip().upper()
    travel_date_str = request.args.get('travel_date', '').strip()
    sort_by = request.args.get('sort', 'price').strip()
    order = request.args.get('order', 'asc').strip()

    # If no parameters provided yet, render the initial search form
    if not from_code and not to_code and not travel_date_str:
        return render_template(
            'flights.html',
            airports=airports,
            flights=None,
            has_searched=False
        )

    # Validation: Source and destination required
    if not from_code or not to_code:
        flash("Please select both origin and destination airports.", "warning")
        return render_template('flights.html', airports=airports, flights=None, has_searched=False)

    if from_code == to_code:
        flash("Origin and destination airports cannot be the same.", "warning")
        return render_template('flights.html', airports=airports, flights=None, has_searched=False)

    # Query flights matching criteria
    try:
        query = """
            SELECT 
                f.flight_id, f.flight_number, f.source_airport_id, f.destination_airport_id,
                f.aircraft_id, f.departure_time, f.arrival_time, f.travel_date, f.base_price, f.status,
                sa.airport_code AS source_code, sa.city AS source_city,
                da.airport_code AS dest_code, da.city AS dest_city,
                ac.aircraft_name, ac.total_seats, ac.overbooking_percentage,
                (
                    SELECT COUNT(*) 
                    FROM booked_seats bs 
                    WHERE bs.flight_id = f.flight_id AND bs.seat_booking_status = 'ACTIVE'
                ) AS booked_count
            FROM flights f
            JOIN airports sa ON f.source_airport_id = sa.airport_id
            JOIN airports da ON f.destination_airport_id = da.airport_id
            JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
            WHERE sa.airport_code = %s 
              AND da.airport_code = %s
              AND f.status = 'SCHEDULED'
        """
        params = [from_code, to_code]

        if travel_date_str:
            query += " AND f.travel_date = %s"
            params.append(travel_date_str)

        with get_db_cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        flight_objects = []
        for r in rows:
            phys_seats = r['total_seats']
            booked = r['booked_count']
            avail = max(0, phys_seats - booked)

            flight = Flight(
                flight_id=r['flight_id'],
                flight_number=r['flight_number'],
                source_airport_id=r['source_airport_id'],
                destination_airport_id=r['destination_airport_id'],
                aircraft_id=r['aircraft_id'],
                departure_time=r['departure_time'],
                arrival_time=r['arrival_time'],
                travel_date=r['travel_date'],
                base_price=r['base_price'],
                status=r['status'],
                source_code=r['source_code'],
                source_city=r['source_city'],
                dest_code=r['dest_code'],
                dest_city=r['dest_city'],
                aircraft_name=r['aircraft_name'],
                available_seats=avail
            )
            flight_objects.append(flight)

        # ADSA Concept: Multi-parameter sorting
        sorted_flight_list = sort_flights(flight_objects, sort_by=sort_by, order=order)

        return render_template(
            'flights.html',
            airports=airports,
            flights=sorted_flight_list,
            has_searched=True,
            from_code=from_code,
            to_code=to_code,
            travel_date=travel_date_str,
            sort_by=sort_by,
            order=order
        )

    except Exception as e:
        flash("An error occurred while searching for flights. Please try again.", "danger")
        print(f"[SEARCH ERROR] {e}")
        return render_template('flights.html', airports=airports, flights=[], has_searched=True)
