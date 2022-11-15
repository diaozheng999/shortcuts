from xml.dom import Node
from xml.dom.minidom import parseString


def remove_whitespaces(node: Node):
    blank_nodes = set()

    for child in node.childNodes:
        if child.nodeType == Node.TEXT_NODE and not child.data.strip():
            blank_nodes.add(child)
        else:
            remove_whitespaces(child)

    for blank in blank_nodes:
        node.removeChild(blank)
        blank.unlink()


def parse(contents: str):
    node = parseString(contents)
    remove_whitespaces(node)
    return node
