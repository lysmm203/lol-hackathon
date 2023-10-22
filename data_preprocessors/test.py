import json

problem_file = './games/ESPORTSTMNT02_3214937_cleaned.json'

with open(problem_file, 'r') as file:
    game = json.load(file)

print(game)





