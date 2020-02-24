DATA_DIR = './data'
OUTPUT_DIR = './output'

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