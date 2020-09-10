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
    if name is None:  # we create one for all songs in song-props
        items = []
        for p in PROPS.values():
            version = ' - BT' if 'bt' in p['versions'] else ''  # by default, better to have BT in the setlist
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

    # create one for all items
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
    mp3_props = create_m3u(items, output_dir, name, has_parent=parent is not None)

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

def create_m3u(items, output_dir, name, has_parent):
    m3u_lines = ['#EXTM3U\n']
    mp3_props = {}

    bts_files = [f for f in os.listdir(f'{REPE_FOLDER}/bts') if f.endswith('.mp3')]

    for item in items:
        if is_bt(item):
            best_bts = _get_best(item, bts_files)
            if len(best_bts) == 0:
                print(f'BT MP3 for {item} not found')
                mp3_props[item] = []
            else:
                mp3_props[item] = [f'bts/{bt}' for bt in best_bts]                
        else:
            mp3_props[item] = []

        def _add_m3u(name_info, path):
            song_props = get_song_props(item)
            if song_props['loop'] is not None:
                name_info += f' - {song_props["loop"]}'

            m3u_lines.append(f'#EXTINF:1,{name_info}\n')
            m3u_lines.append(f'{path}\n')

        for fpath in mp3_props[item]:
            #remove ID3 tags
            mp3 = MP3(f'{REPE_FOLDER}/{fpath}')
            try:
                mp3.delete()
                mp3.save()
            except:
                pass

            fpath = f'../{fpath}'
            if has_parent:
                fpath = f'../{fpath}'
            name_info = os.path.basename(fpath)
            fpath = fpath.replace(' ', '%20')
            _add_m3u(name_info, fpath)
        
        if len(mp3_props[item]) == 0:
            _add_m3u(item, f'{item}.mp3')

    with open(f'{output_dir}/{name}.m3u', 'w') as f:
        f.writelines(m3u_lines)

    return mp3_props

def create_pdf(items, output_dir, name):
    pdfs = get_pdf_paths(items)
    pdf_props = {item: pdf for item, pdf in zip(items, pdfs)}

    merger = PdfFileMerger()

    flat_pdfs = [pdf for song_pdfs in pdfs for pdf in song_pdfs]

    for pdf in flat_pdfs:
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

def _get_dist(item_name, file_name):
    if item_name == file_name or file_name.startswith(item_name):
        return -100

    if '-' in file_name:
        file_song_name = file_name.split('-')[1].strip()
        item_song_name = item_name.split('-')[1].strip()

        if file_song_name == item_song_name:
            if file_name.endswith(file_song_name):
                return -1
            return 0

        return editdistance.eval(file_song_name, item_song_name)

    return 100

def _get_best(item, all_paths):
    MAX_DIST = 999
    min_dist = MAX_DIST
    best_paths = []

    artist_name = get_artist(item).lower().strip()
    artist_name_exp = get_artist(item, expand_abbrs=True).lower().strip()
    song_name = get_name(item).lower().strip()

    to_compare = [f'{artist_name} - {song_name}']
    if artist_name_exp != artist_name:
        to_compare += [f'{artist_name_exp} - {song_name}']

    for path in all_paths:
        file_name = os.path.basename(path).lower()

        for item_name in to_compare:
            dist = _get_dist(item_name, file_name.split('.')[0])

            if dist < min_dist:
                min_dist = dist
                best_paths = [path]
            elif dist == min_dist:
                best_paths.append(path)

    return list(set(best_paths))

def get_pdf_paths(items):
    # get all pdf PATHS from which we'll choose the PDFs
    all_pdf_candidate_paths = _get_all_pdf_candidate_paths()

    pdfs = []

    for item in items:
        # if PDF is specified in song props, go with that
        item_props = get_song_props(item)
        if 'pdf' in item_props:
            if item_props['pdf'] == None:
                pdfs.append([])
                continue
            pdfs.append([item_props['pdf'].replace('PREFIX', PREFIX)])
            continue

        # let's find the most matching PDF
        pdfs.append(_get_best(item, all_pdf_candidate_paths))

    for z in zip([get_full_name(i) for i in items], [p for p in pdfs]):
        print(z)

    print(f'Found PDFs for {len([p for p in pdfs if p is not None])} items out of {len(items)}')

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

    if parent is not None:
        return

    # upload all MP3 files
    print(f'\nUploading the MP3 files...')

    bt_folder_id = gapi.gdrive_query(service, 'bts', is_folder=True, parent_id=repe_folder_id)[0]['id']
    fs_folder_id = gapi.gdrive_query(service, 'full-songs', is_folder=True, parent_id=repe_folder_id)[0]['id']
    
    with open(f'{output_dir}/{name}.json') as f:
        data = json.loads(f.read())
        for item in data.values():
            if 'mp3' not in item:
                continue

            for mp3_fpath in item['mp3']:
                mp3_fpath = f'{REPE_FOLDER}/{mp3_fpath.strip()}'
                print(f'- uploading {mp3_fpath}...')
                mp3_parent_id = bt_folder_id if mp3_fpath.split('/')[-2] == 'bts' else fs_folder_id
                gapi.create_or_update_file(service, mp3_fpath, mp3_fpath.split('/')[-1], mp3_parent_id, update=False)


if __name__ == "__main__":
    upload = True
    create_repe('pl-2020', create_subsections=True, confirm_upload=False, upload=upload)
    create_repe(None, create_subsections=False, confirm_upload=False, upload=upload)