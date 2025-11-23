def db_get_market_hours():
     """
     Returns {"open_time": "09:30", "close_time": "16:00", "tz_name": "America/New_York"}

     Normally reads from the market_hours table, but if there is no row yet,
     it will fall back to standard US stock market hours in New York.
     """
     conn = get_db_connection()
     try:
         with conn:
             with conn.cursor() as cur:
                 cur.execute("""
                     SELECT open_time, close_time, tz_name
                     FROM market_hours
                     WHERE id = TRUE
                     LIMIT 1
                 """)
                 row = cur.fetchone()
                 if not row:
                     #FALLBACK: this is what makes it 09:30–16:00 New York time
                     return {
                         "open_time": "09:30",
                         "close_time": "16:00",
                         "tz_name": "America/New_York",
                     }

                 # row[0] and row[1] are POSTGRES time objects → convert to "HH:MM"
                 open_str = row[0].strftime("%H:%M")
                 close_str = row[1].strftime("%H:%M")
                 return {
                     "open_time": open_str,
                     "close_time": close_str,
                     "tz_name": row[2],
                 }
     finally:
         conn.close()
