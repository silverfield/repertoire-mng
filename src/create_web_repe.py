import json
from common import *

def make_repe_for_web():
    with open(f'{DATA_DIR}/pl-all.json', 'r') as f:
        data = json.loads(f.read())

        new_data = []
        for item in data:
            if 'webrepe' in item and item['webrepe'] == False:
                continue

            name = item['name']
            if '-' in name:
                name = name.split('-')[1].strip()
            
            artist = item['name'].split('-')[0].strip()
            if artist == 'EC':
                artist = 'Eric Clapton'
            if artist == 'PF':
                artist = 'Pink Floyd'
            if artist == 'A Star is Born':
                artist += ' soundtrack'
            if artist == 'The Greatest Showman':
                artist += ' soundtrack'
            if artist == 'DS':
                artist = 'Dire Straits'
            if artist == 'MK':
                artist = 'Mark Knopfler'
            if artist == 'FH':
                artist = 'Fero Hajnovic'

            tp = item['type']

            tags = []
            if 'tags' in item:
                tags = item['tags']

            new_item = {
                'artist': artist,
                'name': name,
                'bt': tp == 'bt',
                'nbt': tp == 'nbt',
                'tags': tags
            }

            matching_items = [
                (i, item) 
                for i, item in enumerate(new_data) 
                if name.lower() == item['name'].lower() and artist.lower() == item['artist'].lower()
            ]
            if len(matching_items) > 0:
                matching_item = matching_items[0][1]
                pos = matching_items[0][0]
                new_item['bt'] = new_item['bt'] or matching_item['bt']
                new_item['nbt'] = new_item['nbt'] or matching_item['nbt']
                new_item['tags'] = list(set(new_item['tags'] + matching_item['tags']))
                new_data[pos] = new_item
            else:
                new_data.append(new_item)

        with open(f'{OUTPUT_DIR}/web_repe.json', 'w') as fout:
            fout.write(json.dumps(new_data, indent=4))


if __name__ == "__main__":
    make_repe_for_web()