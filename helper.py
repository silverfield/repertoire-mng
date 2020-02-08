import json

def create_json(m3u_path, json_path):
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

def create_repe(json_path):
    with open(json_path) as f:
        data = json.loads(f.read())

    m3u_lines = []
    for item in data:
        s = ''
        s += 'bts/' if item['type'] == 'bt' else 'full-songs/'
        s += item['name'].replace(' ', '%20')
        s += 'mp3'
        m3u_lines.append(s)

    with open('')

    
            
        

    print(data)

if __name__ == "__main__":
    # create_json('/d/music/repertoire/pl-main.m3u', './pl-main.json')
    create_repe('./pl-main.json')
