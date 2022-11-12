from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box, FullAtom
from isobmff.BoxList import BoxList

class MVHD(FullAtom):
    type = b"mvhd"
    
    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MVHD.type)
        self.creation_time = self.buffer.read_int32_be()
        self.modification_time = self.buffer.read_int32_be()
        self.time_scale = self.buffer.read_int32_be()
        self.duration = self.buffer.read_int32_be()
        self.preferred_rate = self.buffer.read_int32_be()
        self.preferred_volume = self.buffer.read_int16_be()
        self.reserved = self.buffer.read(10)
        self.matrix = self.buffer.read(36)
        self.preview_time = self.buffer.read_int32_be()
        self.preview_duration = self.buffer.read_int32_be()
        self.poster_time = self.buffer.read_int32_be()
        self.selection_time = self.buffer.read_int32_be()
        self.selection_duration = self.buffer.read_int32_be()
        self.current_time = self.buffer.read_int32_be()
        self.next_track_id = self.buffer.read_int32_be()

class MOOV(Box):
    type = b'moov'
    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MOOV.type)
        self._read_entries()

    def _read_entries(self):
        self._entries = []
        for atom in BoxList(self.contents(), 0):
            if atom.type == b'mvhd':
                self.mvhd = atom.cast_to(MVHD)
                self._entries.append(self.mvhd)
            else:
                self._entries.append(atom)
