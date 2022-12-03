from typing import Union
from isobmff.BoundedBuffer import BoundedBuffer


class Marker(object):

    def __init__(self, buffer: BoundedBuffer, offset: int, type: Union[None, int] = None):
        self.buffer = buffer
        self.offset = offset
        self.type = type
        self.content_offset = 2
        self.seek_to_header()
        self.read_header()
        self._delta = 0
        self._contents = None
        self.on_resize = None

    def seek_to_header(self):
        self.buffer.seek(self.offset)

    def get_size(self):
        self.size = 0

    def read_header(self):
        if self.buffer.read_int8() != 0xff:
            raise AssertionError("Invalid Encoding")

        type = self.buffer.read_int8()

        if self.type and self.type != type:
            raise AssertionError("Invalid Type")

        self.type = type

        self.get_size()

    def contents(self):
        if not self._contents:
            self._contents = BoundedBuffer(
                self.buffer, self.offset + self.content_offset, self.size)
        return self._contents

    def next(self):
        return self.content_offset + self.size

    def repr_additional_info(self):
        return None

    def __repr__(self):
        header = "<%s %02x pos=%s size=%d" % (
            self.__class__.__name__, self.type, self.buffer.format_addr(self.offset), self.size)

        additional_info = self.repr_additional_info()

        if additional_info:
            return "{} {}>".format(header, additional_info)
        else:
            return header + ">"


class MarkerWithData(Marker):
    def get_size(self):
        self.size = self.buffer.read_int16_be()


class SOIMarker(Marker):
    type = 0xd8

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, SOIMarker.type)


class SOF0Marker(MarkerWithData):
    type = 0xc0

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, SOF0Marker.type)


class SOF2Marker(MarkerWithData):
    type = 0xc2

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, SOF2Marker.type)


class DHTMarker(MarkerWithData):
    type = 0xc4

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, DHTMarker.type)


class DQTMarker(MarkerWithData):
    type = 0xdb

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, DQTMarker.type)


class DRIMarker(MarkerWithData):
    type = 0xdd

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, DRIMarker.type)


class Stream(MarkerWithData):
    SOS = 0xda
    EOI = 0xd9
    type = 0xda

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, Stream.SOS)

    def get_size(self):
        start = self.buffer.current_position()
        header_size = self.buffer.read_int16_be()
        self.layer = self.buffer.read(header_size - 2)
        terminated = False

        while not terminated:
            if not self.buffer.contains_next(self.buffer.current_position() + 1):
                self.size = self.buffer.current_position() + 1 - start
                break
            if self.buffer.read_int8() == 0xff:
                cur = self.buffer.current_position()
                next = self.buffer.read_int8()
                if next == Stream.EOI:
                    self.size = self.buffer.current_position() - start
                    break
                else:
                    self.buffer.seek(cur)


class RSTMarker(Marker):
    type = None

    @staticmethod
    def validate(type: int):
        return type >= 0xd0 and type < 0xd8

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset)
        if not RSTMarker.validate(self.type):
            raise AssertionError("Invalid Encoding")


class APPMarker(MarkerWithData):
    type = None

    @staticmethod
    def validate(type: int):
        return type >= 0xe0 and type <= 0xef

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset)
        if not self.validate(self.type):
            raise AssertionError("Invalid Encoding")


class COMMarker(MarkerWithData):
    type = 0xfe

    def __init__(self, buffer: BoundedBuffer, offset: int):
        super().__init__(buffer, offset, COMMarker.type)
