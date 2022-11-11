from io import BufferedRandom
import os
import sys


class Sizeable(object):
    def __init__(self, start: int, size: int):
        self.size = size
        self.start = start
        self.end = start + size

    def contains(self, ptr: int):
        return ptr >= self.start and ptr < self.end

    def limits(self):
        return "[min=%d, max=%d]" % (self.start, self.end)


class ISOBMFF(Sizeable):
    def __init__(self, path: str, readonly=True):
        self.path = path
        self.readonly = readonly
        super().__init__(0, os.stat(path).st_size)

    def __enter__(self):
        self.fp = open(self.path, "rb" if self.readonly else "rb+")
        self._ptr = 0
        return self

    def __exit__(self, __1, __2, __3):
        if self.fp:
            self.fp.close()
        self.fp = None

    def seek(self, offset):
        if (offset < 0 or offset >= self.size):
            raise Exception("Seek out of range.")
        self.fp.seek(offset)
        self._ptr = offset

    def read(self, bytes: int, range_: Sizeable = None):
        range_ = range_ or self

        if not range_.contains(self._ptr + bytes):
            raise Exception("buffer short")

        self._ptr += bytes

        return self.fp.read(bytes)

    def read_cstring(self, range_: Sizeable = None):
        self.bytes = b''
        try:
            c = self.read(1, range_)
            while len(c) and c != b'\0':
                self.bytes += c
                c = self.read(1, range_)
        except Exception:
            pass

        return self.bytes.decode('utf-8')

    def read_int8(self, range_: Sizeable = None):
        return int.from_bytes(self.read(1, range_), byteorder='big')

    def read_int16_be(self, range_: Sizeable = None):
        return int.from_bytes(self.read(2, range_), byteorder="big")

    def read_int32_be(self, range_: Sizeable = None):
        return int.from_bytes(self.read(4, range_), byteorder="big")

    def read_int32_le(self, range_: Sizeable = None):
        return int.from_bytes(self.read(4, range_), byteorder="little")

    def boxes(self):
        return Boxes(self, 0, self)

    def first(self):
        return self.boxes().first()

    def __iter__(self):
        return self.boxes().__iter__()

    def box(self, type: str):
        for box in self:
            if (box.type == type):
                return box


class Boxes(object):
    def __init__(self, fp: ISOBMFF, offset: int, parent: Sizeable):
        self.fp = fp
        self.offset = offset
        self.parent = parent

    def first(self):
        return Box(self.fp, self.offset, self.parent)

    def __iter__(self):
        self._iter = True
        self._box = None
        return self

    def __next__(self):
        if self._box:
            self._box = self._box.next()

        if self._box:
            return self._box
        elif self._iter:
            self._box = self.first()
            self._iter = False
            return self._box
        else:
            self._box = None
            raise StopIteration

    def find(self, type: str):
        for box in self:
            if type == box.type:
                return box


class Box(Sizeable):
    def __init__(self, fp: ISOBMFF, offset: int, parent: Sizeable, type=None):
        self.fp = fp
        self.offset = offset
        self.parent = parent

        fp.seek(offset)
        self.size = int.from_bytes(
            fp.read(4),
            byteorder="big"
        )
        self.type = fp.read(4).decode("utf-8")

        if type and self.type != type:
            raise Exception(
                "Invalid type! Expected %s, received %r" % (type, self.type))

        super().__init__(self.offset, self.size)

    def seek(self, offset=0):
        self.fp.seek(self.offset + 8 + offset)

    def next(self):
        if self.size > 8 and self.parent.contains(self.offset + self.size + 8):
            return Box(self.fp, self.offset + self.size, self.parent)

    def child(self, offset=0):
        return Boxes(self.fp, self.offset + 8 + offset, self)

    def cast(self, specialised):
        return specialised(self.fp, self.offset, self.parent)


class INFE(Box):
    type = "infe"

    def __init__(self, fp: ISOBMFF, offset: int, parent: Sizeable):
        super().__init__(fp, offset, parent, INFE.type)
        self.version = self.fp.read_int8(self.parent)
        self.flags = int.from_bytes(self.fp.read(3), byteorder="big")
        self.id = self.fp.read_int16_be(self.parent)
        self.b = self.fp.read_int16_be(self.parent)
        self.type = self.fp.read_cstring(self.parent)

        if self.type == "mime":
            self.subtype = self.fp.read_cstring(self.parent)
        else:
            self.subtype = None

    def __repr__(self) -> str:
        if not self.subtype:
            return "< infe v%d flags=%06x 0x%04x 0x%04x %s >" % (self.version, self.flags, self.id, self.b, self.type)
        else:
            return "< infe v%d flags=%06x 0x%04x 0x%04x %s %r >" % (self.version, self.flags, self.id, self.b, self.type, self.subtype)


class IINF(Box):
    type = "iinf"

    def __init__(self, fp: ISOBMFF, offset: int, parent: Sizeable):
        super().__init__(fp, offset, parent, IINF.type)
        self.seek(4)
        self.size = self.fp.read_int16_be()
        self._read_entries()

    def _read_entries(self):
        self._cnt = 0
        self._entries = []
        for box in self.child(6):
            self._cnt += 1
            self._entries.append(box.cast(INFE))
        if self._cnt != self.size:
            raise Exception("Invalid IINF box")

    def entries(self):
        return self._entries


if __name__ == "__main__":
    file = os.path.expanduser(sys.argv[1])
    with ISOBMFF(file) as f:
        meta = f.box("meta")

        iinf = meta.child(4).find("iinf").cast(IINF)

        for infe in iinf.entries():
            print(infe)
