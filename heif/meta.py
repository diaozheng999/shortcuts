from isobmff.Box import FullAtom
from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.BoxList import BoxList


class INFE(FullAtom):
    type = b"infe"

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, INFE.type)
        self.id = self.buffer.read_int16_be()
        self.reserved = self.buffer.read_int16_be()
        self.inf = self.buffer.read_cstring()

        if self.inf == "mime":
            self.mime = self.buffer.read_cstring()
        else:
            self.mime = None

    def repr_additional_info(self):
        contents = super().repr_additional_info()
        if not self.mime:
            return "%s id=0x%04x 0x%04x %s" % (contents, self.id, self.reserved, self.inf)
        else:
            return "%s id=0x%04x 0x%04x %s %r" % (contents, self.id, self.reserved, self.inf, self.mime)


class IINF(FullAtom):
    type = b"iinf"

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, IINF.type)
        self.count = self.buffer.read_int16_be()
        self._read_entries()

    def _read_entries(self):
        self._entries = [x.cast_to(INFE)
                         for x in BoxList(self.contents(), 2).cache]

        self._by_id = {}

        if len(self._entries) != self.count:
            raise Exception("Invalid IINF box")

        for entry in self._entries:
            self._by_id[entry.id] = entry

    def __iter__(self):
        return self._entries.__iter__()

    def first_id_of_kind(self, kind: str):
        for entry in self._entries:
            if entry.inf == kind:
                return entry.id

    def find(self, id: int) -> INFE:
        return self._by_id[id]


class ILOCEntry(object):
    size = 16

    OFFSET_CONTENT_START = 8
    OFFSET_CONTENT_SIZE = 12

    def __init__(self, buffer: BoundedBuffer):
        self.buffer = buffer
        self.offset = buffer.current_position()
        self.id = buffer.read_int16_be()
        self.reserved = buffer.read_int16_be()
        self.reserved_1 = buffer.read_int32_be()
        self.content_start = buffer.read_int32_be()
        self.content_size = buffer.read_int32_be()

    def __repr__(self):
        return "<ILOCEntry id=0x%04x 0x%04x 0x%08x start=0x%08x size=%d>" % (self.id, self.reserved, self.reserved_1, self.content_start, self.content_size)

    def set_content_start(self, n: int):
        self.buffer.seek(self.offset + ILOCEntry.OFFSET_CONTENT_START)
        self.buffer.write_int32_be(n)
        self.content_start = n

    def set_content_size(self, n: int):
        self.buffer.seek(self.offset + ILOCEntry.OFFSET_CONTENT_SIZE)
        self.buffer.write_int32_be(n)
        self.content_size = n


class ILOC(FullAtom):
    type = b"iloc"

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, ILOC.type)
        self.reserved = self.buffer.read_int16_be()
        self.count = self.buffer.read_int16_be()
        self._by_id = {}
        self.content_offset += 4
        self._read_entries()

    def repr_additional_info(self):
        return "%s reserved=%04x count=%d" % (super().repr_additional_info(), self.reserved, self.count)

    def _read_entries(self):
        self._entries = []
        buffer = self.contents()
        buffer.repeat_relative(lambda: self._read_entry(buffer))
        if len(self._entries) != self.count:
            raise Exception("Invalid ILOC box")

    def _read_entry(self, buffer):
        entry = ILOCEntry(buffer)
        self._entries.append(entry)
        self._by_id[entry.id] = entry

    def reversed(self):
        return sorted(self._entries, key=lambda x: x.content_start, reverse=True)

    def __iter__(self):
        return sorted(self._entries, key=lambda x: x.content_start).__iter__()

    def describe_changes(self):
        self.contents().describe_changes()
        
    def __getitem__(self, id: int) -> ILOCEntry:
        return self._by_id[id]

class META(FullAtom):
    type = b'meta'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, META.type)
        self._read_entries()

    def _read_entries(self):
        self._entries = []
        self.iinf = None
        self.iloc = None

        for box in BoxList(self.contents(), 0):
            if (box.type == b'iinf'):
                self.iinf = box.cast_to(IINF)
                self._entries.append(self.iinf)
            elif (box.type == b'iloc'):
                self.iloc = box.cast_to(ILOC)
                self._entries.append(self.iloc)
            else:
                self._entries.append(box)

    def __iter__(self):
        return self._entries.__iter__()
