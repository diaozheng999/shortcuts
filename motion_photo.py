from heif.HeifFile import HeifFile
from isobmff.PointerBox import MemoryBox, PointerBox
from qt.QuickTimeFile import QuickTimeFile
from xmp.xmlutil import parse


def get_quicktime_duration_in_us(movie: QuickTimeFile):
    return movie.moov.mvhd.duration_in_us()


def get_xmp_metadata(movie: QuickTimeFile):
    # file_size = movie.size
    # duration = get_quicktime_duration_in_us(movie)

    data = """
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
          xmlns:GCamera="http://ns.google.com/photos/1.0/camera/"
          xmlns:Container="http://ns.google.com/photos/1.0/container/"
          xmlns:Item="http://ns.google.com/photos/1.0/container/item/"
        GCamera:MotionPhoto="1"
        GCamera:MotionPhotoVersion="1"
        GCamera:MotionPhotoPresentationTimestampUs="0">
        <Container:Directory>
          <rdf:Seq>
            <rdf:li rdf:parseType="Resource">
              <Container:Item
                Item:Mime="image/heic"
                Item:Semantic="Primary"
                Item:Length="0"
                Item:Padding="0"/>
            </rdf:li>
            <rdf:li rdf:parseType="Resource">
              <Container:Item
                Item:Mime="video/quicktime"
                Item:Semantic="MotionPhoto"
                Item:Length="12"
                Item:Padding="0"/>
            </rdf:li>
          </rdf:Seq>
        </Container:Directory>
      </rdf:Description>
    </rdf:RDF>"""

    data = parse(data)
    return data.getElementsByTagNameNS("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "Description")[0]


def append_xmp_metadata(file: HeifFile, movie: QuickTimeFile):
    xmp_metadata = get_xmp_metadata(movie)
    id = file.meta.iinf.first_id_of_kind('mime')

    xmp_chunk = file.content[id]
    xmp_chunk.parse()
    xmp_chunk.rdf().appendChild(xmp_metadata)
    xmp_chunk.contents.getElementsByTagNameNS("adobe:ns:meta/", "xmpmeta")[0].setAttributeNS(
      'adobe:ns:meta/',
      'x:xmptk',
      'Adobe XMP Core 5.1.0-jc003'
    )
    xmp_chunk.commit()

    mpvd = PointerBox(movie, b'mpvd')

    contents = b"MotionPhoto_Datampv2" + \
        (file.current_size() + mpvd.get_header_size()
         ).to_bytes(4, 'big') + movie.size.to_bytes(4, 'big')

    mpv2 = MemoryBox(contents, b'mpv2')

    file.add_box(mpvd)
    file.add_box(mpv2)

