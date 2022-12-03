from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box, FullAtom
from isobmff.BoxList import BoxList


class HeaderAtom(FullAtom):
    def __init__(self, buffer: BoundedBuffer, offset: int, type: bytes):
        super().__init__(buffer, offset, type)
        self.creation_time = self.buffer.read_int32_be()
        self.modification_time = self.buffer.read_int32_be()


class MVHD(HeaderAtom):
    type = b"mvhd"

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MVHD.type)
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

    def duration_in_s(self):
        return self.duration / self.time_scale

    def duration_in_us(self):
        return round(self.duration_in_s() * 1000000)


class TKHD(HeaderAtom):
    type = b'tkhd'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, TKHD.type)
        self.track_id = self.buffer.read_int32_be()
        self.reserved_1 = self.buffer.read_int32_be()
        self.duration = self.buffer.read_int32_be()
        self.reserved_2 = self.buffer.read_int64_be()
        self.layer = self.buffer.read_int16_be()
        self.alternate_group = self.buffer.read_int16_be()
        self.volume = self.buffer.read_int16_be()
        self.reserved_3 = self.buffer.read_int16_be()
        self.matrix = self.buffer.read(36)
        self.width = self.buffer.read_int32_be()
        self.height = self.buffer.read_int32_be()

    def repr_additional_info(self):
        return "%s id=0x%04x layer=%d alt=0x%04x" % (super().repr_additional_info(), self.track_id, self.layer, self.alternate_group)


class MDHD(HeaderAtom):
    type = b'mdhd'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MDHD.type)
        self.time_scale = self.buffer.read_int32_be()
        self.duration = self.buffer.read_int32_be()
        self.language = self.buffer.read_int16_be()
        self.quality = self.buffer.read_int16_be()


class HDLR(FullAtom):
    type = b'hdlr'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, HDLR.type)
        self.component_type = self.buffer.read(4)
        self.component_subtype = self.buffer.read(4)
        self.manufacturer = self.buffer.read(4)
        self.flags = self.buffer.read_int32_be()
        self.flags_mask = self.buffer.read_int32_be()
        self.name = self.buffer.read_cstring()

    def repr_additional_info(self):
        return "%s name=%s type=%r subtype=%r" % (super().repr_additional_info(), self.name, self.component_type, self.component_subtype)


class StructAtom(Box):
    def __init__(self, buffer: BoundedBuffer, offset: int, type: bytes):
        super().__init__(buffer, offset, type)
        self._read_entries()

    def before_read(self):
        pass

    def on_read(self, atom: Box):
        return atom

    def _read_entries(self):
        self._entries = []

        self.before_read()

        for atom in BoxList(self.contents(), 0):
            self._entries.append(self.on_read(atom))


class StructWithHeader(StructAtom):
    def __init__(self, buffer: BoundedBuffer, offset: int, type: bytes, header):
        self._header_ctor = header
        super().__init__(buffer, offset, type)

    def on_read(self, atom: Box):
        if atom.type == self._header_ctor.type:
            self.header = atom.cast_to(self._header_ctor)
            return self.header
        else:
            return super().on_read(atom)

class MDIA(StructWithHeader):
    type = b'mdia'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MDIA.type, MDHD)

    def on_read(self, atom: Box):
        if atom.type == b'hdlr':
            self.handler = atom.cast_to(HDLR)
            return self.handler
        elif atom.type == b'minf':
            self.info = atom.cast_to(MINF)
            return self.info
        return super().on_read(atom)


class TRAK(StructWithHeader):
    type = b'trak'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, TRAK.type, TKHD)

    def on_read(self, atom: Box):
        if atom.type == b'mdia':
            self.mdia = atom.cast_to(MDIA)
            return self.mdia
        else:
            return super().on_read(atom)


class MOOV(StructWithHeader):
    type = b'moov'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MOOV.type, MVHD)
        self.mvhd = self.header

    def before_read(self):
        self._tracks = []

    def on_read(self, atom: Box):
        if atom.type == b'trak':
            track = atom.cast_to(TRAK)
            self._tracks.append(track)
            return track
        else:
            return super().on_read(atom)

class MINF(StructAtom):
    type = b'minf'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, MINF.type)

    def on_read(self, atom: Box):
        if atom.type == b'stbl':
            self.sample_table = atom.cast_to(SampleTable)
            return self.sample_table
        return super().on_read(atom)

class SampleDescriptionEntry(object):
    def __init__(self, buffer: BoundedBuffer, offset: int):
        self.buffer = buffer
        self.offset = offset
        self.buffer.seek(offset)
        self.size = self.buffer.read_int32_be()
        self.data_format = self.buffer.read(4)
        self.contents = self.buffer.read()


class SampleDescription(FullAtom):
    type = b'stsd'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, SampleDescription.type)
        self.count = self.buffer.read_int32_be()
        self._read_entries()

    def _read_entries(self):
        pass


class SampleTable(StructAtom):
    type = b'stbl'

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, SampleTable.type)
