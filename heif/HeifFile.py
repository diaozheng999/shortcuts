from isobmff.MediaFile import MediaFile
from heif.content import Content, XMPChunk
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

            elif item.type == Content.type:
                self.content = item.cast_to(Content)
                items.append(self.content)
            else:
                items.append(item)

        self.items = items
        self.content.read(self.meta)

        return self
        
    def describe_for_motion_photo(self):
        print("Describing HEIF file for Motion Photo")
        print("=====================================")
        print("Scanning %d iinf box(es)..."%(self.meta.iinf.count))
        
        mime_ids = []

        for infe in self.meta.iinf:
            if infe.inf == 'mime':
                print(infe)
                mime_ids.append(infe.id)

        print("found %d XMP chunk(s). %r"%(len(mime_ids), mime_ids))
        
        print("Scanning %d content chunk(s)..."%(len(self.content.chunks)))

        for chunk in self.content.chunks:
            if isinstance(chunk, XMPChunk):
                print(chunk)
                print(chunk.contents_as_string())
