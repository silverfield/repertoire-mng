import os
import json

cur_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = f'{cur_dir}/../data'
OUTPUT_DIR = f'{cur_dir}/../output'

TYPE_BT = 'bt'
TYPE_NBT = 'nbt'

ON_LINUX = os.path.exists('/opt')

PREFIX = '/d'
if not ON_LINUX:
    PREFIX = 'G:'
PDF_DIRS = [f'{PREFIX}/music/akordy/chords', f'{PREFIX}/music/akordy/fero-hajnovic']
REPE_FOLDER = f'{PREFIX}/music/repertoire'

WEBSITE_DATA_DIR = '/home/fero/wspace/fhweb/src/data'
if not ON_LINUX:
    WEBSITE_DATA_DIR = 'G:/wspace/fhweb/fhweb/src/data'

def mkdir(d):
    if not os.path.exists(d):
        os.makedirs(d)
mkdir(DATA_DIR)
mkdir(OUTPUT_DIR)

COMMON_ABBRS = {
    'FH': 'Fero Hajnovic',
    'DS': 'Dire Straits',
    'MK': 'Mark Knopfler',
    'EC': 'Eric Clapton',
    'PF': 'Pink Floyd',
}

def get_artist(item, expand_abbrs=False):
    artist = item.split(' - ')[0]

    if expand_abbrs:
        if artist in COMMON_ABBRS:
            artist = COMMON_ABBRS[artist]

    return artist

def get_name(item):
    return item.split(' - ')[1]

def get_full_name(item, expand_artist_abbrs=False):
    return f'{get_artist(item, expand_artist_abbrs)} - {get_name(item)}'

def is_bt(item):
    return item.split(' - ')[-1] == 'BT'

with open(f'{DATA_DIR}/song-props.json', 'r') as f:
    PROPS = json.loads(f.read())
    if any(len(i['tags']) == 0 for i in PROPS):
        no_tags_props = [i['name'] for i in PROPS if len(i['tags']) == 0]
        raise ValueError(f'Tags not specified for {no_tags_props}')
    PROPS = {i['name'].lower(): i for i in PROPS}
    # print(PROPS)

def get_song_props(item):
    key = get_full_name(item, expand_artist_abbrs=True).lower()

    if key in PROPS:
        return PROPS[key]

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