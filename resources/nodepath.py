from .codewalker_xml import *
from xml.etree import ElementTree as ET


class YND:

    file_extension = ".ynd.xml"

    @staticmethod
    def from_xml_file(filepath):
        return NodePath.from_xml_file(filepath)

    @staticmethod
    def write_xml(node, filepath):
        return node.write_xml(filepath)


class JunctionRefItem(ElementTree):
    tag_name = "Item"

    def __init__(self):
        super().__init__()
        self.area_id = ValueProperty("AreaID")
        self.node_id = ValueProperty("NodeID")
        self.junction_id = ValueProperty("JunctionID")
        self.unk_0 = ValueProperty("Unk0")


class JunctionRefListProperty(ListProperty):
    list_type = JunctionRefItem
    tag_name = "JunctionRefs"


class JunctionItem(ElementTree):
    tag_name = "Item"

    def __init__(self):
        super().__init__()
        self.position = Vector2Property("Position")
        self.min_z = ValueProperty("MinZ")
        self.max_z = ValueProperty("MaxZ")
        self.size_x = ValueProperty("SizeX")
        self.size_y = ValueProperty("SizeY")
        self.heightmap = TextProperty("Heightmap")


class JunctionListProperty(ListProperty):
    list_type = JunctionItem
    tag_name = "Junctions"


class LinkItem(ElementTree):
    tag_name = "Item"

    def __init__(self):
        super().__init__()
        self.to_area_id = ValueProperty("ToAreaID")
        self.to_node_id = ValueProperty("ToNodeID")
        self.flags_0 = ValueProperty("Flags0")
        self.flags_1 = ValueProperty("Flags1")
        self.flags_2 = ValueProperty("Flags2")
        self.length = ValueProperty("LinkLength")


class LinkListProperty(ListProperty):
    list_type = LinkItem
    tag_name = "Links"


class NodeItem(ElementTree):
    tag_name = "Item"

    def __init__(self):
        super().__init__()
        self.area_id = ValueProperty("AreaID")
        self.node_id = ValueProperty("NodeID")
        self.streetname = TextProperty("StreetName")
        self.area_id = VectorProperty("Position")
        self.flags_0 = ValueProperty("Flags0")
        self.flags_1 = ValueProperty("Flags1")
        self.flags_2 = ValueProperty("Flags2")
        self.flags_3 = ValueProperty("Flags3")
        self.flags_4 = ValueProperty("Flags4")
        self.flags_5 = ValueProperty("Flags5")
        self.links = LinkListProperty()


class NodeListProperty(ListProperty):
    list_type = NodeItem
    tag_name = "Nodes"


class NodePath(ElementTree, AbstractClass):
    tag_name = "NodeDictionary"

    def __init__(self):
        super().__init__()
        self.vehicle_node_count = ValueProperty("VehicleNodeCount")
        self.ped_node_count = ValueProperty("PedNodeCount")
        self.nodes = NodeListProperty()
