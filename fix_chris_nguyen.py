import json

# Load the league history JSON file
with open('league_history.json', 'r') as f:
    data = json.load(f)

# Standardize "Chris  Nguyen" to "Chris Nguyen" across all years
for year, year_data in data.items():
    for team in year_data['teams']:
        if team['owner'] == 'Chris  Nguyen':
            team['owner'] = 'Chris Nguyen'
    # Also update head-to-head records if they exist
    if 'head_to_head' in year_data:
        head_to_head = year_data['head_to_head']
        if 'Chris  Nguyen' in head_to_head:
            head_to_head['Chris Nguyen'] = head_to_head.pop('Chris  Nguyen')
        for owner in head_to_head:
            if 'Chris  Nguyen' in head_to_head[owner]:
                head_to_head[owner]['Chris Nguyen'] = head_to_head[owner].pop('Chris  Nguyen')

# Save the updated JSON file
with open('league_history.json', 'w') as f:
    json.dump(data, f, indent=4)

print("Chris Nguyen's name has been standardized in league_history.json!")