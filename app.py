import os
from dotenv import load_dotenv
from supabase import create_client
import statsapi

load_dotenv()  # This one line loads your .env file

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)


data = statsapi.get('teams', {'sportId': 1})
mlb_teams = data['teams']



for team in mlb_teams:  # Now iterate over the teams
    team_data = {
        'team_id': team['id'],
        'team_name': team['name'],
        'abbreviation': team['abbreviation']  # Also fix this - use 'abbreviation' not 'id'
    }

    try:
        response = supabase.table('teams').upsert(team_data, on_conflict='team_id').execute()

        print(f"Inserted/Updated: {team['name']}")
    except:
        print(f"Could not update {team['name']}")
    


# Test with teams table (after you create it)
try:
    response = supabase.table('teams').select("*").execute()
    print("✅ Teams table connected!")
except Exception as e:
    print("❌ Error:", e)

