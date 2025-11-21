import xml.etree.ElementTree as ET


def save_joints_to_xml(joints_list, filename):
    """
    joints_list: List[List[float]] 或 List[Tuple[float]]
                 形如 [(j1..j6), (j1..j6), ...]
                 单位为弧度或角度均可，你自己控制

    filename: 保存路径，例如 "/tmp/path.xml"
    """

    root = ET.Element("RobotPath")

    for idx, joints in enumerate(joints_list, start=1):
        point_elem = ET.SubElement(root, "Point", id=str(idx))

        for j_idx, value in enumerate(joints, start=1):
            joint_elem = ET.SubElement(point_elem, f"Joint{j_idx}")
            joint_elem.text = str(value)

    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
