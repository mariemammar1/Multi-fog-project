
import sqlite3

with sqlite3.connect("data/fog_a.db") as connection:
    connection.row_factory = sqlite3.Row

    rows = connection.execute("""
        SELECT hold_id, request_id, station_id, status, expires_at
        FROM reservations
        WHERE station_id = 'A-01'
        ORDER BY created_at DESC
    """).fetchall()

    print("Reservations for A-01:")

    for row in rows:
        print(dict(row))
