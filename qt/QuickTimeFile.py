from isobmff.MediaFile import MediaFile
from qt.meta import MOOV


class QuickTimeFile(MediaFile):
    def __enter__(self):
        super().__enter__()
        items = []

        self.moov = None

        for item in self.items:
            if item.type == MOOV.type:
                self.moov = item.cast_to(MOOV)
                items.append(self.moov)
            else:
                items.append(item)

        self.items = items
        return self

