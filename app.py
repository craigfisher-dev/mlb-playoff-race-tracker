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

# print((mlb_teams[1]))

# test_team_id = statsapi.team_leaders(teamId='112', leaderCategories='hits')
# print(test_team_id)


standings_data = statsapi.standings_data(season='2025')


# Strips the outside dictionary layer and only keeps the values in a list
standings_data_divisions = list(standings_data.values())



# 15 teams per league - NL, AL

national_league_teams = []
american_league_teams = []


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

print(standings_lookup[115])

print(standings_lookup[146])


# Loops through all teams and stores team data in database table 
for team in mlb_teams:
    standings = standings_lookup.get(team['id'])

    games_played = standings['w'] + standings['l']
    win_percentage = round(float(standings['w']/games_played), 3)

    if team['league']['name'] == "National League": 
        national_league_teams.append(team)
    else:
        american_league_teams.append(team)

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
        'games_back_in_wild_card': 0.0 if standings['wc_gb'] == '-' else float(standings['wc_gb']) if standings['wc_gb'] else None,
        'league_rank': standings['league_rank']
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


# print(national_league_teams)
# print(len(national_league_teams))

# print(american_league_teams)
# print(len(american_league_teams))





# Calculate and assign playoff_position values for current playoff seeding (Priority 0)

# Playoff Position Logic:
# Seeds 1-3: Division winners ranked by win percentage (highest = seed 1).
#            If two or more division winners are tied in win percentage, 
#            use league_rank as the tie-breaker. This tie-break rule only 
#            applies to division winners.
# Seeds 4-6: Wild card teams ranked by wild_card_rank (1st WC = seed 4, etc.)
# Seeds 7-15: Non-playoff teams ranked by wild_card_rank

# Steps:
# 1. Separate teams by league (AL/NL)
# 2. For each league:
#    - Get division winners (division_rank == 1), sort by win percentage 
#      (and league_rank if tied), assign playoff_position 1, 2, 3
#    - Get wild card teams (wild_card_rank 1-3), assign playoff_position 4, 5, 6
#    - Get remaining teams, sort by wild_card_rank, assign playoff_position 7-15
# 3. Store playoff_position in database along with other team stats

# Result: playoff_position column will show current playoff seeding



playoff_rank_NL = {}
division_winners_NL = []
wildcard_teams_NL = []


# Calculates and assigns playoff_position values for current playoff seeding (National League)
for team in national_league_teams:
    standings = standings_lookup.get(team['id'])
    wc_rank = standings['wc_rank']
    win_percentage = round(float(standings['w']/(standings['w'] + standings['l'])), 4)

    # Divsion winner
    if (wc_rank == '-'):
        division_winner_data = {
            'team_id' : team['id'], 
            'name' : standings['name'],
            'win_percentage' : win_percentage,
            'league_rank': int(standings['league_rank'])
        }
        division_winners_NL.append(division_winner_data)
    # All other teams
    else:
        wildcard_data = {
            'team_id' : team['id'], 
            'name' : standings['name'],
            'wc_rank' : int(standings['wc_rank'])
        }
        wildcard_teams_NL.append(wildcard_data)

def get_division_sort_key(standings):
    return (-standings['win_percentage'], standings['league_rank'])
    
division_winners_NL.sort(key=get_division_sort_key)
    
def get_wildcard_sort_key(standings):
    return (standings['wc_rank'])
    
wildcard_teams_NL.sort(key=get_wildcard_sort_key)

print(division_winners_NL)

print(wildcard_teams_NL)


playoff_position = 1
    
# Seeds 1-3: Division winners (already sorted by win % and league_rank)
for team in division_winners_NL:
    playoff_rank_NL[team['team_id']] = playoff_position
    playoff_position += 1

# Seeds 4-15: Remaining teams
for team in wildcard_teams_NL:
    playoff_rank_NL[team['team_id']] = playoff_position
    playoff_position += 1

print("NL Playoff Rankings:")
print(playoff_rank_NL)

for team_id in playoff_rank_NL:
    playoff_position_data = {
        'team_id': team_id,                           # Use the key (team_id)
        'playoff_position': playoff_rank_NL[team_id]  # Use the value (playoff_position)
    }
    # print(playoff_position_data)
    
    response = supabase.table('teams').upsert(playoff_position_data, on_conflict='team_id').execute()
    print(f"Updated team {team_id} with playoff position {playoff_rank_NL[team_id]}")



playoff_rank_AL = {}
division_winners_AL = []
wildcard_teams_AL = []

# Calculates and assigns playoff_position values for current playoff seeding (American League)
for team in american_league_teams:
    standings = standings_lookup.get(team['id'])
    wc_rank = standings['wc_rank']
    win_percentage = round(float(standings['w']/(standings['w'] + standings['l'])), 4)

    # Divsion winner
    if (wc_rank == '-'):
        division_winner_data = {
            'team_id' : team['id'], 
            'name' : standings['name'],
            'win_percentage' : win_percentage,
            'league_rank': int(standings['league_rank'])
        }
        division_winners_AL.append(division_winner_data)
    # All other teams
    else:
        wildcard_data = {
            'team_id' : team['id'], 
            'name' : standings['name'],
            'wc_rank' : int(standings['wc_rank'])
        }
        wildcard_teams_AL.append(wildcard_data)

def get_division_sort_key(standings):
    return (-standings['win_percentage'], standings['league_rank'])
    
division_winners_AL.sort(key=get_division_sort_key)
    
def get_wildcard_sort_key(standings):
    return (standings['wc_rank'])
    
wildcard_teams_AL.sort(key=get_wildcard_sort_key)

print(division_winners_AL)

print(wildcard_teams_AL)


playoff_position = 1
    
# Seeds 1-3: Division winners (already sorted by win % and league_rank)
for team in division_winners_AL:
    playoff_rank_AL[team['team_id']] = playoff_position
    playoff_position += 1

# Seeds 4-15: Remaining teams
for team in wildcard_teams_AL:
    playoff_rank_AL[team['team_id']] = playoff_position
    playoff_position += 1

print("AL Playoff Rankings:")
print(playoff_rank_AL)

for team_id in playoff_rank_AL:
    playoff_position_data = {
        'team_id': team_id,                           # Use the key (team_id)
        'playoff_position': playoff_rank_AL[team_id]  # Use the value (playoff_position)
    }
    # print(playoff_position_data)
    
    response = supabase.table('teams').upsert(playoff_position_data, on_conflict='team_id').execute()
    print(f"Updated team {team_id} with playoff position {playoff_rank_AL[team_id]}")







# Division (Magic Number) Distance to finish line calculations (Priority 1)

# 162 (starting zone) Magic Number
# 0 (finish line) Magic Number

# Each teams has there own lane so they are not on top of each other

# 1. Division Magic Number Formula:
# RG + 1 - (Losses by second place team - losses by first place team)
# Where:

# RG = Remaining games for the first place team
# Second/first place teams are within the same division


# Division Magic Number Formula (Trailling teams 2-5):
# RG + 1 - (Losses by first place team - losses by (current place team))
# Where:

# RG = Remaining games for the CURRENT PLACE team
# Current/first place teams are within the same division



# 2. Playoff Magic Number Formula:
# TG - WT - Lo + 1
# Where:

# TG = Total games in season (162 for MLB)
# WT = Wins by your team
# Lo = Losses by closest opponent (team holding last playoff spot)


# 3. Elimination Formula:
# Team is eliminated when: Games back > Games remaining
# Where:

# Games back = How many games behind the last playoff spot
# Games remaining = Games left in the season for that team





# Racing Visualization (Priority 2)

# Team "Cars" on Racing Tracks (Lanes)

# Car position = distance from finish line (magic number either to win division or get into playoffs
# see above for how calculate it)
# Different car colors for different statuses (division leader, wild card, bubble, eliminated)
# "E" for eliminated teams instead of broken cars




# Three View Toggle System (Priority 3)

# Full League View: Two big AL/NL tracks with all 15 teams each
# Division View: All 6 divisions shown separately
# Playoff Bracket View: Tournament tree structure




# Tournament Bracket Tree (Priority 4)

# Proper tree structure showing actual matchups
# Teams face each other and advance through rounds
# Connection lines between rounds
# Current playoff seeding (1-6 in each league)
# "If season ended today" bracket



# Try all the api calls if those dont work then pull data from database (Priority 5)
