from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
import pickle
import os.path

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


def gdrive_query(service, name, is_folder=False, parent_id=None):
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

def create_or_update_file(service, fpath, name, parent_id, update=True):
    file_metadata = {
        'name': name
    }
    
    media = MediaFileUpload(fpath, resumable=True)
    files = gdrive_query(service, name, parent_id=parent_id)

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

def create_folder_if_not_exist(service, name, parent_id):
    l = gdrive_query(service, name, is_folder=True, parent_id=parent_id)
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