import os
import sys
from mp4.MpegFile import MpegFile
from qt.QuickTimeFile import QuickTimeFile

if __name__ == '__main__':
    img_file = os.path.expanduser(sys.argv[1])

    with QuickTimeFile(img_file) as f:

        for track in f.moov._tracks:
            print(track)
            print("  %r" % track.mdia)
            for atom in track.mdia._entries:
              print("    %r" % atom)

            for atom in track.mdia.info.sample_table._entries:
              print("       %r" % atom)