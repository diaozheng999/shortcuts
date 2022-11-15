import os
from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box
from isobmff.BoxList import BoxList
from isobmff.PointerBox import BinaryBox


class MediaFile(BoundedBuffer):
    
    def __init__(self, path: str, readonly=True):
        self.path = path
        self.added_boxes = []
        self._delta = 0
        super().__init__(None, 0, os.stat(path).st_size, readonly)

    def __enter__(self):
        self.parent = open(self.path, "rb" if self.readonly else "rb+")
        self.items = BoxList(self, 0)

        for item in self.items:
            item.on_resize = self.on_resize

        return super().__enter__()

    def __exit__(self, _1, _2, _3):
        super().__exit__(_1, _2, _3)
        self.parent.close()

    def find(self, type: bytes) -> Box:
        for box in self.items:
            if box.type == type:
                return box

    def add_box(self, box: BinaryBox):
        self.items.append(box)
        self.added_boxes.append(box)

    def commit(self, file, dry_run=False, indent=0):
        super().commit(file, dry_run, indent)
        for box in self.added_boxes:
            box.commit(file, dry_run, indent)

    def on_resize(self, delta: int):
        self._delta += delta

    def current_size(self):
        return self.size + self._delta