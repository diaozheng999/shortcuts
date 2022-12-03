from isobmff.FileBuffer import FileBuffer
from jpeg.Marker import APPMarker, COMMarker, DHTMarker, DQTMarker, DRIMarker, RSTMarker, SOF0Marker, SOF2Marker, SOIMarker, Stream


class JpegFile(FileBuffer):

    def __init__(self, path: str, readonly=True):
        super().__init__(path, readonly)
        self.markers = []
        self._register_marker(SOIMarker)
        self._register_marker(SOF0Marker)
        self._register_marker(SOF2Marker)
        self._register_marker(DHTMarker)
        self._register_marker(DQTMarker)
        self._register_marker(DRIMarker)
        self._register_marker(Stream)
        self._register_marker(RSTMarker)
        self._register_marker(APPMarker)
        self._register_marker(COMMarker)

    def _register_marker(self, marker):
        if marker.type:
            def validate(x): return x == marker.type
        else:
            def validate(x): return marker.validate(x)

        self.markers.append((validate, marker))

    def __enter__(self):
        super().__enter__()

        self.items = []

        while True:
            m = self._create_item()
            if m and self.contains(m):
              self.seek(self._ptr + m)
            else:
              break

        return self

    def _create_item(self):
        cur = self._ptr

        if not self.contains(self._ptr + 1):
          return

        self.seek(self._ptr + 1)
        n = self.read_int8()
        self.seek(cur)

        for (validate, marker) in self.markers:
            if validate(n):
                m = marker(self, self._ptr)
                self.items.append(m)
                m.seek_to_header()
                return m.next()
