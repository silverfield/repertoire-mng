### Setup

Need to get credentials.json for Google drive in 

console.developers.google.com
- project setlist
- login as Fero Musician

### Updating busking setlist

To update busking setlist:

- add the song to song-props if not there
    - modify props like loop position, versions...
- add it to the busking playlist: <artist> - <name> - <version>
- run `create_setlist.py` on the playlist

This will:

- create a m3u file with backing tracks or originals with loop positions marked
- create a common PDF with all chords/lyrics
- create a json file that has all the info (mp3 file paths, PDFs...)
- upload everything to Google drive
- copy to the local repe folder on my machine
- do this for subsections of the playlist too

### Updating website repertoire

To update a repertoire for the website:

- add the song to song-props if not there
- update the `pl-web...` jsons
- run `create_web_repe.py`