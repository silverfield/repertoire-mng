import json
import os
from common import *

def create_bare_loop_pos_file():
    full_song_files = [f for f in os.listdir(f'{REPE_FOLDER}/full-songs') if f.endswith('.mp3')]

    j = {
        f.split('.')[0]: -1 for f in full_song_files
    }

    s = json.dumps(j, indent=4)
    with open(f'./loop-pos.json', 'w') as f:
        f.write(s)

def create_pl_all():
    bts_files = [f for f in os.listdir(f'{REPE_FOLDER}/bts') if f.endswith('.mp3')]
    full_song_files = [f for f in os.listdir(f'{REPE_FOLDER}/full-songs') if f.endswith('.mp3')]
    
    j = [
        f.split('.')[0] for f in sorted(bts_files)
    ] + [
        f.split('.')[0] for f in sorted(full_song_files)
    ]

    s = json.dumps(j, indent=4)
    with open(f'{DATA_DIR}/pl-all.json', 'w') as f:
        f.write(s)


def add_versions():
    with open(f'{DATA_DIR}/song-props.json', 'r') as f:
        data = json.loads(f.read())

    new_data = []
    for d in data:
        d['versions'] = ['bt', 'nbt']
        new_data.append(d)

    s = json.dumps(new_data, indent=4)
    with open(f'{DATA_DIR}/song-props.json', 'w') as f:
        f.write(s)


def add_loop_pos():
    with open(f'{DATA_DIR}/song-props.json', 'r') as f:
        data = json.loads(f.read())

    with open(f'{DATA_DIR}/loop-pos.json', 'r') as f:
        looppos = json.loads(f.read())

    looppos = {
        get_song_props(k)['name']: looppos[k] for k in looppos
    }

    for d in data:
        if d['name'] in looppos:
            d['loop'] = looppos[d['name']]
        else:
            d['loop'] = None

    s = json.dumps(data, indent=4)
    with open(f'{DATA_DIR}/song-props.json', 'w') as f:
        f.write(s)

def rework_busk_pl():
    with open(f'{DATA_DIR}/pl-2020.json', 'r') as f:
        data = json.loads(f.read())

    new_data = {}
    for s in data:
        new_data[s['section']] = [i['name'] for i in s['items']]

    s = json.dumps(new_data, indent=4)
    with open(f'{DATA_DIR}/pl-2020.json', 'w') as f:
        f.write(s)

if __name__ == "__main__":
    rework_busk_pl()