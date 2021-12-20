import json

with open('checkbox_config.txt', 'r') as f:
    checkbox_config = json.load(f)
print(checkbox_config)
