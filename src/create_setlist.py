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
        if type(item) == type({}) and 'section' in item:
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
    mp3_props = create_m3u(data, output_dir, name)

    print('\ncreating PDF...')
    pdf_props = create_pdf(data, output_dir, name)

    final_json = {}
    for item in data:
        final_json[item] = {}
        final_json[item]['mp3'] = mp3_props[item]
        final_json[item]['pdf'] = pdf_props[item]
        final_json[item].update(get_song_props(item))

    print('\ncreating final JSON...')
    with open(f"{output_dir}/{name}.json", 'w') as f:
        f.write(json.dumps(final_json, indent=4))

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

    with open(f'{DATA_DIR}/loop-pos.json', 'r') as f:
        loop_pos = json.loads(f.read())
        loop_pos = {key.lower(): value for key, value in loop_pos.items()}

    mp3_props = {}

    for item in data:
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
        if item.lower() in loop_pos:
            name_info += f' - {loop_pos[item.lower()]}'

        m3u_lines.append(f'#EXTINF:1,{name_info}\n')
        m3u_lines.append(f'../{s}\n')

    with open(f'{output_dir}/{name}.m3u', 'w') as f:
        f.writelines(m3u_lines)

    return mp3_props

def create_pdf(data, output_dir, name):
    pdfs = get_pdf_paths(data)
    pdf_props = {item: pdf for item, pdf in zip(data, pdfs)}

    merger = PdfFileMerger()

    for pdf in pdfs:
        if pdf is None:
            continue
        merger.append(pdf)

    merger.write(f"{output_dir}/{name}.pdf")
    merger.close()

    return pdf_props

def get_pdf_paths(data):
    all_pdfs = []
    for pdf_dir in PDF_DIRS:
        all_pdfs.extend([
            os.path.join(pdf_dir, f) 
            for f in os.listdir(pdf_dir) if f.endswith('.pdf')
        ])

    pdfs = []

    for item in data:
        item_props = get_song_props(item)
        if 'pdf' in item_props:
            if item_props['pdf'] == None:
                pdfs.append(None)
                continue
            pdfs.append(item_props['pdf'].replace('PREFIX', PREFIX))
            continue

        MAX_DIST = 999
        min_dist = MAX_DIST
        best_pdf = None

        for pdf in all_pdfs:
            pdf_name = pdf.split('/')[-1].split('.')[0].lower()
            if '-' in pdf_name:
                pdf_name = pdf_name.split('-')[1].strip()
            item_name = get_full_name(item).lower().split('-')[1].strip()

            dist = editdistance.eval(pdf_name, item_name)

            if dist < min_dist:
                min_dist = dist
                best_pdf = pdf

        if min_dist < MAX_DIST:
            pdfs.append(best_pdf)
        else:
            pdfs.append(None)

    for z in zip([get_full_name(i) for i in data], [p for p in pdfs]):
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
    # create_repe('pl-2020', create_subsections=False, confirm_upload=False)
    create_repe('pl-all', create_subsections=False, confirm_upload=False)