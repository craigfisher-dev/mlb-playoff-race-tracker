import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()  # This one line loads your .env file

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")
supabase = create_client(url, key)


# Test with teams table (after you create it)
try:
    response = supabase.table('teams').select("*").execute()
    print("✅ Teams table connected!")
    print("Current teams:", response.data)
except Exception as e:
    print("❌ Error:", e)