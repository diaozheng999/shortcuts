"""
Merges an iPhone Live Photo (HEIF photo and QuickTime movie parts) into a
single Motion Photo file (HEIF format) that can be understood as Motion Photo
in Google Photos.

Requires the following to be installed and inside PATH:
1. exiftool
2. adb

Requires the following python packages
1. opencv_python
2. tqdm

This file is meant to be run with command line access to the iPhone storage
in either Windows or Linux. For Mac, you can sync up the photos with Photos.app
and use `photo_sync.py` to copy the photos that way.

Usage:

python3 ./motion_photo.py /path/to/photos

"""

import os
import sys
import shutil
import subprocess
from tqdm import tqdm
from heif.HeifFile import HeifFile
from xmp.xmlutil import parse

from qt.QuickTimeFile import QuickTimeFile

USE_MICRO_VIDEO_FOR_JPEG = True
ENCODE_AS_MP4 = True
FIX_PRESENTATION_OFFSET = True


def get_file_with_movie(name, d, wd):
    (names, ext) = name.rsplit(".", 1)
    img_file = d + names + '.' + ext
    mov_file = d + names + '.mov'
    mp_file = wd + names + '.' + ext

    mp4_file = (wd + names + ".mp4") if ENCODE_AS_MP4 else mov_file

    jpeg = ext.lower() != 'heic'

    if jpeg and not USE_MICRO_VIDEO_FOR_JPEG:
        mp_file = wd + names + '.MP.' + ext

    xmp_file = wd + names + '.xmp'

    return img_file, mov_file, mp_file, xmp_file, jpeg, mp4_file


def get_quicktime_duration_us(movie_file):
    """
    Get the duration of a QuickTime movie file in microseconds
    """
    with QuickTimeFile(movie_file) as f:
        return f.moov.mvhd.duration_in_us()


def reencode_motion(movie_file, mp4_file):
    # ffmpeg -vcodec copy -acodec copy
    subprocess.run(["ffmpeg", "-i", movie_file, "-c:v",
                   "libx265", "-c:a", "aac", mp4_file])

def get_presentation_offset_for_duration(duration):
    return "-1" if FIX_PRESENTATION_OFFSET else duration

def get_xmp_metadata_for_microvideo(duration, file_size):
    data = """
    <x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.1.0-jc003">
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about=""
            xmlns:GCamera="http://ns.google.com/photos/1.0/camera/"
            xmlns:Container="http://ns.google.com/photos/1.0/container/"
            xmlns:Item="http://ns.google.com/photos/1.0/container/item/"
            GCamera:MicroVideo="1"
            GCamera:MicroVideoOffset="{}"
            GCamera:MicroVideoPresentationTimestampUs="{}" />
        </rdf:RDF>
    </x:xmpmeta>
    """.format(file_size, get_presentation_offset_for_duration(duration))
    return parse(data).childNodes[0].toxml()


def get_xmp_metadata(img_file, movie_file, mp4_file, use_mpv2=False, jpeg=False):
    """
    Adds XMP metadata as if it was taken by GCamera, this is to hint Google
    Photos that there is an embedded Motion Photo part.
    """
    file_size = os.stat(mp4_file).st_size
    duration = get_quicktime_duration_us(movie_file)

    # Here, the second item hints at where the motion photo file itself is
    # embedded. We set the Mime to `video/quicktime` since the provided file
    # itself has `ftypqt  `. Another interesting thing of note, is that the
    # Item:Length of the MotionPhoto resource points to the padding and length
    # of the embedded video file from EOF.
    #
    # Since our file is an HEIF, it's easier to box the QuickTime file, as
    # they're both encoded in the ISOBMFF. We append a new `mpvd` box like so:
    # [ftyp heic][...][meta ][mdat ][mpvd [ftyp qt]<video file here>]
    data = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
          xmlns:Camera="http://ns.google.com/photos/1.0/camera/"
          xmlns:Container="http://ns.google.com/photos/1.0/container/"
          xmlns:Item="http://ns.google.com/photos/1.0/container/item/"
        Camera:MotionPhoto="1"
        Camera:MotionPhotoVersion="1"
        Camera:MotionPhotoPresentationTimestampUs="{}">
        <Container:Directory>
          <rdf:Seq>
            <rdf:li rdf:parseType="Resource">
              <Container:Item
                Item:Mime="image/{}"
                Item:Semantic="Primary"
                Item:Length="0"
                Item:Padding="{}"/>
            </rdf:li>
            <rdf:li rdf:parseType="Resource">
              <Container:Item
                Item:Mime="video/{}"
                Item:Semantic="MotionPhoto"
                Item:Length="{}"
                Item:Padding="0"/>
            </rdf:li>
          </rdf:Seq>
        </Container:Directory>
      </rdf:Description>
    </rdf:RDF>""".format(
        get_presentation_offset_for_duration(duration),
        "jpeg" if jpeg else "heic",
        "0" if jpeg else "16",
        "mp4",  # "quicktime" if movie_file == mp4_file else "mp4",
        "12" if use_mpv2 else file_size
    )

    if not jpeg:
        with HeifFile(img_file) as f:
            p = f.meta.iinf.id_of_kind('mime')
            if len(p) > 1:
                xmp_chunk = f.content[p[-1]]
                xmp_chunk.parse()
                inner = parse(data).getElementsByTagNameNS(
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "Description")[0]
                xmp_chunk.rdf().appendChild(inner)
                return xmp_chunk.contents.childNodes[0].toxml(), file_size

    if jpeg and USE_MICRO_VIDEO_FOR_JPEG:
        return get_xmp_metadata_for_microvideo(duration, file_size), file_size

    data = parse(
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.1.0-jc003">{}</x:xmpmeta>'.format(data))
    return data.childNodes[0].toxml(), file_size


def save_image(file, d, wd, use_mpv2=False, push=True):
    (img_file, movie_file, mp_file, xmp_file,
     jpeg, mp4_file) = get_file_with_movie(file, d, wd)
    save_image_with_paths(img_file, movie_file, mp_file,
                          xmp_file, use_mpv2, jpeg, mp4_file if ENCODE_AS_MP4 else None)
    if push:
        push_to_device(mp_file)


def save_image_with_paths(img_file, movie_file, mp_file, xmp_file, use_mpv2=False, jpeg=False, mp4_file=None):
    shutil.copyfile(img_file, mp_file)

    if not mp4_file:
        mp4_file = movie_file
    else:
        reencode_motion(movie_file, mp4_file)

    # write XMP sidecar
    (metadata, movie_file_size) = get_xmp_metadata(
        img_file, movie_file, mp4_file, use_mpv2, jpeg)
    with open(xmp_file, "w") as f:
        f.write(metadata)

    # attach XMP to the file
    subprocess.run(["exiftool", "-xmp<={}".format(xmp_file),
                   mp_file], stdout=subprocess.DEVNULL)
    mp_file_size = os.stat(mp_file).st_size

    # append the video file behind
    buffer_size = 10000
    mpvd_box_size = (movie_file_size +
                     24) if use_mpv2 else (movie_file_size + 16)

    with open(mp_file, 'ab') as img:
        # create the `mpvd` box
        if not jpeg:
            img.write((1).to_bytes(4, byteorder='big'))
            img.write(b"mpvd")
            img.write(mpvd_box_size.to_bytes(8, byteorder='big'))
        # write the movie file
        with open(mp4_file, 'rb') as mov:
            b = None
            while not b or len(b) == buffer_size:
                b = mov.read(buffer_size)
                img.write(b)
            if use_mpv2 and not jpeg:
                img.write((16).to_bytes(4, byteorder='big'))
                img.write(b'mpv2')
                # account for atom header
                img.write((mp_file_size + 8).to_bytes(4, byteorder='big'))
                img.write(movie_file_size.to_bytes(4, byteorder='big'))


def push_to_device(mp_file):
    # push file to Android device
    subprocess.run(["adb", "push", mp_file, "/sdcard/DCIM/Camera"])


def process_motion_photos(path, use_mpv2=False, push=True):
    if not os.path.exists(path):
        exit("[!!] Folder does not exist!")

    d = path if path.endswith(os.sep) or path.endswith('/') else path + os.sep
    workingdir = d + '__working__' + os.sep
    if not os.path.exists(workingdir):
        os.mkdir(workingdir)

    path = [p for p in os.listdir(path) if p.lower().endswith(
        ".heic") or p.lower().endswith(".jpeg") or p.lower().endswith(".jpg")]

    for file in tqdm(path):
        save_image(file, d, workingdir, use_mpv2, push)


if __name__ == "__main__":
    file = os.path.expanduser(sys.argv[1])
    process_motion_photos(file, push=False, use_mpv2=False)
