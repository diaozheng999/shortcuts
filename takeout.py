import json
import sys
import os
from tqdm import tqdm
from datetime import datetime, timezone

KEEP_METRICS = {
    #"com.google.heart_rate.bpm": "heart_rate",
    #"com.google.height": "height",
    #"com.google.weight": "weight",
    "com.google.step_count.delta": "steps",
    #"com.google.calories.bmr": "resting_energy"
}

def get_dir(root, path):
    return "%s/Fit/%s" % (root, path)


def get_file(filename, counts, entries):
    with open(filename, "r") as f:
        data = json.load(f)

    for point in data["Data Points"]:
        if point["dataTypeName"] in counts:
            counts[point["dataTypeName"]] += 1
        else:
            counts[point["dataTypeName"]] = 1

        if point["dataTypeName"] in KEEP_METRICS:
            try:
                value = point["fitValue"][0]["value"]

                if 'fpVal' in value:
                    value = value['fpVal']
                elif 'intVal' in value:
                    value = value['intVal']
                else:
                    print(value)
                    break

                t = datetime.fromtimestamp(
                    point["startTimeNanos"] / 1000000000, timezone.utc)

                entries.write("%s,%s,%s\n" % (
                    KEEP_METRICS[point["dataTypeName"]],
                    value,
                    t.isoformat()
                ))
            except KeyError:
                print(point)
                break

def get_file(filename, entries):
    acc_type = ""
    acc_date = None
    acc_value = 0

    with open(filename, "r") as f:
        for line in f.readlines():
            [t, v, d] = line.split(",")
            d = datetime.fromisoformat(d)

            if not acc_date or d.date - acc_date :
                


class BufferedOutput(object):
    def __init__(self, path, bufferSize):
        self._path = path
        self._part = 0
        self._bufferSize = bufferSize

    def _openFile(self):
        self.file = open("%s_part_%03d.csv" % (self._path, self._part), 'w')
        self._line = 0

    def _incr(self):
        self._closeFile()
        self._part += 1
        self._openFile()

    def write(self, contents):
        if (self._line >= self._bufferSize):
            self._incr()

        self.file.write(contents)
        self._line += 1

    def __enter__(self):
        self._openFile()
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self._closeFile()

    def _closeFile(self):
        self.file.close()


def get_activity_metrics(root):
    path = get_dir(root, "All data")

    counts = {}

    parts = 0

    with BufferedOutput("data/map", 10000) as outf:
        for f in tqdm(os.listdir(path)):
            get_file(path + "/" + f, counts, outf)
        parts = outf._part

    with open("output.csv", "w") as f:
        for key, value in counts.items():
            f.write("%s,%s\n" % (key, value))


if __name__ == "__main__":
    root = sys.argv[1]
    get_activity_metrics(root)
