import json
from common import *

def make_repe_for_web(pl='pl-all'):
    with open(f'{DATA_DIR}/{pl}.json', 'r') as f:
        data = json.loads(f.read())

        web_repe = {}

        for item in data:
            item_props = get_song_props(item)
            if 'webrepe' in item_props and item_props['webrepe'] == False:
                continue

            name = get_name(item)
            artist = get_artist(item)

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

            tags = []
            if 'tags' in item_props:
                tags = item_props['tags']

            new_item = {
                'artist': artist,
                'name': name,
                'bt': is_bt(item),
                'nbt': not is_bt(item),
                'tags': tags
            }
            key = get_full_name(item).lower()

            if key in web_repe:
                web_repe[key]['bt'] = new_item['bt'] or web_repe[key]['bt']
                web_repe[key]['nbt'] = new_item['nbt'] or web_repe[key]['nbt']
                web_repe[key]['tags'] = list(set(new_item['tags'] + web_repe[key]['tags']))
            else:
                web_repe[key] = new_item

        with open(f'{OUTPUT_DIR}/web_repe.json', 'w') as fout:
            fout.write(json.dumps(list(web_repe.values()), indent=4))


if __name__ == "__main__":
    make_repe_for_web('pl-all')