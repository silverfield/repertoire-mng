import json
import os
import editdistance
from PyPDF2 import PdfFileMerger
import shutil
import sys

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

JSON_DIR = './jsons'
OUTPUT_DIR = './output'

TYPE_BT = 'bt'
TYPE_NBT = 'nbt'

PREFIX = '/d'
if not os.path.exists(PREFIX):
    PREFIX = 'G:'
PDF_DIRS = [f'{PREFIX}/music/akordy/chords', f'{PREFIX}/music/akordy/fero-hajnovic']
REPE_FOLDER = f'{PREFIX}/music/repertoire'

SPEC_PDF_SONGS = {
    'FH - Summer tune - BT': None,
    'MK - Going home 96 - BT': f'{PREFIX}/music/akordy/chords/Mark Knopfler - Local hero.pdf',
    'Ray Charles - Hit The Road Jack (remastered)': None,
    'Tommy Emmanuel - Those Who Wait': f'{PREFIX}/music/noty/tommy emmanuel：those who wait.pdf',
}

def mkdir(d):
    if not os.path.exists(d):
        os.mkdir(d)
mkdir(JSON_DIR)
mkdir(OUTPUT_DIR)

def create_json_from_m3u(m3u_path):
    with open(m3u_path) as f:
        lines = f.readlines()

    lines = [l for l in lines if not l.startswith('#')]
    lines = [l.split('.')[0] for l in lines]
    lines = [l.replace('%20', ' ') for l in lines]
    
    j = [
        {
            'name': line.split('/')[1],
            'type': TYPE_BT if line.split('/')[0] == 'bts' else TYPE_NBT
        } for line in lines
    ]
    for i in range(len(j)):
        if j[i]['name'] in SPEC_PDF_SONGS:
            j[i]['pdf'] = SPEC_PDF_SONGS[j[i]['name']]

    s = json.dumps(j)
    name = m3u_path.split("/")[-1].split('.')[0]
    with open(f'{JSON_DIR}/{name}.json', 'w') as f:
        f.write(s)

def create_all():
    bts_files = [f for f in os.listdir(f'{REPE_FOLDER}/bts') if f.endswith('.mp3')]
    full_song_files = [f for f in os.listdir(f'{REPE_FOLDER}/full-songs') if f.endswith('.mp3')]
    
    j = [
        {
            'name': f.split('.')[0],
            'type': TYPE_BT
        } for f in sorted(bts_files)
    ] + [
        {
            'name': f.split('.')[0],
            'type': TYPE_NBT
        } for f in sorted(full_song_files)
    ]
    for i in range(len(j)):
        if j[i]['name'] in SPEC_PDF_SONGS:
            j[i]['pdf'] = SPEC_PDF_SONGS[j[i]['name']]

    s = json.dumps(j)
    with open(f'{JSON_DIR}/pl-all.json', 'w') as f:
        f.write(s)

def create_repe(json_path, name=None):
    if name is None:
        name = json_path.split('/')[-1].split('.')[0]

    output_dir = f'{OUTPUT_DIR}/{name}'
    mkdir(output_dir)

    print(f'Output dir is {output_dir}')

    with open(json_path) as f:
        data = json.loads(f.read())

    print('\ncreating m3u...')
    create_m3u(data, output_dir, name)

    print('\ncreating PDF...')
    create_pdf(data, output_dir, name)

    print('\ncopying JSON...')
    shutil.copy(json_path, f"{output_dir}/{name}.json")

    input('Proceed with upload? Press any key to continue...')
    print('\n uploading to Drive...')
    upload_to_drive(output_dir, name)

    print('\nOK')

def create_m3u(data, output_dir, name):
    m3u_lines = []
    mp3_file_paths = []

    for item in data:
        s = ''
        s += 'bts/' if item['type'] == TYPE_BT else 'full-songs/'
        s += item['name']
        s += '.mp3'

        fpath = f'{REPE_FOLDER}/{s}'
        if not os.path.exists(fpath):
            print(f'MP3 for {item["name"]} not found in {fpath}')
        else:
            mp3_file_paths.append(f'{fpath}\n')

        s = s.replace(' ', '%20')
        m3u_lines.append(f'../{s}\n')

    with open(f'{output_dir}/{name}.m3u', 'w') as f:
        f.writelines(m3u_lines)

    with open(f'{output_dir}/{name}_mp3_paths.txt', 'w') as f:
        f.writelines(mp3_file_paths)

def create_pdf(data, output_dir, name):
    pdfs = get_pdf_paths(data)

    merger = PdfFileMerger()

    for pdf in pdfs:
        if pdf is None:
            continue
        merger.append(pdf)

    merger.write(f"{output_dir}/{name}.pdf")
    merger.close()

def get_pdf_paths(data):
    all_pdfs = []
    for pdf_dir in PDF_DIRS:
        all_pdfs.extend([
            os.path.join(pdf_dir, f) 
            for f in os.listdir(pdf_dir) if f.endswith('.pdf')
        ])

    pdfs = []
    for item in data:
        if 'pdf' in item:
            pdfs.append(item['pdf'])
            continue

        MAX_DIST = 999
        min_dist = MAX_DIST
        best_pdf = None

        for pdf in all_pdfs:
            pdf_name = pdf.split('/')[-1].split('.')[0].lower()
            if '-' in pdf_name:
                pdf_name = pdf_name.split('-')[1].strip()
            item_name = item['name'].lower().split('-')[1].strip()

            dist = editdistance.eval(pdf_name, item_name)

            if dist < min_dist:
                min_dist = dist
                best_pdf = pdf

        if min_dist < MAX_DIST:
            pdfs.append(best_pdf)
        else:
            pdfs.append(None)

    for z in zip([i['name'] for i in data], [p for p in pdfs]):
        print(z)

    print(f'Found {len([p for p in pdfs if p is not None])} PDFs for {len(data)} items')

    return pdfs

def get_gdrive_service():
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/drive']

    creds = None

    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)

    return service


def _gdrive_query(service, name, is_folder=False, parent_id=None):
    q = f'name="{name}" and trashed = false'
    if is_folder:
        q += ' and mimeType="application/vnd.google-apps.folder"'

    if parent_id:
        q += f" and '{parent_id}' in parents"

    l = service.files().list(
        q=q,
        spaces='drive',
    ).execute()['files']

    return l

def _create_or_update_file(service, fpath, name, parent_id, update=True):
    file_metadata = {
        'name': name
    }
    
    media = MediaFileUpload(fpath, resumable=True)
    files = _gdrive_query(service, name, parent_id=parent_id)

    if len(files) > 0:
        if update:
            print(f'  - updating {name}...')
            
            return service.files().update(
                fileId=files[0]['id'],
                body=file_metadata,
                media_body=media,
                fields='id',
            ).execute()
        else:
            print(f'  - no action for {name} - present in drive and update set to False')
    else:
        print(f'  - creating {name}...')

        file_metadata['parents'] = [parent_id]
        
        return service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

def _create_folder_if_not_exist(service, name, parent_id):
    l = _gdrive_query(service, name, is_folder=True, parent_id=parent_id)
    if len(l) == 0:
        print(f'Creating a new folder called {name}...')
        folder_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=folder_metadata).execute()
    else:
        print(f'Folder {name} found...')
        folder = l[0]

    return folder


def upload_to_drive(output_dir, name):
    print('Getting Gdrive service...')
    service = get_gdrive_service()

    # find the ID of the repertoire folder
    print('Getting ID of the repertoire folder...')
    repe_folder = _gdrive_query(service, 'repertoire', is_folder=True)[0]
    repe_folder_id = repe_folder['id']

    # create a new folder there with the name of the setlist
    print(f'Checking if {name} folder already exists...')
    folder = _create_folder_if_not_exist(service, name, repe_folder_id)

    # upload all the files to it
    for f in os.listdir(output_dir):
        print(f'- uploading {f}...')
        _create_or_update_file(service, f"{output_dir}/{f}", f, folder['id'])

    # upload all MP3 files
    print(f'\nUploading the MP3 files...')

    bt_folder_id = _gdrive_query(service, 'bts', is_folder=True, parent_id=repe_folder_id)[0]['id']
    fs_folder_id = _gdrive_query(service, 'full-songs', is_folder=True, parent_id=repe_folder_id)[0]['id']
    
    with open(f'{output_dir}/{name}_mp3_paths.txt') as f:
        for mp3_fpath in f.readlines():
            mp3_fpath = mp3_fpath.strip()
            print(f'- uploading {mp3_fpath}...')
            parent_id = bt_folder_id if mp3_fpath.split('/')[-2] == 'bts' else fs_folder_id
            _create_or_update_file(service, mp3_fpath, mp3_fpath.split('/')[-1], parent_id, update=False)

        
def main(name='pl-main'):
    if len(sys.argv) > 1:
        name = sys.argv[1]
    
    create_repe(f'{JSON_DIR}/{name}.json')

if __name__ == "__main__":
    main('pl-all')
    # create_json_from_m3u('/d/music/repertoire/pl-main.m3u')
    # create_all()