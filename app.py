import os
from dotenv import load_dotenv
from supabase import create_client
import statsapi
import streamlit as st
import time
from concurrent.futures import ThreadPoolExecutor

load_dotenv()  # This one line loads your .env file

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

st.set_page_config("MLB Playoff Race Tracker", layout='wide')

# Title
st.markdown("<h1 style='text-align: center;'>MLB Playoff Race Tracker</h1>", unsafe_allow_html=True)

status_placeholder = st.empty()
status_placeholder.info("Loading latest MLB data...")

totaltime = time.time()

def fetch_teams_data():
    return statsapi.get('teams', {'sportId': 1})
    # print(data)


def fetch_standing_data():
    return statsapi.standings_data(season='2025')


# Multithreading for API calls
with ThreadPoolExecutor(max_workers=2) as executor:
    # Submit requests (both start immediately) 
    teams_data_request = executor.submit(fetch_teams_data)
    standings_data_request = executor.submit(fetch_standing_data)

    # Pull responses once there ready
    data = teams_data_request.result()
    standings_data = standings_data_request.result()

time_api_end = time.time()

print(f"APIs take {time_api_end - totaltime:.3f} seconds")
mlb_teams = data['teams']

# print((mlb_teams[1]))

# test_team_id = statsapi.team_leaders(teamId='112', leaderCategories='hits')
# print(test_team_id)

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

# print(standings_lookup[115])

# print(standings_lookup[146])

all_team_data = []

start_time = time.time()

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

    all_team_data.append(team_data)

# Single batch insert after the loop
try:
    response = supabase.table('teams').upsert(all_team_data, on_conflict='team_id').execute()
    end_time = time.time()
    print(f"Successfully updated {len(all_team_data)} teams in {end_time - start_time:.3f} seconds")
except Exception as e:
    print(f"Could not update teams: {e}")
    # Fallback to individual inserts if batch fails
    for team_data in all_team_data:
        try:
            response = supabase.table('teams').upsert(team_data, on_conflict='team_id').execute()
            print(f"Inserted/Updated: {team_data['team_name']}")
        except Exception as individual_error:
            print(f"Could not update {team_data['team_name']}: {individual_error}")


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


playoff_time_start = time.time()

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

# print(division_winners_NL)

# print(wildcard_teams_NL)


playoff_position = 1
    
# Seeds 1-3: Division winners (already sorted by win % and league_rank)
for team in division_winners_NL:
    playoff_rank_NL[team['team_id']] = playoff_position
    playoff_position += 1

# Seeds 4-15: Remaining teams
for team in wildcard_teams_NL:
    playoff_rank_NL[team['team_id']] = playoff_position
    playoff_position += 1

# print("NL Playoff Rankings:")
# print(playoff_rank_NL)

playoff_rank_NL_data = []

for team_id in playoff_rank_NL:
    playoff_position_data = {
        'team_id': team_id,                           # Use the key (team_id)
        'playoff_position': playoff_rank_NL[team_id]  # Use the value (playoff_position)
    }
    # print(playoff_position_data)
    playoff_rank_NL_data.append(playoff_position_data)

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

# print(division_winners_AL)

# print(wildcard_teams_AL)


playoff_position = 1
    
# Seeds 1-3: Division winners (already sorted by win % and league_rank)
for team in division_winners_AL:
    playoff_rank_AL[team['team_id']] = playoff_position
    playoff_position += 1

# Seeds 4-15: Remaining teams
for team in wildcard_teams_AL:
    playoff_rank_AL[team['team_id']] = playoff_position
    playoff_position += 1

# print("AL Playoff Rankings:")
# print(playoff_rank_AL)


playoff_rank_AL_data = []

for team_id in playoff_rank_AL:
    playoff_position_data = {
        'team_id': team_id,                           # Use the key (team_id)
        'playoff_position': playoff_rank_AL[team_id]  # Use the value (playoff_position)
    }
    # print(playoff_position_data)
    playoff_rank_AL_data.append(playoff_position_data)

all_playoff_data = playoff_rank_NL_data + playoff_rank_AL_data

response = supabase.table('teams').upsert(all_playoff_data, on_conflict='team_id').execute()

playoff_time_end = time.time()

print(f"Playoff_rank has taken {playoff_time_end - playoff_time_start:.3f} seconds")

def division_NL_sort_key(national_league_teams):
    return (national_league_teams['division']['name'])

def division_AL_sort_key(american_league_teams):
    return (american_league_teams['division']['name'])

national_league_teams.sort(key=division_NL_sort_key)

american_league_teams.sort(key=division_AL_sort_key)

# print(national_league_teams[1])

# for team in national_league_teams:
#     print(team['name'])

# for team in american_league_teams:
#     print(team['name'])


def create_divisions_dict(teams):
    divisions = {}
    for team in teams:
        standings = standings_lookup.get(team['id'])
        division = team['division']['name']
        
        if division not in divisions:
            divisions[division] = {}
        
        # Convert div_rank to int for proper indexing
        div_rank = int(standings['div_rank'])
        
        divisions[division][div_rank] = {
            'team': team,
            'standings': standings,
            'losses': standings['l'],
            'wins': standings['w'],
            'team_name': team['name']
        }
    
    # # Print divisions
    # for division_name, teams_in_div in divisions.items():
    #     # print(f"\n{division_name}:")
    #     for rank in sorted(teams_in_div.keys()):
    #         team_info = teams_in_div[rank]
    #         # print(f"  {rank}. {team_info['team_name']} ({team_info['wins']}-{team_info['losses']})")
    
    return divisions

divisions_NL = create_divisions_dict(national_league_teams)
divisions_AL = create_divisions_dict(american_league_teams)



# Division (Magic Number) Distance to finish line calculations (Priority 1)

# 163 (starting zone) Magic Number
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


def calculate_division_magic_numbers(teams, divisions_dict):
    for team in teams:
        standings = standings_lookup.get(team['id'])
        division = team['division']['name']
        
        if int(standings['div_rank']) == 1:
            # Only calculate for first place teams
            remaining_games = 162 - (standings['w'] + standings['l'])
            second_place_losses = divisions_dict[division][2]['losses']
            team['magic_number_win_division'] = remaining_games + 1 - (second_place_losses - standings['l'])
            # print(f"{team['name']}: Division Magic Number = {team['magic_number_win_division']}")
        else:
            # Set to NULL for non-first place teams
            team['magic_number_win_division'] = None
            # print(f"{team['name']}: Not in first place - no division magic number")

# Use it for both leagues
calculate_division_magic_numbers(national_league_teams, divisions_NL)
calculate_division_magic_numbers(american_league_teams, divisions_AL)



# Distance calculation for race track visual
def calculate_distance_from_clinch(teams, divisions_dict):
    for team in teams:
        standings = standings_lookup.get(team['id'])
        division = team['division']['name']
        
        # Find the division leader's magic number
        division_leader = divisions_dict[division][1]  # First place team
        leader_magic_number = division_leader['team'].get('magic_number_win_division', 0)
        
        if int(standings['div_rank']) == 1:
            # Division leader: distance = their magic number
            team['distance_from_clinched_division'] = leader_magic_number
        else:
            # Other teams: leader's magic number + games back
            games_back = float(standings['gb']) if standings['gb'] != '-' else 0.0
            team['distance_from_clinched_division'] = leader_magic_number + games_back
        
        # print(f"{team['name']}: Distance from division clinch = {team['distance_from_clinched_division']}")

calculate_distance_from_clinch(national_league_teams, divisions_NL)
calculate_distance_from_clinch(american_league_teams, divisions_AL)


# Team Elimination

def add_elimination_status(teams):
    for team in teams:
        standings = standings_lookup.get(team['id'])
        
        # Check if eliminated (API returns 'E' for eliminated teams)
        team['eliminated_from_division'] = standings['elim_num'] == 'E'
        team['eliminated_from_playoffs'] = standings['wc_elim_num'] == 'E'
        
        # print(f"{team['name']}: Div Eliminated = {team['eliminated_from_division']}, Playoff Eliminated = {team['eliminated_from_playoffs']}")

# Add this to your code
add_elimination_status(national_league_teams)
add_elimination_status(american_league_teams)


all_remaining_database_update_data = []

def update_database_with_magic_numbers_and_elimination():
    start_time = time.time()
    # Update all teams with magic numbers and elimination status
    all_teams = national_league_teams + american_league_teams

    for team in all_teams:
        standings = standings_lookup.get(team['id'])
        
        # Get elimination status from API (convert 'E' to 1, anything else to 0)
        eliminated_from_division = 1 if standings['elim_num'] == 'E' else 0
        eliminated_from_wildcard = 1 if standings['wc_elim_num'] == 'E' else 0
        
        # Get magic numbers (Already calculated before)
        magic_number_division = team.get('magic_number_win_division', None)
        distance_from_clinch = team.get('distance_from_clinched_division', None)
        
        # Data for database update
        update_data = {
            'team_id': team['id'],
            'magic_number_division': magic_number_division,
            'distance_from_clinched_division': distance_from_clinch,
            'eliminated_from_division': eliminated_from_division,
            'eliminated_from_wildcard': eliminated_from_wildcard
        }

        all_remaining_database_update_data.append(update_data)
        
    try:
        response = supabase.table('teams').upsert(all_remaining_database_update_data, on_conflict='team_id').execute()
        end_time = time.time()
        print(f"Successfully updated {len(all_remaining_database_update_data)} teams in {end_time - start_time:.3f} seconds")
    except Exception as e:
        print(f"Could not update teams: {e}") 

        # Fallback to individual inserts if batch fails
        for update_data  in all_remaining_database_update_data:
            try:
                response = supabase.table('teams').upsert(update_data , on_conflict='team_id').execute()
                print(f"Updated team {update_data['team_id']}")
            except Exception as e:
                print(f"Error updating team {update_data['team_id']}: {e}")

# Updates magic_numbers_and_elimination in database
update_database_with_magic_numbers_and_elimination()

status_placeholder.empty()

col1, col2 = st.columns(2)

# American League (Left Side)
with col1:
    st.markdown("<h2 style='text-align: center;'>American League</h2>", unsafe_allow_html=True)
    
    # Order divisions geographically: East, Central, West
    division_order = ['American League East', 'American League Central', 'American League West']
    for division_name in division_order:
        if division_name in divisions_AL:
            teams_in_div = divisions_AL[division_name]
            st.markdown(f"<h3 style='color: #ffd93d; text-align: center; margin-bottom: 20px; font-size: 1.3rem;'>{division_name}</h3>", unsafe_allow_html=True)
            
            # Create sub-columns within AL: lanes take 2/3, data takes 1/3
            lane_col, data_col = st.columns([2, 1])
            
            with lane_col:
                # Build HTML for racing lanes only
                lanes_html = """
                <div style="display: flex; flex-direction: column; gap: 8px;">
                """
                
                # Create a lane for each team
                for rank in sorted(teams_in_div.keys()):
                    team_info = teams_in_div[rank]
                    team = team_info['team']
                    standings = team_info['standings']
                    
                    # Calculate position based on distance_from_clinched_division
                    distance = team.get('distance_from_clinched_division', 80)
                    max_distance = 163
                    position_percent = ((max_distance - distance) / max_distance) * 85  # Max 85% to leave room for finish zone
                    
                    # Check if team has clinched division (magic number 0 or less)
                    magic_number = team.get('magic_number_win_division', None)
                    has_clinched = magic_number is not None and magic_number <= 0
                    
                    # If clinched, move them past the finish line
                    if has_clinched:
                        position_percent = 92  # Place them clearly past the finish line
                    
                    # Determine team circle style based on status - add transparency
                    if has_clinched and int(standings['div_rank']) == 1:
                        bg_color = "linear-gradient(135deg, rgba(76,175,80,0.9), rgba(102,187,106,0.9))"
                        border_color = "#4caf50"
                        text_color = "white"
                    elif int(standings['div_rank']) == 1:
                        bg_color = "linear-gradient(135deg, rgba(255,217,61,0.9), rgba(255,237,78,0.9))"
                        border_color = "#ffd93d"
                        text_color = "#333"
                    elif standings.get('wc_rank', 99) != '-' and int(standings.get('wc_rank', 99)) <= 3:
                        bg_color = "linear-gradient(135deg, rgba(77,150,255,0.9), rgba(103,181,255,0.9))"
                        border_color = "#4d96ff"
                        text_color = "white"
                    elif team_info['standings'].get('elim_num') == 'E':
                        bg_color = "linear-gradient(135deg, rgba(66,66,66,0.8), rgba(97,97,97,0.8))"
                        border_color = "#666"
                        text_color = "#ccc"
                    else:
                        bg_color = "linear-gradient(135deg, rgba(158,158,158,0.8), rgba(189,189,189,0.8))"
                        border_color = "#9e9e9e"
                        text_color = "#333"
                    
                    # Use abbreviation unless eliminated
                    team_display = team['abbreviation']
                    
                    lanes_html += f"""
                        <!-- Lane for {team['abbreviation']} -->
                        <div style="position: relative; height: 50px; background: linear-gradient(90deg, rgba(220,53,69,0.15) 0%, rgba(255,193,7,0.15) 35%, rgba(40,167,69,0.15) 85%, rgba(40,167,69,0.2) 100%); border-radius: 25px; border: 1px solid rgba(255,255,255,0.15); overflow: hidden;">
                            
                            <!-- Track markers -->
                            <div style="position: absolute; top: 30%; bottom: 30%; left: 5%; right: 8%; border-top: 1px dashed rgba(255,255,255,0.3); border-bottom: 1px dashed rgba(255,255,255,0.3);"></div>
                            
                            <!-- Finish line -->
                            <div style="position: absolute; right: 8%; top: 8%; bottom: 8%; width: 3px; background: linear-gradient(180deg, #28a745, #40e95e); border-radius: 1px; box-shadow: 0 0 4px rgba(40,167,69,0.4);"></div>
                            
                            <!-- Team car -->
                            <div style="position: absolute; top: 50%; transform: translateY(-50%); left: {position_percent}%; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 8px; color: {text_color}; background: {bg_color}; border: 2px solid {border_color}; transition: all 0.3s ease; z-index: 10; {'box-shadow: 0 0 10px rgba(40,167,69,0.6);' if has_clinched else ''}">
                                {team_display}
                            </div>
                        </div>
                    """
                
                lanes_html += "</div>"
                st.html(lanes_html)
            
            with data_col:
                # Build HTML for team data only - single line format to match lane height exactly
                data_html = '<div style="display: flex; flex-direction: column; gap: 8px;">'
                
                for rank in sorted(teams_in_div.keys()):
                    team_info = teams_in_div[rank]
                    team = team_info['team']
                    standings = team_info['standings']
                    
                    record = f"{team_info['wins']}-{team_info['losses']}"
                    games_back = team_info['standings']['gb'] if team_info['standings']['gb'] != '-' else "LEAD"
                    win_pct = f"{team_info['wins']/(team_info['wins'] + team_info['losses']):.3f}"
                    
                    # Magic number logic - only show if not clinched and is division leader
                    magic_number = team.get('magic_number_win_division', None)
                    has_clinched = magic_number is not None and magic_number <= 0
                    magic_text = ""
                    if not has_clinched and magic_number is not None and int(standings['div_rank']) == 1:
                        magic_text = f" • Magic #: {magic_number}"
                    
                    # Status text and color
                    if has_clinched and int(standings['div_rank']) == 1:
                        status = "CLINCHED DIVISION"
                        status_color = "#4caf50"
                        emoji = "🏆"
                    elif int(standings['div_rank']) == 1:
                        status = "LEADING"
                        status_color = "#ffd93d"
                        emoji = "🥇"
                    elif standings.get('wc_rank', 99) != '-' and int(standings.get('wc_rank', 99)) <= 3:
                        status = f"PLAYOFFS • {games_back} GB"
                        status_color = "#4d96ff"
                        emoji = "🎯"
                    elif team_info['standings'].get('elim_num') == 'E':
                        status = "ELIMINATED"
                        status_color = "#666"
                        emoji = "❌"
                    else:
                        status = f"CHASING • {games_back} GB"
                        status_color = "#9e9e9e"
                        emoji = "⚔️"
                    
                    # Single line format matching lane height exactly (50px)
                    data_html += f"""
                        <div style="height: 50px; display: flex; align-items: center; text-align: left; padding: 0 12px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 3px solid {status_color};">
                            <div style="font-size: 0.85rem; line-height: 1.2;">
                                <div style="font-weight: 600; color: white;">{emoji} {team['name']}</div>
                                <div style="font-size: 0.75rem; opacity: 0.8;">{record} ({win_pct}){magic_text} • <span style="color: {status_color};">{status}</span></div>
                            </div>
                        </div>
                    """
                
                data_html += "</div>"
                st.html(data_html)

# National League (Right Side)
with col2:
    st.markdown("<h2 style='text-align: center;'>National League</h2>", unsafe_allow_html=True)
    
    # Order divisions geographically: East, Central, West
    division_order = ['National League East', 'National League Central', 'National League West']
    for division_name in division_order:
        if division_name in divisions_NL:
            teams_in_div = divisions_NL[division_name]
            st.markdown(f"<h3 style='color: #ffd93d; text-align: center; margin-bottom: 20px; font-size: 1.3rem;'>{division_name}</h3>", unsafe_allow_html=True)
            
            # Create sub-columns within NL: lanes take 2/3, data takes 1/3
            lane_col, data_col = st.columns([2, 1])
            
            with lane_col:
                # Build HTML for racing lanes only
                lanes_html = """
                <div style="display: flex; flex-direction: column; gap: 8px;">
                """
                
                # Create a lane for each team
                for rank in sorted(teams_in_div.keys()):
                    team_info = teams_in_div[rank]
                    team = team_info['team']
                    standings = team_info['standings']
                    
                    # Calculate position based on distance_from_clinched_division
                    distance = team.get('distance_from_clinched_division', 80)
                    max_distance = 163
                    position_percent = ((max_distance - distance) / max_distance) * 85  # Max 85% to leave room for finish zone
                    
                    # Check if team has clinched division (magic number 0 or less)
                    magic_number = team.get('magic_number_win_division', None)
                    has_clinched = magic_number is not None and magic_number <= 0
                    
                    # If clinched, move them past the finish line
                    if has_clinched:
                        position_percent = 92  # Place them clearly past the finish line
                    
                    # Determine team circle style based on status
                    if has_clinched and int(standings['div_rank']) == 1:
                        bg_color = "linear-gradient(135deg, rgba(76,175,80,0.9), rgba(102,187,106,0.9))"
                        border_color = "#4caf50"
                        text_color = "white"
                    elif int(standings['div_rank']) == 1:
                        bg_color = "linear-gradient(135deg, rgba(255,217,61,0.9), rgba(255,237,78,0.9))"
                        border_color = "#ffd93d"
                        text_color = "#333"
                    elif standings.get('wc_rank', 99) != '-' and int(standings.get('wc_rank', 99)) <= 3:
                        bg_color = "linear-gradient(135deg, rgba(77,150,255,0.9), rgba(103,181,255,0.9))"
                        border_color = "#4d96ff"
                        text_color = "white"
                    elif team_info['standings'].get('elim_num') == 'E':
                        bg_color = "linear-gradient(135deg, rgba(66,66,66,0.8), rgba(97,97,97,0.8))"
                        border_color = "#666"
                        text_color = "#ccc"
                    else:
                        bg_color = "linear-gradient(135deg, rgba(158,158,158,0.8), rgba(189,189,189,0.8))"
                        border_color = "#9e9e9e"
                        text_color = "#333"
                    
                    # Use abbreviation unless eliminated
                    team_display = team['abbreviation']
                    
                    lanes_html += f"""
                        <!-- Lane for {team['abbreviation']} -->
                        <div style="position: relative; height: 50px; background: linear-gradient(90deg, rgba(220,53,69,0.15) 0%, rgba(255,193,7,0.15) 35%, rgba(40,167,69,0.15) 85%, rgba(40,167,69,0.2) 100%); border-radius: 25px; border: 1px solid rgba(255,255,255,0.15); overflow: hidden;">
                            
                            <!-- Track markers -->
                            <div style="position: absolute; top: 30%; bottom: 30%; left: 5%; right: 8%; border-top: 1px dashed rgba(255,255,255,0.3); border-bottom: 1px dashed rgba(255,255,255,0.3);"></div>
                            
                            <!-- Finish line -->
                            <div style="position: absolute; right: 8%; top: 8%; bottom: 8%; width: 3px; background: linear-gradient(180deg, #28a745, #40e95e); border-radius: 1px; box-shadow: 0 0 4px rgba(40,167,69,0.4);"></div>
                            
                            <!-- Team car -->
                            <div style="position: absolute; top: 50%; transform: translateY(-50%); left: {position_percent}%; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 8px; color: {text_color}; background: {bg_color}; border: 2px solid {border_color}; transition: all 0.3s ease; z-index: 10; {'box-shadow: 0 0 10px rgba(40,167,69,0.6);' if has_clinched else ''}">
                                {team_display}
                            </div>
                        </div>
                    """
                
                lanes_html += "</div>"
                st.html(lanes_html)
            
            with data_col:
                # Build HTML for team data only - single line format to match lane height exactly
                data_html = '<div style="display: flex; flex-direction: column; gap: 8px;">'
                
                for rank in sorted(teams_in_div.keys()):
                    team_info = teams_in_div[rank]
                    team = team_info['team']
                    standings = team_info['standings']
                    
                    record = f"{team_info['wins']}-{team_info['losses']}"
                    games_back = team_info['standings']['gb'] if team_info['standings']['gb'] != '-' else "LEAD"
                    win_pct = f"{team_info['wins']/(team_info['wins'] + team_info['losses']):.3f}"
                    
                    # Magic number logic - only show if not clinched and is division leader
                    magic_number = team.get('magic_number_win_division', None)
                    has_clinched = magic_number is not None and magic_number <= 0
                    magic_text = ""
                    if not has_clinched and magic_number is not None and int(standings['div_rank']) == 1:
                        magic_text = f" • Magic #: {magic_number}"
                    
                    # Status text and color
                    if has_clinched and int(standings['div_rank']) == 1:
                        status = "CLINCHED DIVISION"
                        status_color = "#4caf50"
                        emoji = "🏆"
                    elif int(standings['div_rank']) == 1:
                        status = "LEADING"
                        status_color = "#ffd93d"
                        emoji = "🥇"
                    elif standings.get('wc_rank', 99) != '-' and int(standings.get('wc_rank', 99)) <= 3:
                        status = f"PLAYOFFS • {games_back} GB"
                        status_color = "#4d96ff"
                        emoji = "🎯"
                    elif team_info['standings'].get('elim_num') == 'E':
                        status = "ELIMINATED"
                        status_color = "#666"
                        emoji = "❌"
                    else:
                        status = f"CHASING • {games_back} GB"
                        status_color = "#9e9e9e"
                        emoji = "⚔️"
                    
                    # Single line format matching lane height exactly (50px)
                    data_html += f"""
                        <div style="height: 50px; display: flex; align-items: center; text-align: left; padding: 0 12px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 3px solid {status_color};">
                            <div style="font-size: 0.85rem; line-height: 1.2;">
                                <div style="font-weight: 600; color: white;">{emoji} {team['name']}</div>
                                <div style="font-size: 0.75rem; opacity: 0.8;">{record} ({win_pct}){magic_text} • <span style="color: {status_color};">{status}</span></div>
                            </div>
                        </div>
                    """
                
                data_html += "</div>"
                st.html(data_html)

endtime = time.time() - totaltime

print(f"Total time to run the whole program {endtime:.3f} seconds")

# Try all the api calls if those dont work then pull data from database (Priority 3)
