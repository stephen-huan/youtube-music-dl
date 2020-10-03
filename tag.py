#!/usr/bin/env python3
"""
A light-weight command-line wrapper over a light-weight Python wrapper
of a C++ library (taglib).
Inspired by eyed3.
"""
import argparse, subprocess, sys
import taglib

PRINT = "pyprinttags3"

def call(l: list) -> str:
    """ Runs a shell program and returns its output. """
    return subprocess.run(l, capture_output=True, text=True).stdout

parser = argparse.ArgumentParser(description="command-line music metadata editor")
parser.add_argument("-v", "--version", action="version", version="tag v1.0")
parser.add_argument("paths", nargs="+")
parser.add_argument("-a", "--artist",
                    help="Set the artist name.")
parser.add_argument("-A", "--album",
                    help="Set the album name.")
parser.add_argument("-b", "--album-artist",
                    help="Set the album artist name. \
                    Takes priority over artist.")
parser.add_argument("-t", "--title",
                    help="Set the track title.")
parser.add_argument("-n", "--track",
                    help="Set the track number. Use 0 to clear.")
parser.add_argument("-N", "--track-total",
                    help="Set the total number of tracks. Use 0 to clear.")

args = parser.parse_args()

tags = {"ALBUM": args.album,
        "ALBUMARTIST": args.album_artist,
        "ARTIST": args.artist,
        "TITLE": args.title,
        "TRACKNUMBER": args.track,
       }

for path in args.paths:
    song = taglib.File(path)
    for tag, value in tags.items():
        if value is not None:
            song.tags[tag] = value
    song.save()

    # display information after possible changes
    print(call([PRINT, path]))

