"""
Syncs the new photos in the Photo Library to an Android device for uploading
to Google Photos.

This script will also convert Live Photos to a compatible format that is
understandable by Google Photos.

Requires the following to be installed and inside PATH:
1. exiftool
2. adb

Requires the following python packages
1. opencv_python
2. tqdm

This script is meant to be run on a Mac, where you have the ability to sync
photos over to Photos.app. On Windows or Linux, use `motion_photo.py` to copy
the image files directly. 
"""

import sqlite3
import os
import motion_photo
import shutil
import subprocess
from tqdm import tqdm

# Where the Photos Library package sits. This should be ~/Pictures by default
PHOTO_LIB_DIR = os.path.expanduser('~/Pictures/Photos Library.photoslibrary')


def path(p):
    return PHOTO_LIB_DIR + p


class Photo(object):
    """
    Represents a specific photo in the Photo library
    """

    filenames = {}
    """
    To disambiguate between multiple photos of the same name. For example,
    all FaceTime photos are stored as `lp_image.heic`.
    """

    def __init__(self, pk, subtype, filename, uuid, originalFilename, exported):
        self.pk = pk                            # photo primary key
        self.uuid = uuid                        # photo UUID
        self.update_filename(originalFilename or filename)
        self.ext = filename.split(".")[1]       # extension. either `jpeg` or `heic`
        self.decide_kind(subtype)
        self.exported = exported                # whether file has already been exported
        self.update_original(filename)
        self.copied_to_output = False           # whether file has been processed

    def decide_kind(self, subtype):
        """
        The Photos enumeration. We use this to determine if it's a live photo
        """
        if subtype == 0:
            self.subtype = "still"
        elif subtype == 2:
            self.subtype = 'live_photo'
        elif subtype == 10:
            self.subtype = 'screenshot'
        elif subtype == 100:
            self.subtype = 'video'
        elif subtype == 101:
            self.subtype = 'slow_mo'
        elif subtype == 102:
            self.subtype = 'timelapse'

    def update_filename(self, originalFilename):
        """
        sets the output filename (i.e. the filename visible to Google Photos)
        based on the ZORIGINALFILENAME column.
        """

        # set filename here
        name = originalFilename.lower()
        if name not in Photo.filenames:
            self.filename = originalFilename
            Photo.filenames[name] = 0
        else:
            (name_wo_ext, ext) = originalFilename.split(".")
            self.filename = "{}_{}.{}".format(
                name_wo_ext,
                Photo.filenames[name],
                ext
            )
        Photo.filenames[name] += 1

    def update_original(self, filename):
        """
        Sets the path to the original photo file inside the Photo Library.
        This is usually stored in
        
        `<pkg>/originals/{first letter of UUID}/{UUID}.(jpeg|heic)`
        
        If the photo is a live photo, then the accompanying movie is stored at
        
        `<pkg>/originals/{first letter of UUID}/{UUID}_3.mov`
        """
        self.original = path("/originals/{}/{}".format(filename[0], filename))
        if (self.subtype == 'live_photo'):
            self.movie_path = path(
                "/originals/{}/{}_3.mov".format(filename[0], self.uuid))

    def copy_to_output(self, output_folder):
        """
        Process the photo to store to the Android device's camera roll.

        If the photo is a live photo, embed the video such that Google Photos
        treats it as a motion photo.
        """
        output = output_folder + self.filename
        self.__output_filename = output
        if self.copied_to_output:
            return
        elif self.subtype != 'live_photo':
            shutil.copyfile(self.original, output)
            self.copied_to_output = True
        elif self.ext != "heic":
            # TODO: support JPEG live photos, should behave similar
            # to GCamera output.
            print("JPEG Live Photos are not supported yet")
        else:
            xmp_file = output_folder + self.uuid + ".xmp"
            motion_photo.save_image_with_paths(
                self.original,
                self.movie_path,
                output,
                xmp_file
            )
            os.remove(xmp_file)
            os.remove(output + "_original")
            self.copied_to_output = True

    def push_to_device(self, cursor, conn):
        """
        Push this to the Android device using ADB.
        """
        motion_photo.push_to_device(self.__output_filename)
        subprocess.run(["adb", "shell", "am", "broadcast",
                        "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                        "-d", "file:///sdcard/DCIM/Camera/{}".format(self.filename)])
        cursor.execute("""
        INSERT INTO ext_google_photo_export (PK, EXPORTED) values ({}, 1)
        """.format(self.pk))
        conn.commit()

def setup_connection(conn):
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ext_google_photo_export (
        PK integer primary key,
        EXPORTED integer
    )
    """)

    return cur


def get_photos_to_upload(cur):
    res = cur.execute("""
    SELECT
        a.Z_PK,
        ZKindSubtype,
        ZFilename,
        ZUUID,
        ZOriginalFilename,
        EXPORTED
    FROM
        ZAsset a
        LEFT JOIN ZAdditionalAssetAttributes aa on aa.Z_PK = a.Z_PK
        LEFT JOIN ext_google_photo_export e on e.PK = a.Z_PK
    WHERE
        EXPORTED is null
    """)

    photos = []

    for row in res.fetchall():
        print(row)
        photos.append(Photo(*row))

    return photos


if __name__ == "__main__":
    conn = sqlite3.connect(path('/database/Photos.sqlite'))
    cur = setup_connection(conn)

    output = "out/"

    if not os.path.exists(output):
        os.mkdir(output)

    photos = get_photos_to_upload(cur)
    count = 0

    for photo in tqdm(photos):
        photo.copy_to_output(output)
        if photo.copied_to_output:
            count += 1

    print("{} of {} photo(s) processed.".format(count, len(photos)))

    print("exporting file to device...")
    for photo in photos:
        photo.push_to_device(cur, conn)
