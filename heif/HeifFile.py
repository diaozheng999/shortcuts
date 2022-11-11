from heif.MediaFile import MediaFile
from heif.content import Content
from heif.meta import META


class HeifFile(MediaFile):
    def __enter__(self):
        super().__enter__()
        items = []
        self.content = None
        self.meta = None

        for item in self.items:
            if item.type == META.type:
                self.meta = item.cast_to(META)
                items.append(self.meta)
                if self.content:
                    self.content.read(self.meta)

            elif item.type == Content.type:
                self.content = item.cast_to(Content, meta=self.meta)
                items.append(self.content)
            else:
                items.append(item)

        self.items = items

        return self
        
