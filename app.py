import os
from dotenv import load_dotenv
from supabase import create_client
import statsapi

load_dotenv()  # This one line loads your .env file

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)


data = statsapi.get('teams', {'sportId': 1})

# print(data)

mlb_teams = data['teams']

# print(len(mlb_teams))

# test_team_id = statsapi.team_leaders(teamId='112', leaderCategories='hits')
# print(test_team_id)

standings_data = statsapi.standings_data(season='2025')

standings_data_divisions = list(standings_data.values())

# print(standings_data_divisions[0])


# Loops through all teams and stores team data in database table 
for team in mlb_teams:
    team_data = {
        'team_id': team['id'],
        'team_name': team['name'],
        'abbreviation': team['abbreviation'],
        'division': team['division']['name'],
        'league': team['league']['name']
    }

    try:
        response = supabase.table('teams').upsert(team_data, on_conflict='team_id').execute()
        
        # Testing before putting to database table
        # print(team['id'])
        # print(team['name'])
        # print(team['abbreviation'])
        # print (team['division']['name'])
        # print (team['league']['name'])

        print(f"Inserted/Updated: {team['name']}")
    except:
        print(f"Could not update {team['name']}")
    

# Testing if connect to database
try:
    # response = supabase.table('teams').select("*").execute()
    print("✅ Teams table connected!")
except Exception as e:
    print("❌ Error:", e)

