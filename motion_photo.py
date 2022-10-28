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
"""

import os
import sys
import cv2
import shutil
import subprocess
from tqdm import tqdm


def get_file_with_movie(name, d, wd):
    (names, ext) = name.rsplit(".", 1)
    img_file = d + names + '.' + ext
    mov_file = d + names + '.mov'
    mp_file = wd + names + '.MP.HEIC'
    xmp_file = wd + names + '.xmp'

    return img_file, mov_file, mp_file, xmp_file


def get_quicktime_duration_us(movie_file):
    """
    Get the duration of a QuickTime movie file in microseconds
    """
    cap = cv2.VideoCapture(movie_file)
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    return round(frames / fps * 1000000)


def get_xmp_metadata(movie_file):
    """
    Adds XMP metadata as if it was taken by GCamera, this is to hint Google
    Photos that there is an embedded Motion Photo part.
    """
    file_size = os.stat(movie_file).st_size
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
    data = '''<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.1.0-jc003">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:GCamera="http://ns.google.com/photos/1.0/camera/"
        xmlns:Container="http://ns.google.com/photos/1.0/container/"
        xmlns:Item="http://ns.google.com/photos/1.0/container/item/"
      GCamera:MotionPhoto="1"
      GCamera:MotionPhotoVersion="1"
      GCamera:MotionPhotoPresentationTimestampUs="{}">
      <Container:Directory>
        <rdf:Seq>
          <rdf:li rdf:parseType="Resource">
            <Container:Item
              Item:Mime="image/heic"
              Item:Semantic="Primary"
              Item:Length="0"
              Item:Padding="0"/>
          </rdf:li>
          <rdf:li rdf:parseType="Resource">
            <Container:Item
              Item:Mime="video/quicktime"
              Item:Semantic="MotionPhoto"
              Item:Length="{}"
              Item:Padding="0"/>
          </rdf:li>
        </rdf:Seq>
      </Container:Directory>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''.format(duration, file_size)
    return data, file_size


def save_image(file, d, wd):
    (img_file, movie_file, mp_file, xmp_file) = get_file_with_movie(file, d, wd)
    save_image_with_paths(img_file, movie_file, mp_file, xmp_file)
    push_to_device(mp_file)

def save_image_with_paths(img_file, movie_file, mp_file, xmp_file):
    shutil.copyfile(img_file, mp_file)

    # write XMP sidecar
    (metadata, movie_file_size) = get_xmp_metadata(movie_file)
    with open(xmp_file, "w") as f:
        f.write(metadata)

    # attach XMP to the file
    subprocess.run(["exiftool", "-xmp<={}".format(xmp_file), mp_file], stdout=subprocess.DEVNULL)

    # For iPhone photos, the mdat box is the last box, and is set
    # to the size 1. Since we're appending another box to the end,
    # we must set it to the actual byte value, so that the file
    # parser knows where the end of the mdat box is.
    mp_file_size = os.stat(mp_file).st_size
    ptr = 0
    with open(mp_file, 'rb+') as img:
        type = ''

        while type != 'mdat':
            img.seek(ptr)
            size = int.from_bytes(
                img.read(4),
                byteorder='big'
            )
            type = img.read(4).decode('utf-8')
            if type != 'mdat':
                ptr += size

        img.seek(ptr)
        mdat_size = mp_file_size - ptr
        img.write(mdat_size.to_bytes(4, byteorder='big'))

    # append the video file behind
    buffer_size = 1000
    ptr = None
    with open(mp_file, 'ab') as img:
        # create the `mpvd` box
        img.write((movie_file_size + 8).to_bytes(4, byteorder='big'))
        img.write(b"mpvd")
        # write the movie file
        with open(movie_file, 'rb') as mov:
            b = None
            while not b or len(b) == buffer_size:
                b = mov.read(buffer_size)
                img.write(b)

def push_to_device(mp_file):
    # push file to Pixel device
    subprocess.run(["adb", "push", mp_file, "/sdcard/DCIM/Camera"])


def process_motion_photos(path):
    if not os.path.exists(path):
        exit("[!!] Folder does not exist!")

    d = path if path.endswith("/") else path + '/'
    workingdir = d + '__working__/'
    if not os.path.exists(workingdir):
        os.mkdir(workingdir)

    path = [p for p in os.listdir(path) if p.lower().endswith(".heic")]

    for file in tqdm(path):
        save_image(file, d, workingdir)


if __name__ == "__main__":
    file = os.path.expanduser(sys.argv[1])
    process_motion_photos(file)
