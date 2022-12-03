import os

from isobmff.BoundedBuffer import BoundedBuffer


class FileBuffer(BoundedBuffer):

    def __init__(self, path: str, readonly=True):
        self.path = path
        self._delta = 0
        super().__init__(None, 0, os.stat(path).st_size, readonly)

    def __enter__(self):
        self.parent = open(self.path, "rb" if self.readonly else "rb+")
        return super().__enter__()

    def __exit__(self, _1, _2, _3):
        super().__exit__(_1, _2, _3)
        self.parent.close()

    def on_resize(self, delta: int):
        self._delta += delta

    def current_size(self):
        return self.size + self._delta
