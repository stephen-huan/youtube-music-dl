import argparse, os, sys, subprocess, datetime
from requests_html import HTMLSession
from ytmusicapi import YTMusic
# import youtube_dl
import eyed3
import db

""" testing:
artist: https://music.youtube.com/channel/UChmAdYjOdnnrSA2kBMKdoYw
playlist: https://music.youtube.com/playlist?list=OLAK5uy_m9Ce3WCVVZXhHZNwdzaPQcY725pY9vIg0
browse: https://music.youtube.com/browse/MPREb_L3mB1OJ9weN
song: https://music.youtube.com/watch?v=_mapaZYhg7c&list=RDAMVM_mapaZYhg7c
"""

# bin hack
path = sys.argv[-1]
os.chdir(path)
sys.argv = sys.argv[:-1]

# setup youtube music
# YTMusic.setup(filepath="headers_auth.json")
# ytmusic = YTMusic("headers_auth.json")

ytmusic = YTMusic()
cache = db.load_db()

ARTIST, PLAYLIST, SONG = 0, 1, 2

def get_browse_id(url: str) -> str:
    """ Returns the browse id from a playlist url. """
    session = HTMLSession()
    r = session.get(url)
    t = r.html.html
    i = t.find("MPREb")
    l = t[i:].find("\\")
    return t[i: i + l]

def get_type(url: str) -> tuple:
    """ Parses a url and returns the id, along with the type. """
    if "channel" in url:
        return (ARTIST, url.split("/")[-1])
    if "playlist" in url:
        return (PLAYLIST, get_browse_id(url))
    if "browse" in url:
        return (PLAYLIST, url.split("/")[-1]) 
    if "watch" in url:
        return (SONG, url.split("v=")[-1].split("&")[0])
    raise Exception("Provided URL is an invalid Youtube music link.")

def download_song(sid: str, artist: str=None, album_artist: str=None, 
                  title: str="song", album_title: str="",
                  track: int=1, date: str=None, path: str="") -> None:
    """ Downloads a song. """
    if args.cache and sid in cache:
        print("Song is cached.")
        return 
    
    print(f"Downloading song {title}")
    subprocess.run(["youtube-dl", "--add-metadata",
                    "--extract-audio", "--audio-format", "mp3",
                    "--output", "%(id)s.%(ext)s", 
                    f"https://www.youtube.com/watch?v={sid}"])

    f = eyed3.load(f"{sid}.mp3")
    f.tag.artist = artist
    f.tag.album = album_title
    f.tag.album_artist = album_artist
    f.tag.title = title
    f.tag.track_num = track
    # yyyy-mm-dd format for date
    f.tag.release_date = date
    f.tag.save()

    os.rename(f"{sid}.mp3", f"{path}{track}_{title.replace('/', '-')}.mp3")

    cache.add(sid)
    db.save_db(cache)

def download_playlist(bid: str) -> None:
    """ Downloads a playlist. """
    if args.playlist_cache and bid in cache:
        print(f"Playlist {bid} is cached.")
        return

    album = ytmusic.get_album(bid)
    artists = ", ".join(a["name"] for a in album["artist"])
    title = album["title"]

    path = artists.replace("/", "-") 
    if not os.path.exists(path):
        os.mkdir(path)

    path += "/" + title.replace("/", "-")
    if not os.path.exists(path):
        os.mkdir(path)
    path += "/"

    rd = album["releaseDate"]
    date = f"{rd['year']}{rd['month']}{rd['day']}"

    print(f"Downloading playlist {title}")
    for song in album["tracks"]:
        download_song(song["videoId"], song["artists"], artists,
                      song["title"], title, int(song["index"]), date, path)

    cache.add(bid)
    db.save_db(cache)

def download_artist(aid: str) -> None:
    """ Downloads all the content of an artist. """
    info = ytmusic.get_artist(aid)
    albums = info["albums"]
    singles = info["singles"]
    for album in albums["results"]:
        download_playlist(album["browseId"])
    # singles are just playlists with one song in them
    for single in singles["results"]:
        download_playlist(single["browseId"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="youtube-music-dl")
    parser.add_argument("-v", "--version", action="version", version="1.0.0")
    parser.add_argument("-u", "--url", dest="url", type=str, required=True,
                        help="specifies the URL to download from")
    parser.add_argument("-f", "--force", dest="cache", 
                        action="store_false", default=True,
                        help="disable cache")
    parser.add_argument("-l", "--list", dest="playlist_cache", 
                        action="store_false", default=True,
                        help="disable playlist cache")
    args = parser.parse_args()
    content, ID = get_type(args.url)
    {ARTIST: download_artist, PLAYLIST: download_playlist, SONG: download_song}[content](ID)

