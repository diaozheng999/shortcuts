from typing import Callable, Tuple, Union


class BufferShort(Exception):
    pass


class UnownedBuffer(Exception):
    pass


class BoundedBuffer(object):
    BUFFER_SIZE = 10000

    def __init__(self, parent, offset: int, size: int, readonly=True):
        self.parent = parent
        self.offset = offset
        self.size = size
        self.end = offset + size
        self._ptr = 0
        self.readonly = readonly
        self.__memo_cached_abs_offset = None
        self.__memo_cached_word_size = None
        self._span = []
        i = 0
        n = size
        while n > 0:
            chunk = min(BoundedBuffer.BUFFER_SIZE, n)
            n -= chunk
            self._span.append((i, chunk))
            i += chunk

        if isinstance(self.parent, BoundedBuffer):
            self.parent._attach_child(self)

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

    def current_position(self):
        return self._ptr

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

    def write_int_be(self, n: int, size: int = 1):
        content = n.to_bytes(size, byteorder='big')
        self.write(size, content)

    def read_int8(self):
        return self.read_int_be(1)

    def write_int8(self, n: int):
        return self.write_int_be(n, 1)

    def read_int16_be(self):
        return self.read_int_be(2)

    def write_int16_be(self, n: int):
        return self.write_int_be(n, 2)

    def read_int32_be(self):
        return self.read_int_be(4)

    def write_int32_be(self, n: int):
        return self.write_int_be(n, 4)

    def read_int64_be(self):
        return self.read_int_be(8)

    def write_int64_be(self, n: int):
        return self.write_int_be(n, 8)

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

    def _size(self, span: Union[Tuple[int, int], bytes]):
        if type(span) == tuple:
            return span[1]
        elif isinstance(span, BoundedBuffer):
            return span.size
        return len(span)

    def _idx(self, offs: int) -> Tuple[int, int, int, Union[Tuple[int, int], bytes]]:
        i = 0
        start = 0
        for span in self._span:
            chunk = self._size(span)
            if start + chunk > offs:
                return (i, start, chunk, span)
            start += chunk
            i += 1

    def _slice_leading(self, offs: int, i: int, start: int, span: Union[Tuple[int, int], bytes]):
        if type(span) == tuple:
            self._span[i] = (start, offs - start)
        elif isinstance(span, BoundedBuffer):
            raise UnownedBuffer("Content is not owned by this buffer!")
        else:
            self._span[i] = span[:offs - start]

    def _slice_trailing(self, offs: int, i: int, start: int, size: int, span: Union[Tuple[int, int], bytes]):
        if offs == start:
            # edge case, the trailing is actually exactly at the point of the
            # next buffer, so no trimming is necessary
            pass
        elif type(span) == tuple:
            self._span[i] = (offs, size - (offs - start))
        elif isinstance(span, BoundedBuffer):
            raise UnownedBuffer("Content is not owned by this buffer!")
        else:
            self._span[i] = span[offs - start:]

    def _write(self, offs: int, size: int, content):
        self._sanity_check()

        start = self._idx(offs)
        end = self._idx(offs + size)

        before = self._span[:start[0] + 1]
        before.append(content)

        if end:
            after = self._span[end[0]:]
            before += after

        self._span = before
        self._slice_leading(offs, start[0], start[1], start[3])
        if end:
            self._slice_trailing(
                offs + size, start[0] + 2, end[1], end[2], after[0])

        span = self._span
        self._span = []

        for i in span:
            if self._size(i) > 0:
                self._span.append(i)

        self._sanity_check(start, end)

    def _sanity_check(self, *args):
        i = 0
        for span in self._span:
            if type(span) == tuple:
                if span[0] < i:
                    print(args)
                    raise AssertionError("Value should be strictly increasing")
                i = span[0] + span[1]

    def write(self, size: int, content: bytes):
        self._write(self._ptr, size, content)
        self._ptr += size

        delta = len(content) - size
        self.size += delta
        return delta

    def _attach_child(self, child):
        self._write(child.offset, child.size, child)

    def _print(self, indent, contents):
        print("%s%s" % (' '*indent, contents))

    def describe_changes(self, indent=0):
        self._print(indent, "%d span(s):" % (len(self._span)))
        for i in self._span:
            if type(i) == tuple:
                self._print(indent, "  - len=%8d  underlying buffer from 0x%08x to 0x%08x" %
                            (i[1], self.offs(i[0]), self.offs(i[0] + i[1])))
            elif isinstance(i, BoundedBuffer):
                self._print(
                    indent, "  - len=%8d  controlled by child buffer" % (i.size, ))
                i.describe_changes(indent + 4)
            else:
                self._print(indent, "  - len=%8d  binary %r" % (len(i), i))

    def _commit_span(self, file, span,  dry_run=False, indent=0):
        if type(span) == tuple:
            (start, size) = span
            if dry_run:
                self._print(indent, "  - len=%8d  underlying buffer from 0x%08x to 0x%08x" %
                            (size, self.offs(start), self.offs(start + size)))
            else:
                self.seek(start)
                contents = self.read(size)
                file.write(contents)
        elif isinstance(span, BoundedBuffer):
            if dry_run:
                self._print(
                    indent, "  - len=%8d  controlled by child buffer" % (span.size, ))
            span.commit(file, dry_run, indent + 4)
        else:
            if dry_run:
                self._print(indent, "  - len=%8d  binary %r" %
                            (len(span), span))
            else:
                file.write(span)

    def commit(self, file, dry_run=False, indent=0):
        for span in self._span:
            self._commit_span(file, span, dry_run, indent)
