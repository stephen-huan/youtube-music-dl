# youtube-music-dl

Uses the [ytmusicapi](https://github.com/sigma67/ytmusicapi) and 
[youtube-dl](https://github.com/ytdl-org/youtube-dl) to scrap and download
music. 

### Setup

`pipenv install` to install the dependencies.

### Running

`pipenv run python youtube-music-dl.py -u URL`

The type of media (songs, playlists, or artist) is automatically recognized
from the URL. Also, a `db.json` file is used as a cache. Pass `-f` to ignore
the cache.
