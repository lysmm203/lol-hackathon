import requests
import json
import gzip
import shutil
import time
import os
from io import BytesIO


S3_BUCKET_URL = "https://power-rankings-dataset-gprhack.s3.us-west-2.amazonaws.com"
# 1 gameTime = 1 millisecond
ONE_MIN = 60000
THREE_MIN = 3 * ONE_MIN
FIVE_MIN = 5 * ONE_MIN
TEN_MIN = 10 * ONE_MIN
FOURTEEN_MIN = 14 * ONE_MIN
FIFTEEN_MIN = 15 * ONE_MIN

def open_json(file_name):
    data = None
    with open(file_name, 'r') as f:
        data = json.load(f)
    return data

def write_json(file_name, json_data):
    with open(file_name, 'w') as f:
        json.dump(json_data, f, indent=4)


def initializeTimeStamps(timeStamps, cleaned_data):
    for time, name in timeStamps:
        cleaned_data[name] = {}

def addTimeStamps(timeStamps, event, cleaned_data):
    if event['eventType'] == 'stats_update':
        if len(timeStamps) > 0 and timeStamps[0][0] <= int(event['gameTime']):
            cleaned_data[timeStamps[0][1]] = event
            timeStamps.pop(0)

def truncate_game_data(file_name):
    game_data = open_json(f'{file_name}.json') 
    os.remove(f'{file_name}.json')
    game_mapping_data = get_game_mapping()
    cleaned_data = {}
    cleaned_data['gameInfo'] = game_data[0]

    gameID = cleaned_data['gameInfo']['platformGameId']

    cleaned_data['gameInfo']['teamMappingID'] = game_mapping_data[gameID]['teamMapping']

    team200ID = game_mapping_data[gameID]['teamMapping']['200']
    team100ID = game_mapping_data[gameID]['teamMapping']['100']

    cleaned_data['objectives'] = []
    firstBlood = False
    find_baron_one = False
    find_baron_three = False
    cleaned_data['baronKilled'] = False
    cleaned_data['baronPowerPlay'] = []
    baronPowerPlay = []
    baronTime = 0
    timeStamps = [(ONE_MIN, 'min1'), (FIVE_MIN, 'min5'), (TEN_MIN, 'min10'), (FOURTEEN_MIN, 'min14'), (FIFTEEN_MIN, 'min15')]
    initializeTimeStamps(timeStamps, cleaned_data)

    for event in game_data:
        addTimeStamps(timeStamps, event, cleaned_data)
        if event['eventType'] == 'building_destroyed' or (event['eventType'] == 'epic_monster_kill' and event['monsterType'] in ['dragon', 'riftHerald', 'baron']):
            cleaned_data['objectives'].append(event)
            # Baron Event
            if 'monsterType' in event and event['monsterType'] == 'baron':
                baronPowerPlay = [event]
                find_baron_one = True
                cleaned_data['baronKilled'] = True
                baronTime = int(event['gameTime'])
        if (event['eventType'] == 'stats_update'):
            # Check if stats_update is 3 minutes after baron
            if find_baron_three and int(event['gameTime']) > baronTime + THREE_MIN:
                baronPowerPlay.append(event)
                find_baron_three = False
                cleaned_data['baronPowerPlay'].append(baronPowerPlay)
                baronPowerPlay = []
            # Check if stats_update is immidiately after baron 
            elif find_baron_one and int(event['gameTime']) > baronTime:
                baronPowerPlay.append(event) 
                find_baron_one = False
                find_baron_three = True
        if not firstBlood and event['eventType'] == 'champion_kill_special':
            cleaned_data['firstBlood'] = event
            firstBlood = True


       
    cleaned_data['finalStats'] = game_data[-2]
    cleaned_data['gameEnd'] = game_data[-1]

    write_json(f'{file_name}_cleaned.json', cleaned_data)
    #team_mapping_data = get_team_mapping()
    #player_mapping_data = get_player_mapping()
    # For identifying players
    #for player in cleaned_data['gameInfo']['participants']:
    #    participantGameID = str(player['participantID'])
    #    player['participantRealID'] = game_mapping_data[gameID]['participantMapping'][participantGameID]
    #    player['participantHandle'] = get_player_handle(player['participantRealID'], player_mapping_data) 

def get_player_handle(playerID, player_mapping_data):
    if playerID in player_mapping_data: return player_mapping_data[playerID]
    return 'UNKNOWN'
# Returns a dictionary for participants ID and handle
def get_player_mapping():
    mapping_dict = {}
    player_mapping_data = open_json('esports-data/players.json')
    for player in player_mapping_data:
        mapping_dict[player['player_id']] = player['handle']
    return mapping_dict

# Returns a dictionary for gameID where the values stores the participating teams and members
def get_game_mapping():
    mapping_dict = {}
    games_mapping_data = open_json('esports-data/mapping_data.json')
    for game_data in games_mapping_data:
        gameId = game_data['platformGameId']
        mapping_dict[gameId] = game_data
    return mapping_dict

# Returns dict for team mapping
def get_team_mapping():
    mapping_dict = {}
    data = open_json('esports-data/teams.json')
    for team in data:
        mapping_dict[team['team_id']] = team['slug']
    return mapping_dict

# Find the team name based on teamID
def get_team_name(teamID, team_dict):
    if teamID in team_dict: return team_dict[teamID]
    return 'UNKNOWN'


def download_gzip_and_write_to_json(file_name):
   print(file_name)
   local_file_name = file_name.replace(":", "_")
   # If file already exists locally do not re-download game
   if os.path.isfile(f"{local_file_name}.json"):
       return

   response = requests.get(f"{S3_BUCKET_URL}/{file_name}.json.gz")
   if response.status_code == 200:
       try:
           gzip_bytes = BytesIO(response.content)
           with gzip.GzipFile(fileobj=gzip_bytes, mode="rb") as gzipped_file:
               with open(f"{local_file_name}.json", 'wb') as output_file:
                   shutil.copyfileobj(gzipped_file, output_file)
               print(f"{file_name}.json written")
               truncate_game_data(local_file_name)

       except Exception as e:
           print("Error:", e)
   else:
       print(f"Failed to download {file_name}")


def download_esports_files():
   directory = "esports-data"
   if not os.path.exists(directory):
       os.makedirs(directory)

   esports_data_files = ["leagues", "tournaments", "players", "teams", "mapping_data"]
   for file_name in esports_data_files:
       download_gzip_and_write_to_json(f"{directory}/{file_name}")


def download_games(year):
   start_time = time.time()
   with open("esports-data/filtered_tournaments.json", "r") as json_file:
       tournaments_data = json.load(json_file)
   with open("esports-data/mapping_data.json", "r") as json_file:
       mappings_data = json.load(json_file)

   directory = "games"
   if not os.path.exists(directory):
       os.makedirs(directory)

   mappings = {
       esports_game["esportsGameId"]: esports_game for esports_game in mappings_data
   }

   game_counter = 0


   for tournament in tournaments_data:
       start_date = tournament.get("startDate", "")
       if start_date.startswith(str(year)):
           print(f"Processing {tournament['slug']}")
           for stage in tournament["stages"]:
               for section in stage["sections"]:
                   for match in section["matches"]:
                       for game in match["games"]:
                           if game["state"] == "completed":
                               try:
                                   platform_game_id = mappings[game["id"]]["platformGameId"]
                               except KeyError:
                                   print(f"{platform_game_id} {game['id']} not found in the mapping table")
                                   continue

                               download_gzip_and_write_to_json(f"{directory}/{platform_game_id}")
                               game_counter += 1

                           if game_counter % 10 == 0:
                               print(
                                   f"----- Processed {game_counter} games, current run time: \
                                   {round((time.time() - start_time)/60, 2)} minutes"
                               )


if __name__ == "__main__":
   #download_esports_files()
   download_games(2023)
