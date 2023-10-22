import json
with open('leagues.json', 'r') as f:
    data = json.load(f)

valid_leagues = ['msi', 'lcs', 'cblol-brazil', 'lck', 'lec', 'ljl-japan', 'lla', 'lpl', 'pcs', 'vcs']

def cfilter(obj):
    if obj['slug'] in valid_leagues: return True
    return False

filtered_data = [item for item in data if cfilter(item)]

with open('filtered_leagues.json', 'w') as new:
    json.dump(filtered_data, new, indent=4)
