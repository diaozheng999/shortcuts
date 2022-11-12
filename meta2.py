import os
import sys
from heif.HeifFile import HeifFile

from isobmff.MediaFile import MediaFile
from isobmff.BoxList import BoxList
from heif.meta import IINF, ILOC, META
from qt.QuickTimeFile import QuickTimeFile

if __name__ == "__main__":
    file = os.path.expanduser(sys.argv[1])
    with QuickTimeFile(file) as f:
        for box in f.items:
            print(box)
