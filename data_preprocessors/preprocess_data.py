import json
import os
import pandas as pd
import shutil

teams_json_path = 'esports-data/teams.json'
# Load all the data from teams_json_path. Each entry will have the team_id, name of the team, slug, and acronym



with open(teams_json_path, 'r') as teams_json:
    all_teams = json.load(teams_json)

df_columns = [
    'team',
    'gold_diff',
    'gold_diff_14min',
    'elder_dragon_kills',
    'baron_kills',
    'dragon_kills',
    'herald_kills',
    'team_KD_ratio',
    'game_length',
    'objectives_stolen_away',
    'first_turret_kill',
    'second_turret_kill',
    'third_turret_kill',
    'baron_powerplay',
    'first_blood',
    'result'
]

leagues = ["LCS", "LEC", "CBLOL", "LCK", "LJL", "LLA", "LPL", "PCS", "VCS"]

all_regions = {}

for league in leagues:
    all_regions[league] = pd.DataFrame(columns=df_columns)

games_directory = './games'

try:
    files = os.listdir(games_directory)
except FileNotFoundError:
    print("Directory not found")

filtered_tournaments_path = './esports-data/filtered_tournaments.json'
filtered_leagues_path = './esports-data/filtered_leagues.json'


def get_league_id_from_team_id(team_id):
    with open(filtered_tournaments_path, 'r') as tournaments_json:
        try:
            tournaments = json.load(tournaments_json)
        except json.decoder.JSONDecodeError as e:
            print("JSON decoding error:", str(e))
            print("Problematic data:", tournaments_json[e.pos - 10:e.pos + 10])

        league_id = None

        for tournament in tournaments:
            if league_id is not None:
                break

            if tournament['name'] == 'MSI 2023':
                continue

            if len(tournament['stages']) == 1:
                # PCS data is odd: the length of tournament['stages'] for their regular season is 1
                if tournament['slug'] != 'pcs_summer_2023':
                    continue

            matches = tournament['stages'][0]['sections'][0]['matches']
            for match in matches:
                for team in match['teams']:
                    if team['id'] == team_id:
                        league_id = tournament['leagueId']

        with open(filtered_leagues_path, 'r') as leagues_json:
            leagues = json.load(leagues_json)
            for league in leagues:
                if league_id == league['id']:
                    return league['name']


def process_data(input):
    counter = 0
    for file_path in files:
        file_name = os.path.join(games_directory, file_path)



        with (open(file_name, 'r') as file):
            game = json.load(file)
            game_length = game['gameEnd']['gameTime'] / 60000

            # Literally one game has this error
            try:
                victor_id = game['gameEnd']['winningTeam']
                loser_id = 100 if victor_id == 200 else 200
            except:
                continue



            victor_team, loser_team = None, None
            # Identify the league of each team
            for key in game['gameInfo']['teamMappingID']:
                team_id = game['gameInfo']['teamMappingID'][key]
                league = get_league_id_from_team_id(team_id)

                for team in all_teams:
                    if team_id == team['team_id']:
                        if key == str(victor_id):
                            victor_team = team['acronym']
                        else:
                            loser_team = team['acronym']

            if victor_team is None or loser_team is None:
                counter +=1
                print(f'current file: {file_name}')
                print(f'winner: {victor_team}')
                print(f'loser: {loser_team}')
                print(f"counter: {counter}")



            # Determine the team who got first blood
            first_blood_killer_id = game['firstBlood']['killer']
            first_blood_team = 100 if first_blood_killer_id <= 5 else 200

            # Get the final stats of both teams
            victor_final_stats = game['finalStats']['teams'][0 if victor_id == 100 else 1]
            loser_final_stats = game['finalStats']['teams'][0 if loser_id == 100 else 1]

            # Get the gold diff at the end of the game
            victor_gold_difference = victor_final_stats['totalGold'] - loser_final_stats['totalGold']
            loser_gold_difference = loser_final_stats['totalGold'] - victor_final_stats['totalGold']

            # Get the gold diff at 14 minutes (when turret plating expires)
            for team in game['min14']['teams']:
                if team['teamID'] == victor_id:
                    victor_gold_14min = team['totalGold']
                else:
                    loser_gold_14min = team['totalGold']

            victor_gold_difference_14min = victor_gold_14min - loser_gold_14min
            loser_gold_difference_14min = victor_gold_difference_14min * -1


            # Herald killcount
            victor_herald_killcount, loser_herald_killcount = 0, 0

            # Elder dragon killcount
            victor_elder_killcount, loser_elder_killcount = 0, 0

            # Number of objectives stolen for each team
            victor_stolen, loser_stolen = 0, 0

            # The turrets destroyed for each team
            victor_turrets_killed, loser_turrets_killed = [],[]

            # Baron powerplay
            victor_baron_powerplay, loser_baron_powerplay = [], []
            if len(game['baronPowerPlay']) != 0:
                for power_play in game['baronPowerPlay']:
                    baron_killer_id = power_play[0]['killerTeamID']
                    baron_killer_initial_gold, other_team_initial_gold = 0, 0
                    baron_killer_subsequent_gold, other_team_subsequent_gold = 0, 0

                    for team in power_play[1]['teams']:
                        if team['teamID'] == baron_killer_id:
                            baron_killer_initial_gold = team['totalGold']
                        else:
                            other_team_initial_gold = team['totalGold']

                    for team in power_play[2]['teams']:
                        if team['teamID'] == baron_killer_id:
                            baron_killer_subsequent_gold = team['totalGold']
                        else:
                            other_team_subsequent_gold = team['totalGold']

                    powerplay_gold = (baron_killer_subsequent_gold - baron_killer_initial_gold) \
                                     - (other_team_subsequent_gold - other_team_initial_gold)

                    if baron_killer_id == victor_id:
                        victor_baron_powerplay.append(powerplay_gold)
                    else:
                        loser_baron_powerplay.append(powerplay_gold)


            if not victor_baron_powerplay:
                victor_baron_powerplay = 0
            else:
                victor_baron_powerplay = sum(victor_baron_powerplay) / len(victor_baron_powerplay)

            if not loser_baron_powerplay:
                loser_baron_powerplay = 0
            else:
                loser_baron_powerplay = sum(loser_baron_powerplay) / len(loser_baron_powerplay)


            # Calculate KD ratio
            victor_kd_ratio, loser_kd_ratio = 0, 0
            victor_kd_ratio = victor_final_stats['championsKills'] / victor_final_stats['deaths'] \
                if victor_final_stats['deaths'] != 0 else victor_final_stats['championsKills']
            loser_kd_ratio = loser_final_stats['championsKills'] / loser_final_stats['deaths'] \
                if loser_final_stats['deaths'] != 0 else loser_final_stats['championsKills']

            for events in game['objectives']:
                # Calculate number of elder dragons killed for each team
                if events['eventType'] == 'epic_monster_kill':

                    if events['monsterType'] == 'dragon' and events['dragonType'] == 'elder':
                        if events['killerTeamID'] == victor_id:
                            victor_elder_killcount += 1
                        else:
                            loser_elder_killcount += 1

                    if events['monsterType'] == 'riftHerald':
                        if events['killerTeamID'] == victor_id:
                            victor_herald_killcount += 1
                        else:
                            loser_herald_killcount += 1

                # Calculate the number of times an objective has been stolen
                if 'killType' in events and events['killType'] == 'steal':
                    if events['killerTeamID'] == victor_id:
                        loser_stolen += 1
                    else:
                        victor_stolen += 1

                # Keep track of the turrets destroyed
                if events['eventType'] == 'building_destroyed':
                    if events['teamID'] == loser_id:
                        if events['buildingType'] == 'turret':
                            appending_dict = {
                                'turretTier': events['turretTier'],
                                'lane': events['lane'],
                                'gameTime': events['gameTime'],
                            }
                            victor_turrets_killed.append(appending_dict)


                    if events['teamID'] == victor_id:
                        if events['buildingType'] == 'turret':
                            appending_dict = {
                                'turretTier': events['turretTier'],
                                'lane': events['lane'],
                                'gameTime': events['gameTime'],
                            }
                            loser_turrets_killed.append(appending_dict)

            victor_second_turret, victor_third_turret, loser_second_turret, loser_third_turret = None, None, None, None

            for turret in victor_turrets_killed:
                if turret['turretTier'] == 'inner':
                    victor_second_turret = turret['gameTime']

                if turret['turretTier'] == 'base':
                    victor_third_turret = turret['gameTime']

            if loser_turrets_killed:
                for turret in loser_turrets_killed:
                    if turret['turretTier'] == 'inner':
                        loser_second_turret = turret['gameTime']

                    if turret['turretTier'] == 'base':
                        loser_third_turret = turret['gameTime']




        victor = pd.Series({
            'team': victor_team,
            'gold_diff': victor_gold_difference,
            'gold_diff_14min': victor_gold_difference_14min,
            'elder_dragon_kills': victor_elder_killcount,
            'baron_kills': victor_final_stats['baronKills'],
            'dragon_kills': victor_final_stats['dragonKills'],
            'herald_kills': victor_herald_killcount,
            'team_KD_ratio': victor_kd_ratio,
            'game_length': game_length,
            'objectives_stolen_away': victor_stolen,
            'first_turret_kill': victor_turrets_killed[0]['gameTime'],
            'second_turret_kill': victor_second_turret,
            'third_turret_kill': victor_third_turret,
            'baron_powerplay': victor_baron_powerplay,
            'first_blood': first_blood_team == victor_id,
            'result': 1
        })

        loser = pd.Series({
            'team': loser_team,
            'gold_diff': loser_gold_difference,
            'gold_diff_14min': loser_gold_difference_14min,
            'elder_dragon_kills': loser_elder_killcount,
            'baron_kills': loser_final_stats['baronKills'],
            'dragon_kills': loser_final_stats['dragonKills'],
            'herald_kills': loser_herald_killcount,
            'team_KD_ratio': loser_kd_ratio,
            'game_length': game_length,
            'objectives_stolen_away': loser_stolen,
            'first_turret_kill': loser_turrets_killed[0]['gameTime'] if loser_turrets_killed else None,
            'second_turret_kill': loser_second_turret,
            'third_turret_kill': loser_third_turret,
            'baron_powerplay': loser_baron_powerplay,
            'first_blood': first_blood_team == loser_id,
            'result': 0
        })

        for region in all_regions:
            if region == league:
                all_regions[region] = pd.concat([all_regions[region], victor.to_frame().T], \
                                                ignore_index=True)
                all_regions[region] = pd.concat([all_regions[region], loser.to_frame().T], \
                                                ignore_index=True)
                break



    new_directory_path = 'data_by_league/'
    os.makedirs(new_directory_path, exist_ok=True)


    for league in all_regions:
        output_directory = new_directory_path + league + '.csv'
        all_regions[league].to_csv(output_directory, index=False)



process_data("region")

