from heif.BoundedBuffer import BoundedBuffer
from heif.Box import Box
from heif.meta import META
from xml.dom.minidom import parse, parseString


class XMPChunk(BoundedBuffer):
    def contents(self):
        parseString(self.read(self.size))


class Content(Box):
    type = b'mdat'

    def __init__(self, buffer: BoundedBuffer, offset: int, meta: META):
        super().__init__(buffer, offset, Content.type)
        self.meta = None
        self.read(meta)

    def read(self, meta: META):
        if not meta or self.meta:
            pass
        self.meta = meta
        contents = self.contents()
        self.chunks = []
        for item in self.meta.iloc:
            pass
