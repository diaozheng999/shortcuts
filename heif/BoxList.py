from heif.BoundedBuffer import BoundedBuffer
from heif.Box import Box


class BoxList(object):
    def __init__(self, buffer: BoundedBuffer, offset: int):
        self.cache = []
        self.buffer = buffer
        self.buffer.seek(offset)
        self.buffer.repeat(self._append_to_cache)

    def _append_to_cache(self):
        box = Box(self.buffer, self.buffer._ptr)
        self.cache.append(box)
        return box.next_offset()

    def __iter__(self):
        return self.cache.__iter__()

    def find(self, type: str) -> Box:
        for box in self.cache:
            if type == box.type:
                return box
