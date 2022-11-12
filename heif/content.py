from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box
from heif.meta import INFE, META, ILOCEntry
from xml.dom import Node
from xml.dom.minidom import parse, parseString

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
        parsed = parseString(self.buffer.read(self.buffer.size))
        self._cleanup_nodes(parsed)
        return parsed

    def _cleanup_nodes(self, node):
        blank_nodes = set()

        for child in node.childNodes:
            if child.nodeType == Node.TEXT_NODE and not child.data.strip():
                blank_nodes.add(child)
            else:
                self._cleanup_nodes(child)

        for blank in blank_nodes:
            node.removeChild(blank)
            blank.unlink()

    def attach_xml():
        pass

    def contents_as_string(self):
        return self.contents().toprettyxml(indent="  ")

    def __repr__(self):
        return "<XMPChunk 0x%04x>"%(self.id)

class PointerChunk(Chunk):
    def __init__(self, id: int, index: int, meta: INFE, iloc: ILOCEntry):
        super().__init__(id, index, meta, iloc, None)

    def __repr__(self):
        return "<PointerChunk 0x%04x >"%(self.id)

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
                buffer = BoundedBuffer(file, item.content_start - offs, item.content_size)
                if infe.inf == 'mime' and infe.mime == 'application/rdf+xml':
                    chunk = XMPChunk(item.id, i, infe, item, buffer)
                else:
                    chunk = Chunk(item.id, i, infe, item, buffer)
            else:
                chunk = PointerChunk(item.id, i, infe, item)
            self.chunks.append(chunk)
            self._chunks_by_id[item.id] = chunk
            i += 1

    def repr_additional_info(self):
        return "%d chunk(s)"%(len(self.chunks))
