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
        fields='*'
    ).execute()['files']

    return l

def create_or_update_file(service, fpath, name, parent_id, update=True):
    file_metadata = {
        'name': name
    }
    
    media = MediaFileUpload(fpath, resumable=True)
    files = gdrive_query(service, name, parent_id=parent_id)

    def _create():
        file_metadata['parents'] = [parent_id]

        service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

    if len(files) > 0:
        online_size = int(files[0]['size'])
        local_size = os.path.getsize(fpath)
        size_mismatch = online_size != local_size
        if size_mismatch:
            print(f'local size: {local_size} != {online_size}')

        if update or size_mismatch:
            print(f'  - updating {name} {"because sizes do not match" if size_mismatch else ""}...')

            service.files().delete(
                fileId=files[0]['id'],
            ).execute()

            _create()
        else:
            print(f'  - no action for {name} - present in drive and update set to False')
    else:
        print(f'  - creating {name}...')

        # file_metadata['parents'] = [parent_id]
        
        return _create()

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

if __name__ == "__main__":
    print('Getting Gdrive service...')
    service = get_gdrive_service()

    print('Getting ID of the repertoire folder...')
    test = gdrive_query(service, 'John Mayer - Stop This Train.mp3', is_folder=False)[0]

    import pprint
    pprint.pprint(test)

    print(os.path.getsize('G:\music\\repertoire\\songs\\John Mayer - Stop This Train.mp3'))
