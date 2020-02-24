from common import *
import gdrive_api as gapi
import json
import os
import editdistance
from PyPDF2 import PdfFileMerger
import shutil
import sys
from mutagen.mp3 import MP3

def create_repe(name, create_subsections=False, confirm_upload=True):
    json_path = f"{DATA_DIR}/{name}.json"

    with open(json_path) as f:
        data = json.loads(f.read())
    
    # flatten structure
    flat_data = []
    for item in data:
        if 'section' in item:
            flat_data.extend(item['items'])
            if create_subsections:
                create_repe_from_data(
                    item['items'], 
                    name=f'{name}-{item["section"]}', 
                    confirm_upload=confirm_upload
                )
        else:
            flat_data.append(item)

    create_repe_from_data(flat_data, name, confirm_upload=confirm_upload)

def create_repe_from_data(data, name, confirm_upload=True):
    output_dir = f'{OUTPUT_DIR}/{name}'
    mkdir(output_dir)

    print(f'Output dir is {output_dir}')

    print('\ncreating m3u...')
    data = create_m3u(data, output_dir, name)

    print('\ncreating PDF...')
    data = create_pdf(data, output_dir, name)

    print('\ncreating JSON...')
    with open(f"{output_dir}/{name}.json", 'w') as f:
        f.write(json.dumps(data, indent=4))

    print('\nCopying locally to repertoire folder...')
    target_path = f"{REPE_FOLDER}/{name}"
    if os.path.exists(target_path):
        shutil.rmtree(target_path)
    shutil.copytree(output_dir, target_path)

    if confirm_upload:
        print(confirm_upload)
        input('\nProceed with upload? Press any key to continue...')
    print('\n uploading to Drive...')
    upload_to_drive(output_dir, name)

    print('\nOK')

def create_m3u(data, output_dir, name):
    m3u_lines = ['#EXTM3U\n']
    mp3_file_paths = []

    with open('./loop-pos.json', 'r') as f:
        loop_pos = json.loads(f.read())
        loop_pos = {key.lower(): value for key, value in loop_pos.items()}

    for item in data:
        s = ''
        s += 'bts/' if item['type'] == TYPE_BT else 'full-songs/'
        s += item['name']
        s += '.mp3'

        fpath = f'{REPE_FOLDER}/{s}'
        if not os.path.exists(fpath):
            print(f'MP3 for {item["name"]} not found in {fpath}')
            item['mp3'] = None
        else:
            mp3_file_paths.append(f'{fpath}\n')
            item['mp3'] = fpath
            
            mp3 = MP3(fpath)
            try:
                mp3.delete()
                mp3.save()
            except:
                pass


        s = s.replace(' ', '%20')
        
        name_info = item["name"]
        if item['name'].lower() in loop_pos:
            name_info += f' - {loop_pos[item["name"].lower()]}'

        m3u_lines.append(f'#EXTINF:1,{name_info}\n')
        m3u_lines.append(f'../{s}\n')

    with open(f'{output_dir}/{name}.m3u', 'w') as f:
        f.writelines(m3u_lines)

    return data

def create_pdf(data, output_dir, name):
    pdfs = get_pdf_paths(data)
    for d, pdf in zip(data, pdfs):
        d.update({'pdf': pdf})

    merger = PdfFileMerger()

    for pdf in pdfs:
        if pdf is None:
            continue
        merger.append(pdf)

    merger.write(f"{output_dir}/{name}.pdf")
    merger.close()

    return data

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
        elif item['name'] in SPEC_PDF_SONGS:
            pdfs.append(SPEC_PDF_SONGS[item['name']])
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

def upload_to_drive(output_dir, name):
    print('Getting Gdrive service...')
    service = gapi.get_gdrive_service()

    # find the ID of the repertoire folder
    print('Getting ID of the repertoire folder...')
    repe_folder = gapi.gdrive_query(service, 'repertoire', is_folder=True)[0]
    repe_folder_id = repe_folder['id']

    # create a new folder there with the name of the setlist
    print(f'Checking if {name} folder already exists...')
    folder = gapi.create_folder_if_not_exist(service, name, repe_folder_id)

    # upload all the files to it
    for f in os.listdir(output_dir):
        print(f'- uploading {f}...')
        gapi.create_or_update_file(service, f"{output_dir}/{f}", f, folder['id'])

    # upload all MP3 files
    print(f'\nUploading the MP3 files...')

    bt_folder_id = gapi.gdrive_query(service, 'bts', is_folder=True, parent_id=repe_folder_id)[0]['id']
    fs_folder_id = gapi.gdrive_query(service, 'full-songs', is_folder=True, parent_id=repe_folder_id)[0]['id']
    
    with open(f'{output_dir}/{name}.json') as f:
        data = json.loads(f.read())
        for item in data:
            if 'mp3' not in item or item['mp3'] is None:
                continue

            mp3_fpath = item['mp3'].strip()
            print(f'- uploading {mp3_fpath}...')
            parent_id = bt_folder_id if mp3_fpath.split('/')[-2] == 'bts' else fs_folder_id
            gapi.create_or_update_file(service, mp3_fpath, mp3_fpath.split('/')[-1], parent_id, update=False)


if __name__ == "__main__":
    create_repe('pl-2020', create_subsections=False, confirm_upload=False)