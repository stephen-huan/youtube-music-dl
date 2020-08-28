import argparse, os, subprocess
import eyed3
from audio2numpy import open_audio
from scipy.io.wavfile import read, write
import numpy as np

def save_mp3(fname: str, data: np.array, rate: int) -> None:
    """ Saves data into the mp3 format. """
    write(fname + ".wav", rate, data)
    # fix from here: https://superuser.com/questions/892996/ffmpeg-is-doubling-audio-length-when-extracting-from-video#comment1795058_893044
    subprocess.call(["ffmpeg", "-i", fname + ".wav", "-write_xing", "0", "-y", fname + ".mp3"])
    os.remove(fname + ".wav")

try:
    from audio_parser import parse_file
except ModuleNotFoundError:
    print("File-specific parser not found, using default parser")
    def parse_file(args: argparse.ArgumentParser, sr: int) -> list:
        """ Parses the input file for timestamps """
        with open(args.file) as f:
            lines = []
            for line in f:
                line = line.split(args.delim)
                # see if hour is defined
                try:
                    int(line[2])
                except ValueError:
                    line = [0] + line
                h, m, s = int(line[0]), int(line[1]), int(line[2])
                t = (3600*h + 60*m + s)*sr
                title = args.delim.join(line[3:]).strip()
                tokens = title.split("-")
                title, artist = ("-".join(tokens[:-1]), tokens[-1].strip()) if len(tokens) > 1 else (title, None)
                lines.append((t, title.strip().replace("/", "-"), artist))
        return lines

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ostlyser")
    parser.add_argument("-v", "--version", action="version", version="1.0.0")
    parser.add_argument("-a", "--audio", dest="audio", required=True,
                        help="audio file to break up")
    parser.add_argument("-i", "--input", dest="file", required=True,
                        help="read timing information from a file")
    parser.add_argument("-d", "--delimiter", dest="delim", default=":",
                        help="delimiter to split input file on")
    args = parser.parse_args()

    data, sr = open_audio(args.audio)
    file = eyed3.load(args.audio)
    lines = parse_file(args, sr)

    for i, (start, name, artist) in enumerate(lines):
        # get slice of the original file that this song represents
        song = data[start: lines[i + 1][0] if i != len(lines) - 1 else len(data)]
        path = f"{i + 1}_{name}"
        save_mp3(path, song, sr)

        f = eyed3.load(path + ".mp3")
        # copy the tags of the original file
        f.tag = file.tag
        f.tag.title = name
        f.tag.artist = artist
        f.tag.track_num = i + 1
        f.tag.save()

