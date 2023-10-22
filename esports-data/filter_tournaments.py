import json

with open('tournaments.json', 'r') as f:
    data = json.load(f)

with open('filtered_leagues.json', 'r') as l:
    leagues = json.load(l)

major_league_ids = [obj['id'] for obj in leagues]

def cfilter(obj):
    # Only include tournaments after MSI 2023 ended 
    if obj['leagueId'] not in major_league_ids: return False
    if obj['startDate'] < "2023-05-02" or obj['startDate'] > '2023-10-14': return False
    return True

filtered_data = [item for item in data if cfilter(item)]

for tournament in filtered_data:
    print(tournament['slug'])

with open('filtered_tournaments.json', 'w') as new:
    json.dump(filtered_data, new, indent=4)

