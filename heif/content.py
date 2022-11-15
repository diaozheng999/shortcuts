from typing import Callable
from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box
from heif.meta import INFE, META, ILOCEntry
from xml.dom import Node
from xmp.xmlutil import parse


class Chunk(object):
    def __init__(self, id: int, index: int, meta: INFE, iloc: ILOCEntry, buffer: BoundedBuffer, parent):
        self.id = id
        self.index = index
        self.meta = meta
        self.iloc = iloc
        self.buffer = buffer
        self.delta = 0
        self.original_position_absolute = self.iloc.content_start
        self.size = buffer.size if buffer else 0
        self.parent = parent

    def __repr__(self):
        return "<Chunk 0x%04x >" % (self.id)

    def relocate(self, delta: int):
        self.delta += delta
        self.iloc.set_content_start(
            self.original_position_absolute + self.delta)

    def resize(self, delta: int):
        self.size += delta
        self.iloc.set_content_size(self.size)
        self.parent._on_chunk_resized(self.index, delta)


class XMPChunk(Chunk):
    def __init__(self, id: int, index: int, meta: INFE, iloc: ILOCEntry, buffer: BoundedBuffer, parent):
        super().__init__(id, index, meta, iloc, buffer, parent)
        self.contents = None

    def parse(self):
        if self.contents:
            return
        self.buffer.seek(0)
        self.contents = parse(self.buffer.read(self.buffer.size))

    def contents_as_string(self):
        self.parse()
        return self.contents.toprettyxml(indent="  ")

    def rdf(self):
        self.parse()
        return self.contents.getElementsByTagNameNS(
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "RDF"
        )[0]

    def commit(self):
        content = self.contents.toxml().encode("utf-8")
        self.buffer.seek(0)
        self.buffer.write(self.buffer.size, content)
        delta = len(content) - self.size
        self.resize(delta)

    def __repr__(self):
        return "<XMPChunk 0x%04x>" % (self.id)


class PointerChunk(Chunk):
    def __init__(self, id: int, index: int, meta: INFE, iloc: ILOCEntry, parent):
        super().__init__(id, index, meta, iloc, None, parent)

    def __repr__(self):
        return "<PointerChunk 0x%04x >" % (self.id)


class Content(Box):
    type = b'mdat'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, Content.type)
        self.meta = None

    def read(self, meta: META):
        if not meta or self.meta:
            pass
        self.meta = meta
        file = self.contents()
        self.chunks = []
        self._chunks_by_id = {}
        i = 0
        offs = file.offs(0)
        for item in self.meta.iloc:
            infe = self.meta.iinf.find(item.id)
            if item.content_start >= offs:
                buffer = BoundedBuffer(
                    file, item.content_start - offs, item.content_size)
                if infe.inf == 'mime' and infe.mime == 'application/rdf+xml':
                    chunk = XMPChunk(item.id, i, infe, item, buffer, self)
                else:
                    chunk = Chunk(item.id, i, infe, item, buffer, self)
            else:
                chunk = PointerChunk(item.id, i, infe, item, self)
            self.chunks.append(chunk)
            self._chunks_by_id[item.id] = chunk
            i += 1

    def __getitem__(self, id: int) -> Chunk:
        return self._chunks_by_id[id]

    def _on_chunk_resized(self, pos: int, delta: int):
        self.resize(delta)
        for chunk in self.chunks[pos + 1:]:
            chunk.relocate(delta)

    def repr_additional_info(self):
        return "%d chunk(s)" % (len(self.chunks))
