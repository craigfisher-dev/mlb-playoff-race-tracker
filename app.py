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


# Strips the outside dictionary layer and only keeps the values in a list
standings_data_divisions = list(standings_data.values())


# Gets the division - standings_data_divisions[0]
# Then gets all the teams in the division ['teams']
# Then get the first team [0]
# standings_data_divisions[0]['teams'][0]
# Add any stat you want for example : wins
# standings_data_divisions[0]['teams'][0]['w'] returns
# the number of wins by that team


# print(standings_data_divisions[0]['teams'][0]['w'])



standings_lookup = {}
for division in standings_data_divisions:
    for team in division['teams']:
        standings_lookup[team['team_id']] = team
    
print(standings_lookup[108])



# Loops through all teams and stores team data in database table 
for team in mlb_teams:
    standings = standings_lookup.get(team['id'])

    games_played = standings['w'] + standings['l']
    win_percentage = round(float(standings['w']/games_played), 3)

    team_data = {
        'team_id': team['id'],
        'team_name': team['name'],
        'abbreviation': team['abbreviation'],
        'division': team['division']['name'],
        'league': team['league']['name'],
        
        # standings data
        'wins': standings['w'],
        'losses': standings['l'],
        'games_played': games_played,
        'win_percentage': win_percentage,
        'division_rank': int(standings['div_rank']) if standings['div_rank'] != '-' else 1,
        'games_back_in_division': 0.0 if standings['gb'] == '-' else float(standings['gb']),
        'wild_card_rank': int(standings['wc_rank']) if standings['wc_rank'] != '-' else None,
        'games_back_in_wild_card': 0.0 if standings['wc_gb'] == '-' else float(standings['wc_gb']) if standings['wc_gb'] else None
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


# Division rank stats have the correct tiebreak 
# logic use that for placement when making tables