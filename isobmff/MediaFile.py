import os
from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box
from isobmff.BoxList import BoxList


class MediaFile(BoundedBuffer):
    def __init__(self, path: str, readonly=True):
        self.path = path
        super().__init__(None, 0, os.stat(path).st_size, readonly)

    def __enter__(self):
        self.parent = open(self.path, "rb" if self.readonly else "rb+")
        self.items = BoxList(self, 0)
        return super().__enter__()

    def __exit__(self, _1, _2, _3):
        super().__exit__(_1, _2, _3)
        self.parent.close()

    def find(self, type: bytes) -> Box:
        for box in self.items:
            if box.type == type:
                return box
