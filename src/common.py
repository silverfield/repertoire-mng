import os
import json

cur_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = f'{cur_dir}/../data'
OUTPUT_DIR = f'{cur_dir}/../output'

TYPE_BT = 'bt'
TYPE_NBT = 'nbt'

PREFIX = '/d'
if not os.path.exists(PREFIX):
    PREFIX = 'G:'
PDF_DIRS = [f'{PREFIX}/music/akordy/chords', f'{PREFIX}/music/akordy/fero-hajnovic']
REPE_FOLDER = f'{PREFIX}/music/repertoire'

def mkdir(d):
    if not os.path.exists(d):
        os.mkdir(d)
mkdir(DATA_DIR)
mkdir(OUTPUT_DIR)

COMMON_ABBRS = [
    ['FH', 'Fero Hajnovic'],
    ['DS', 'Dire Straits'],
    ['MK', 'Mark Knopfler'],
    ['EC', 'Eric Clapton'],
    ['PF', 'Pink Floyd'],
]
COMMON_ABBRS.extend([abbr[::-1] for abbr in COMMON_ABBRS])

def get_artist(item):
    return item.split(' - ')[0]

def get_name(item):
    return item.split(' - ')[1]

def get_full_name(item):
    return f'{get_artist(item)} - {get_name(item)}'

def is_bt(item):
    return item.split(' - ')[-1] == 'BT'

with open(f'{DATA_DIR}/song-props.json', 'r') as f:
    PROPS = json.loads(f.read())
    PROPS = {i['name'].lower(): i for i in PROPS}

def get_song_props(item):
    key = get_full_name(item).lower()

    if key in PROPS:
        return PROPS[key]
    else:
        for abbr in COMMON_ABBRS:
            key_rep = key.replace(abbr[0].lower(), abbr[1].lower())
            if key_rep in PROPS:
                return PROPS[key_rep]

    err_msg = f'{item} not found in props'
    print(err_msg)
    print('Maybe add something like this to song-props.json:')
    print(json.dumps({
        "name": item,
        "tags": [],
        "used": True,
        "versions": ['nbt'],
        "loop": None
    }, indent=4))

    raise KeyError(err_msg)