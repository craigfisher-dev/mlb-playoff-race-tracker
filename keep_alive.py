# Keeps the Supabase free plan project from getting paused for inactivity
# (Supabase pauses free projects after 7 days of no activity, so this pings the database on a timer)
# Render starts this next to the app: python keep_alive.py & streamlit run app.py ...
# (It runs once when the server starts, NOT once per page load, so visitors do not affect how often it pings)
#
# Every ping does 2 things:
# write: upserts one row (id 1) in the keep_alive table with the current UTC time
# read: reads the keep_alive table back
import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()  # Loads .env file (only matters for local testing, on Render the real environment variables are used)

# Supabase project URL and service role key (same variable names app.py uses)
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# Headers sent with every request to Supabase:
# apikey + Authorization: who we are (the service role key)
# Content-Type: the data we send is JSON
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}

# Seconds to wait between pings (6 hours)
# (Supabase only needs activity once every 7 days, so this is more than enough, raise it for fewer pings)
INTERVAL = 6 * 60 * 60  # seconds between pings

# Runs forever: ping, sleep, ping again (Stops when the server stops)
while True:
    try:
        # WRITE: upsert row id 1 with the current UTC time, Example: 2026-11-13T14:30:05+00:00
        # ("merge-duplicates" updates the row if id 1 already exists instead of throwing an error)
        # Status 201 = success
        w = requests.post(
            f"{URL}/rest/v1/keep_alive",
            headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
            json={"id": 1, "pinged_at": datetime.now(timezone.utc).isoformat()},
            timeout=15,
        )

        # READ: gets the first row back from the keep_alive table
        # Status 200 = success
        r = requests.get(
            f"{URL}/rest/v1/keep_alive?select=*&limit=1",
            headers=HEADERS,
            timeout=15,
        )

        # Shows up in the Render Logs tab, Example: keep-alive write=201 read=200
        # (A bad status like 401 does not raise an error, it only shows up in these printed numbers)
        # (flush=True makes the line show up right away instead of being held back by Python)
        print(f"keep-alive write={w.status_code} read={r.status_code}", flush=True)

    # If the request itself fails (no network, Supabase down, timeout) print the error and keep looping
    # (So one bad ping does not kill the script, the next ping still happens)
    except Exception as e:
        print(f"keep-alive failed: {e}", flush=True)

    # Wait until the next ping
    time.sleep(INTERVAL)