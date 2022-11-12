from typing import Callable


class BufferShort(Exception):
    pass


class BoundedBuffer(object):
    def __init__(self, parent, offset: int, size: int, readonly=True):
        self.parent = parent
        self.offset = offset
        self.size = size
        self.end = offset + size
        self._ptr = 0
        self.readonly = readonly
        self.__memo_cached_abs_offset = None
        self.__memo_cached_word_size = None

    def __compute_word_size(self):
        if isinstance(self.parent, BoundedBuffer):
            return self.parent.__compute_word_size()
        elif self.size > 0xffffffff:
            return "0x%016x"
        else:
            return "0x%08x"

    def word_size(self) -> str:
        if self.__memo_cached_word_size == None:
            self.__memo_cached_word_size = self.__compute_word_size()
        return self.__memo_cached_word_size

    def __enter__(self):
        self.seek(0)
        return self

    def __exit__(self, _1, _2, _3):
        pass

    def seek(self, offset: int):
        self.parent.seek(self.offset + offset)
        self._ptr = offset

    def contains(self, ptr: int) -> bool:
        return ptr >= 0 and ptr < self.size

    def contains_next(self, ptr: int) -> bool:
        return ptr >= 0 and ptr <= self.size

    def repeat(self, f: Callable[[], int]):
        while self._ptr < self.size:
            self.seek(f())

    def repeat_relative(self, f: Callable[[], None]):
        while self._ptr < self.size:
            f()

    def read(self, bytes: int) -> bytes:
        if not self.contains_next(self._ptr + bytes):
            raise BufferShort
        self._ptr += bytes
        return self.parent.read(bytes)

    

    def read_cstring(self) -> str:
        if self._ptr == self.size:
            return ""

        self.bytes = b''
        c = self.read(1)
        last_pos = self.size - 1
        while len(c) and c != b'\0' and self._ptr <= last_pos:
            self.bytes += c
            c = self.read(1)

        return self.bytes.decode('utf-8')

    def read_int_be(self, size: int = 1):
        return int.from_bytes(self.read(size), byteorder='big')

    def read_int8(self):
        return self.read_int_be(1)

    def read_int16_be(self):
        return self.read_int_be(2)

    def read_int32_be(self):
        return self.read_int_be(4)

    def read_int64_be(self):
        return self.read_int_be(8)

    def absolute_offset(self) -> int:
        if self.__memo_cached_abs_offset == None:
            self.__memo_cached_abs_offset = self.__compute_absolute_offset()
        return self.__memo_cached_abs_offset

    def __compute_absolute_offset(self):
        if isinstance(self.parent, BoundedBuffer):
            return self.offset + self.parent.absolute_offset()
        else:
            return self.offset

    def root(self):
        if isinstance(self.parent, BoundedBuffer):
            return self.parent.root()
        else:
            return self

    def offs(self, offset):
        return self.absolute_offset() + offset

    def __repr__(self):
        offs = self.absolute_offset()
        return "<BoundedBuffer offs=[0x%08x, 0x%08x] cur=0x%08x parent=%r>" % (offs, offs + self.size, offs + self._ptr, self.parent)

    def format_addr(self, p):
        return self.word_size() % (self.offs(p))

    def format_pos(self, p):
        return ("%d [{}]".format(self.word_size())) % (p, self.offs(p))
