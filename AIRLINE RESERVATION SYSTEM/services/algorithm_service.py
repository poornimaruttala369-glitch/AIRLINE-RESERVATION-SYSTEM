"""
Algorithm Service (ADSA Concepts)
---------------------------------
Practical realization of Advanced Data Structures & Algorithms:
1. Flight Sorting: Multi-attribute sorting (Price, Time, Available Seats) with O(N log N) complexity.
2. Seat Matrix Lookup: O(1) Hash Set membership check for fast cabin rendering.
3. Route Search & Filtering: Filter algorithms for flight discovery.
"""


def sort_flights(flights, sort_by='price', order='asc'):
    """
    Sorts a list of Flight objects based on specified criteria.
    ADSA Concept:
    - Time Complexity: O(N log N) where N is number of flights.
    - Space Complexity: O(N) auxiliary space.
    - Demonstrates comparator key functions.
    """
    reverse = (order.lower() == 'desc')

    if sort_by == 'price':
        return sorted(flights, key=lambda f: f.base_price, reverse=reverse)
    elif sort_by == 'dep_time':
        return sorted(flights, key=lambda f: f.departure_time, reverse=reverse)
    elif sort_by == 'arr_time':
        return sorted(flights, key=lambda f: f.arrival_time, reverse=reverse)
    elif sort_by == 'seats':
        return sorted(flights, key=lambda f: (f.available_seats or 0), reverse=reverse)
    else:
        # Default sort by price
        return sorted(flights, key=lambda f: f.base_price, reverse=reverse)


def build_seat_matrix(seats, active_booked_seat_ids):
    """
    Constructs a visual cabin map matrix grouped by rows.
    ADSA Concept:
    - Hash Set: active_booked_seat_ids converted to set for O(1) membership check.
    - Hash Map / Dictionary grouping: O(M) time where M is number of physical seats.
    """
    booked_set = set(active_booked_seat_ids)
    rows_dict = {}

    for seat in seats:
        # Check if seat is currently booked in O(1)
        seat.status = 'BOOKED' if seat.seat_id in booked_set else 'AVAILABLE'
        
        row_num = seat.seat_row
        if row_num not in rows_dict:
            rows_dict[row_num] = []
        rows_dict[row_num].append(seat)

    # Sort seats within each row by column ('A', 'B', 'C', ...)
    for row_num in rows_dict:
        rows_dict[row_num].sort(key=lambda s: s.seat_col)

    # Return ordered list of rows
    return sorted(rows_dict.items(), key=lambda item: item[0])
