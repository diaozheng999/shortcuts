import os
import sys
from heif.HeifFile import HeifFile

from isobmff.MediaFile import MediaFile
from isobmff.BoxList import BoxList
from heif.meta import IINF, ILOC, META
from isobmff.PointerBox import PointerBox
from motion_photo import append_xmp_metadata, get_xmp_metadata
from qt.QuickTimeFile import QuickTimeFile

if __name__ == "__main__":
    img_file = os.path.expanduser(sys.argv[1])
    mov_file = os.path.expanduser(sys.argv[2])

    with HeifFile(img_file) as imgf:
        with QuickTimeFile(mov_file) as movf:
            append_xmp_metadata(imgf, movf)

            with open('__out.heic', 'wb') as f:
                imgf.commit(f)

    with HeifFile('__out.heic') as f:
        f.describe_for_motion_photo()
