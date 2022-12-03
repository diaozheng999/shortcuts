import os
import sys

from heif.HeifFile import HeifFile

if __name__ == "__main__":
    img_file = os.path.expanduser(sys.argv[1])

    with HeifFile(img_file) as f:
      f.describe_for_motion_photo()