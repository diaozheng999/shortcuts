from isobmff.BoundedBuffer import BoundedBuffer
from isobmff.Box import Box


class BinaryBox(Box):
    def __init__(self, type: bytes):
        self.type = type

    def get_content_size(self):
        return 0
    
    def commit_content(self, file, dry_run=False, indent=0):
        pass

    def get_header_size(self):
        content_size = self.get_content_size()
        # decide if small or large
        if content_size > 0xffffffff:
            return 16
        else:
            return 8

    def get_size(self):
        return self.get_header_size() + self.get_content_size()

    def commit(self, file, dry_run=False, indent=0):
        content_size = self.get_content_size()
        # decide if small or large
        if content_size > 0xffffffff:
            size = content_size + 16
            self._commit_int32_be(file, 1, dry_run, indent)
            self._commit_bytes(file, self.type, dry_run, indent)
            self._commit_int64_be(file, size, dry_run, indent)
        else:
            print(self.type)
            size = content_size + 8
            self._commit_int32_be(file, size, dry_run, indent)
            self._commit_bytes(file, self.type, dry_run, indent)
        self.commit_content(file, dry_run, indent)

    def _commit_int64_be(self, file, value: int, dry_run=False, indent=0):
        if dry_run:
            self._print(indent, "- len=%8d  int64_value %d" % (8, value))
        else:
            file.write(value.to_bytes(8, byteorder='big'))

    def _commit_int32_be(self, file, value: int, dry_run=False, indent=0):
        if dry_run:
            self._print(indent, "- len=%8d  int32_value %d" % (8, value))
        else:
            file.write(value.to_bytes(4, byteorder='big'))

    def _commit_bytes(self, file, value: bytes, dry_run=False, indent=0):
        if dry_run:
            self._print(indent, "- len=%8d  binary %r" % (len(value), value))
        else:
            file.write(value)

    def _print(self, indent, contents):
        print("%s%s" % (' '*indent, contents))


class PointerBox(BinaryBox):
    def __init__(self, buffer: BoundedBuffer, type: bytes):
        super().__init__(type)
        self.buffer = buffer

    def get_content_size(self):
        return self.buffer.size

    def commit_content(self, file, dry_run=False, indent=0):
        self.buffer.commit(file, dry_run, indent)

class MemoryBox(BinaryBox):
    def __init__(self, contents: bytes, type: bytes):
        super().__init__(type)
        self.contents = contents

    def get_content_size(self):
        return len(self.contents)

    def commit_content(self, file, dry_run=False, indent=0):
        self._commit_bytes(file, self.contents, dry_run, indent)
