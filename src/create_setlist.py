from common import *
import gdrive_api as gapi
import json
import os
import editdistance
from PyPDF2 import PdfFileMerger
import shutil
import sys
from mutagen.mp3 import MP3

def create_repe(name, create_subsections=False, confirm_upload=True, upload=True):
    if name is None:
        items = []
        for p in PROPS.values():
            if 'used' in p and p['used'] == False:
                continue

            for v in p['versions']:
                version = ' - BT' if v == 'bt' else ''
                items.append(f"{p['name']}{version}")

        return create_repe_from_items(items, 'pl-ALL', confirm_upload=confirm_upload, upload=upload)

    json_path = f"{DATA_DIR}/busk-pls/{name}.json"

    with open(json_path) as f:
        data = json.loads(f.read())
    
    # go through the structure
    all_items = []
    for section_name, items in data.items():
        all_items.extend(items)
        if create_subsections:
            create_repe_from_items(
                items, 
                name=f'{name}-{section_name}', 
                confirm_upload=confirm_upload,
                parent=name,
                upload=upload
            )

    create_repe_from_items(all_items, name, confirm_upload=confirm_upload, upload=upload)

def create_repe_from_items(items, name, confirm_upload=True, parent=None, upload=True):
    new_items = []
    for item in items:
        item_props = get_song_props(item)
        if 'used' in item_props and item_props['used'] == False:
            print(f'Dropping {item} as it is marked unused')
            continue

        new_items.append(item)
    
    items = new_items

    subdir = f'/{parent}' if parent is not None else ''
    output_dir = f'{OUTPUT_DIR}{subdir}/{name}'
    mkdir(output_dir)

    print()
    print(f'Output dir is {output_dir}')

    print('\ncreating m3u...')
    mp3_props = create_m3u(items, output_dir, name)

    print('\ncreating PDF...')
    pdf_props = create_pdf(items, output_dir, name)

    final_json = {}
    for item in items:
        final_json[item] = {}
        final_json[item]['mp3'] = mp3_props[item]
        final_json[item]['pdf'] = pdf_props[item]
        final_json[item].update(get_song_props(item))

    print('\ncreating final JSON...')
    with open(f"{output_dir}/{name}.json", 'w') as f:
        f.write(json.dumps(final_json, indent=4))

    print('\nCopying locally to repertoire folder...')
    target_path = f"{REPE_FOLDER}{subdir}/{name}"
    if os.path.exists(target_path):
        shutil.rmtree(target_path)
    shutil.copytree(output_dir, target_path)

    if upload:
        if confirm_upload:
            print(confirm_upload)
            input('\nProceed with upload? Press any key to continue...')
        print('\n uploading to Drive...')
        upload_to_drive(output_dir, name, parent)

    print('\nOK')

def create_m3u(items, output_dir, name):
    m3u_lines = ['#EXTM3U\n']
    mp3_file_paths = []
    mp3_props = {}

    for item in items:
        s = ''
        s += 'bts/' if is_bt(item) else 'full-songs/'
        s += item
        s += '.mp3'

        fpath = f'{REPE_FOLDER}/{s}'
        if not os.path.exists(fpath):
            print(f'MP3 for {item} not found in {fpath}')
            mp3_props[item] = None
        else:
            mp3_file_paths.append(f'{fpath}\n')
            mp3_props[item] = fpath
            
            #remove ID3 tags
            mp3 = MP3(fpath)
            try:
                mp3.delete()
                mp3.save()
            except:
                pass

        s = s.replace(' ', '%20')
        
        name_info = item
        song_props = get_song_props(item)
        if song_props['loop'] is not None:
            name_info += f' - {song_props["loop"]}'

        m3u_lines.append(f'#EXTINF:1,{name_info}\n')
        m3u_lines.append(f'../{s}\n')

    with open(f'{output_dir}/{name}.m3u', 'w') as f:
        f.writelines(m3u_lines)

    return mp3_props

def create_pdf(items, output_dir, name):
    pdfs = get_pdf_paths(items)
    pdf_props = {item: pdf for item, pdf in zip(items, pdfs)}

    merger = PdfFileMerger()

    for pdf in pdfs:
        if pdf is None:
            continue
        merger.append(pdf)

    merger.write(f"{output_dir}/{name}.pdf")
    merger.close()

    return pdf_props

def _get_all_pdf_candidate_paths():
    all_paths = []

    for pdf_dir in PDF_DIRS:
        all_paths.extend([
            os.path.join(pdf_dir, f) 
            for f in os.listdir(pdf_dir) if f.endswith('.pdf')
        ])

    return all_paths

def _get_dist(item_name, pdf_name):
    if item_name == pdf_name:
        return -100

    if '-' in pdf_name:
        pdf_song_name = pdf_name.split('-')[1].strip()
        item_song_name = item_name.split('-')[1].strip()

        if pdf_song_name == item_song_name:
            if pdf_name.endswith(pdf_song_name):
                return -1
            return 0

        return editdistance.eval(pdf_song_name, item_song_name)

    return 100

def _get_best(item, all_pdf_candidate_paths):
    MAX_DIST = 999
    min_dist = MAX_DIST
    best_pdf = None

    for pdf_path in all_pdf_candidate_paths:
        pdf_name = pdf_path.split('/')[-1].split('.')[0].lower()
        item_name = get_full_name(item).lower().strip()

        dist = _get_dist(item_name, pdf_name)

        if dist < min_dist:
            min_dist = dist
            best_pdf = pdf_path

    if min_dist < MAX_DIST:
        return best_pdf

    return None

def get_pdf_paths(items):
    # get all pdf PATHS from which we'll choose the PDFs
    all_pdf_candidate_paths = _get_all_pdf_candidate_paths()

    pdfs = []

    for item in items:
        # if PDF is specified in song props, go with that
        item_props = get_song_props(item)
        if 'pdf' in item_props:
            if item_props['pdf'] == None:
                pdfs.append(None)
                continue
            pdfs.append(item_props['pdf'].replace('PREFIX', PREFIX))
            continue

        # let's find the most matching PDF
        pdfs.append(_get_best(item, all_pdf_candidate_paths))

    for z in zip([get_full_name(i) for i in items], [p for p in pdfs]):
        print(z)

    print(f'Found {len([p for p in pdfs if p is not None])} PDFs for {len(items)} items')

    return pdfs

def upload_to_drive(output_dir, name, parent=None):
    print('Getting Gdrive service...')
    service = gapi.get_gdrive_service()

    # find the ID of the repertoire folder
    print('Getting ID of the repertoire folder...')
    repe_folder = gapi.gdrive_query(service, 'repertoire', is_folder=True)[0]
    repe_folder_id = repe_folder['id']

    if parent:
        print(f'Checking if parent folder {parent} folder already exists...')
        parent_folder = gapi.create_folder_if_not_exist(service, parent, repe_folder_id)
        parent_folder_id = parent_folder['id']
    else:
        parent_folder_id = repe_folder_id

    # create a new folder there with the name of the setlist
    print(f'Checking if {name} folder already exists...')
    folder = gapi.create_folder_if_not_exist(service, name, parent_folder_id)

    # upload all the files to it
    for f in os.listdir(output_dir):
        if os.path.isdir(f'{output_dir}/{f}'):
            continue
        print(f'- uploading {f}...')
        gapi.create_or_update_file(service, f"{output_dir}/{f}", f, folder['id'])

    # upload all MP3 files
    print(f'\nUploading the MP3 files...')

    bt_folder_id = gapi.gdrive_query(service, 'bts', is_folder=True, parent_id=repe_folder_id)[0]['id']
    fs_folder_id = gapi.gdrive_query(service, 'full-songs', is_folder=True, parent_id=repe_folder_id)[0]['id']
    
    with open(f'{output_dir}/{name}.json') as f:
        data = json.loads(f.read())
        for item in data.values():
            if 'mp3' not in item or item['mp3'] is None:
                continue

            mp3_fpath = item['mp3'].strip()
            print(f'- uploading {mp3_fpath}...')
            mp3_parent_id = bt_folder_id if mp3_fpath.split('/')[-2] == 'bts' else fs_folder_id
            gapi.create_or_update_file(service, mp3_fpath, mp3_fpath.split('/')[-1], mp3_parent_id, update=False)


if __name__ == "__main__":
    # create_repe('pl-2020', create_subsections=True, confirm_upload=False, upload=True)
    create_repe(None, create_subsections=False, confirm_upload=False, upload=True)