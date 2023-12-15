
import os
import subprocess
import sys
from tqdm import tqdm

def transfer_file(folder, file_name):
    fname = os.path.join(folder, file_name)
    subprocess.run(["adb", "push", fname, "/sdcard/DCIM/Camera"])
    subprocess.run(["adb", "shell", "am", "broadcast",
                    "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                    "-d", "file:///sdcard/DCIM/Camera/{}".format(file_name)])

def transfer_all(folder):
    for file_name in tqdm(os.listdir(folder)):
        if file_name == '.DS_Store':
            continue
        f = os.path.join(folder, file_name)
        print(f)
        transfer_file(folder, file_name)

if __name__ == "__main__":
    transfer_all(sys.argv[1])
