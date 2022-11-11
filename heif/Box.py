from typing import Union
from heif.BoundedBuffer import BoundedBuffer


class InvalidType(Exception):
    def __init__(self, type, received):
        super().__init__("Expected %s, received %r" % (type, received))


class Box(object):
    def __init__(self, buffer: BoundedBuffer, offset: int, type: Union[None, bytes] = None):
        self.buffer = buffer
        self.offset = offset
        self.type = type
        self.content_offset = 8
        self.seek_to_header()
        self.read_header()

    def seek_to_header(self):
        self.buffer.seek(self.offset)

    def read_header(self):
        self.size = self.buffer.read_int32_be()
        type = self.buffer.read(4)

        if self.type and self.type != type:
            raise InvalidType(self.type, type)

        if self.size == 1:
            self.size = self.buffer.read_int64_be()
            self.content_offset += 8

        elif self.size == 0:
            self.size = self.buffer.size - self.offset

        self.type = type

    def contents(self):
        return BoundedBuffer(self.buffer, self.offset + self.content_offset, self.size - self.content_offset)

    def cast_to(self, specialised, **kwargs):
        return specialised(self.buffer, self.offset, **kwargs)

    def repr_additional_info(self):
        return None

    def __repr__(self):
        header = "<%s %s pos=%s size=%d" % (self.__class__.__name__, self.type, self.buffer.format_addr(self.offset), self.size)

        additional_info = self.repr_additional_info()

        if additional_info:
            return "{} {}>".format(header, additional_info)
        else:
            return header + ">"

    def next_offset(self):
        return self.offset + self.size

class FullAtom(Box):
    def __init__(self, buffer: BoundedBuffer, offset: int, type: Union[None, bytes] = None):
        super().__init__(buffer, offset, type)
        self.version = self.buffer.read_int8()
        self.flags = self.buffer.read_int_be(3)
        self.content_offset += 4

    def repr_additional_info(self):
        return "v%d flags=%06x"%(self.version, self.flags)