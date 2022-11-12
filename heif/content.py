from heif.BoundedBuffer import BoundedBuffer
from heif.Box import Box
from heif.meta import INFE, META, ILOCEntry
from xml.etree  import ElementTree

class Chunk(object):
    def __init__(self, id: int, index: int, meta: INFE, iloc: ILOCEntry, buffer: BoundedBuffer):
        self.id = id
        self.index = index
        self.meta = meta
        self.iloc = iloc
        self.buffer = buffer

    def __repr__(self):
        return "<Chunk 0x%04x >"%(self.id)

class XMPChunk(Chunk):
    def contents(self):
        self.buffer.seek(0)
        return ElementTree.fromstring(self.buffer.read(self.buffer.size))

    def contents_as_string(self):
        return ElementTree.dump(self.contents())

    def __repr__(self):
        return "<XMPChunk 0x%04x>"%(self.id)


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
        file = self.buffer.root()
        self.chunks = []
        self._chunks_by_id = {}
        i = 0
        for item in self.meta.iloc:
            infe = self.meta.iinf.find(item.id)
            buffer = BoundedBuffer(file, item.content_start, item.content_size)
            if infe.inf == 'mime' and infe.mime == 'application/rdf+xml':
                chunk = XMPChunk(item.id, i, infe, item, buffer)
            else:
                chunk = Chunk(item.id, i, infe, item, buffer)
            self.chunks.append(chunk)
            self._chunks_by_id[item.id] = chunk
            i += 1

    def repr_additional_info(self):
        return "%d chunk(s)"%(len(self.chunks))
