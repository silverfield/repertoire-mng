import json
from common import *

def make_repe_for_web(pl=None):
    if pl is None:
        data = [p['name'] for p in PROPS]
    else:
        with open(f'{DATA_DIR}/{pl}.json', 'r') as f:
            data = json.loads(f.read())

    web_repe = {}

    for item in data:
        item_props = get_song_props(item)
        if 'used' in item_props and item_props['used'] == False:
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
            'bt': is_bt(item) or ('bt' in item_props['versions']),
            'nbt': not is_bt(item) or ('nbt' in item_props['versions']),
            'tags': tags
        }
        key = f'{artist}_{name}'.lower()

        if key in web_repe:
            web_repe[key]['bt'] = new_item['bt'] or web_repe[key]['bt']
            web_repe[key]['nbt'] = new_item['nbt'] or web_repe[key]['nbt']
            web_repe[key]['tags'] = list(set(new_item['tags'] + web_repe[key]['tags']))
        else:
            web_repe[key] = new_item

    with open(f'{OUTPUT_DIR}/web-repe-{pl}.json', 'w') as fout:
        fout.write(json.dumps(list(web_repe.values()), indent=4))


if __name__ == "__main__":
    make_repe_for_web()  # all songs in song-props
    make_repe_for_web('pl-web-gig-background-nbt')
    make_repe_for_web('pl-web-gig-fri-pub-nbt')
    make_repe_for_web('pl-web-gig-originals')

    import shutil
    for f in os.listdir(OUTPUT_DIR):
        if f.startswith('web-repe'):
            shutil.copyfile(f'{OUTPUT_DIR}/{f}', f'/home/fero/wspace/fhweb/code/src/data/{f}')