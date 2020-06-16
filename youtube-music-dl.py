import argparse, os, sys, subprocess, datetime
import requests
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
    i = t.find("browseId") + 13
    l = t[i:].find("\\")
    bid = t[i: i + l]
    # re-search if found browse id is not valid
    while bid == "SPunlimited":
        t = t[i + l:]
        i = t.find("browseId") + 13
        l = t[i:].find("\\")
        bid = t[i: i + l] 

    return bid

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

def parse_artists(artists: list) -> str:
    """ Parses artists from a video. """
    if isinstance(artists, str):
        return artists

    return ", ".join(artist["name"] for artist in artists)

def download_song(sid: str, artist: str=None, album_artist: str=None, 
                  title: str="song", album_title: str="",
                  track: int=1, date: str=None, 
                  path: str="", pid: str="", thumbnail_url: str=None) -> None:
    """ Downloads a song. """
    if args.cache and f"{pid}|{sid}" in cache:
        print("Song is cached.")
        return 

    if sid is None:
        print("Cannot download song.")
        return

    print(f"Downloading song {title} with id {sid}")
    path = f"{path}{track}_{title.replace('/', '-')}.mp3" 
    if not args.dry:
        subprocess.run(["youtube-dl", "--add-metadata",
                        "--extract-audio", "--audio-format", "mp3",
                        "--output", "%(id)s.%(ext)s", 
                        f"https://www.youtube.com/watch?v={sid}"])
        os.rename(f"{sid}.mp3", path)

    if not args.dry or args.write_tag:
        f = eyed3.load(path)
        f.tag.artist = artist
        f.tag.album = album_title
        f.tag.album_artist = album_artist
        f.tag.title = title
        f.tag.track_num = track
        # yyyy-mm-dd format for date
        f.tag.release_date = date
        # image types documented here: https://eyed3.readthedocs.io/en/latest/eyed3.id3.html#eyed3.id3.frames.ImageFrame
        r = requests.get(thumbnail_url)
        imagedata = r.content
        f.tag.images.set(1, imagedata, "image/jpeg", "icon image", None)
        f.tag.save()

    cache.add(f"{pid}|{sid}")
    db.save_db(cache)

def download_playlist(bid: str, artist: str=None) -> None:
    """ Downloads a playlist. """
    if args.playlist_cache and bid in cache:
        print(f"Playlist {bid} is cached.")
        return

    try:
        album = ytmusic.get_album(bid)
        rd = album["releaseDate"]
        date = f"{rd['year']}-{rd['month']}-{rd['day']}"
    # assumes playlist is album, this is for an actual playlist
    except KeyError:
        album = ytmusic.get_playlist(bid)
        artist = album["author"]
        # date is arbitrary because precise playlist creation dates are unknown 
        date = f"{album['year']}-07-10"

    artists = ", ".join(a["name"] for a in album["artist"]) \
              if artist is None else artist
    title = album["title"]

    path = artists.replace("/", "-")
    
    if len(path) > 0:
        if not os.path.exists(path):
            os.mkdir(path)
        path += "/"

    path += title.replace("/", "-")
    if not os.path.exists(path):
        os.mkdir(path)
    path += "/"

    print(f"Downloading playlist {title} with id {bid}")
    for i, song in enumerate(album["tracks"]):
        # last element in thumbnails is highest resolution
        download_song(song["videoId"], parse_artists(song["artists"]), artists,
                      song["title"], title, int(song.get("index", i + 1)), date, 
                      path, bid, song["thumbnails"][-1]["url"])
    cache.add(bid)
    db.save_db(cache)

def download_artist(aid: str) -> None:
    """ Downloads all the content of an artist. """
    info = ytmusic.get_artist(aid)
    albums = info["albums"]
    singles = info["singles"]
    artist = info["name"] if args.overwrite else None
    for album in albums["results"]:
        download_playlist(album["browseId"], artist)
    # singles are just playlists with one song in them
    for single in singles["results"]:
        download_playlist(single["browseId"], artist)

def download_url(url: str) -> None:
    """ Downloads the url. """
    content, ID = get_type(url)
    {ARTIST: download_artist, PLAYLIST: download_playlist, SONG: download_song}[content](ID)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="youtube-music-dl")
    parser.add_argument("-v", "--version", action="version", version="1.0.0")
    parser.add_argument("-u", "--url", dest="url", type=str,
                        help="specifies the URL to download from")
    parser.add_argument("-f", "--force", dest="cache", 
                        action="store_false", default=True,
                        help="disable song cache")
    parser.add_argument("-l", "--list", dest="playlist_cache", 
                        action="store_false", default=True,
                        help="disable playlist cache")
    parser.add_argument("-o", "--overwrite", dest="overwrite", 
                        action="store_false", default=True,
                        help="don't overwrite the 'album_artist' tag")
    parser.add_argument("-s", "--simulate", dest="dry", 
                        action="store_true", default=False,
                        help="don't actually download music")
    parser.add_argument("-t", "--tag", dest="write_tag",
                        action="store_true", default=False,
                        help="force update id3 tags even if running under --simulate")
    parser.add_argument("-i", "--input", dest="file", 
                        help="read URLs from a file")
    args = parser.parse_args()

    if args.file is not None:
        if os.path.exists(args.file):
            with open(args.file) as f:
                for line in f:
                    url = line.split("#")[0].strip()
                    if len(url) > 0:
                        print(f"Processing URL {url}")
                        download_url(url)
        else:
            print("Input file is not a valid path!")

    elif args.url is not None:
        download_url(args.url)
    else:
        print("Nothing to do!")

