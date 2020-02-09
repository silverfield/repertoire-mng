import json
import os
import editdistance
from PyPDF2 import PdfFileMerger
import shutil

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

JSON_DIR = './jsons'
OUTPUT_DIR = './output'

PDF_DIRS = ['/d/music/akordy/chords', '/d/music/akordy/fero-hajnovic']

def mkdir(d):
    if not os.path.exists(d):
        os.mkdir(d)
mkdir(JSON_DIR)
mkdir(OUTPUT_DIR)

def create_json_from_m3u(m3u_path, json_path):
    with open(m3u_path) as f:
        lines = f.readlines()

    lines = [l for l in lines if not l.startswith('#')]
    lines = [l.split('.')[0] for l in lines]
    lines = [l.replace('%20', ' ') for l in lines]
    
    j = [
        {
            'name': line.split('/')[1],
            'type': 'bt' if line.split('/')[0] == 'bts' else 'loop'
        } for line in lines
    ]

    s = json.dumps(j)
    with open(json_path, 'w') as f:
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

    print('\ncreating uploading to Drive...')
    upload_to_drive(output_dir, name)

    print('\nOK')

def create_m3u(data, output_dir, name):
    m3u_lines = []
    for item in data:
        s = '../'
        s += 'bts/' if item['type'] == 'bt' else 'full-songs/'
        s += item['name'].replace(' ', '%20')
        s += 'mp3\n'
        m3u_lines.append(s)

    with open(f'{output_dir}/{name}.m3u', 'w') as f:
        f.writelines(m3u_lines)

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

    # for z in zip([i['name'] for i in data], [p for p in pdfs]):
    #     print(z)

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


def upload_to_drive(output_dir, name):
    print('Getting Gdrive service...')
    service = get_gdrive_service()

    # find the ID of the repertoire folder
    print('Getting ID of the repertoire folder...')
    repe_folder = service.files().list(
        q='mimeType="application/vnd.google-apps.folder" and name="repertoire"',
        spaces='drive',
    ).execute()['files'][0]
    repe_folder_id = repe_folder['id']

    # create a new folder there with the name of the setlist
    print(f'Creating a new folder called {name}...')
    folder_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [repe_folder_id]
    }
    folder = service.files().create(body=folder_metadata).execute()

    # upload all the files to it
    for f in os.listdir(output_dir):
        print(f'- uploading {f}...')
        file_metadata = {
            'name': f,
            'parents': [folder['id']]
        }
        
        media = MediaFileUpload(f"{output_dir}/{f}", resumable=True)
        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()


if __name__ == "__main__":
    create_repe(f'{JSON_DIR}/pl-main.json')

