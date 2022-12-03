import os
import sys
from jpeg.JpegFile import JpegFile

if __name__ == "__main__":
    img_file = os.path.expanduser(sys.argv[1])

    with JpegFile(img_file) as f:
        for item in f.items:
            print(item)
