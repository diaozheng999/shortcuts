import os
import sys
from heif.HeifFile import HeifFile

from heif.MediaFile import MediaFile
from heif.BoxList import BoxList
from heif.meta import IINF, ILOC, META

if __name__ == "__main__":
    file = os.path.expanduser(sys.argv[1])
    with HeifFile(file) as f:
        f.describe_for_motion_photo()
