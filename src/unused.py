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


if __name__ == "__main__":
    create_pl_all()