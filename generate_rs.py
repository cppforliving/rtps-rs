from __future__ import print_function

import json
import os
import re
from contextlib import closing
from fileinput import FileInput
from urllib import URLopener
from xml.etree import ElementTree as ET

from xmljson import badgerfish as bf


def download_and_save_file(url, filename):
    if not os.path.exists(filename):
        URLopener().retrieve(url + filename, filename)
    else:
        print(filename + " already exists")


def replace_inside_file(filename, strings):
    input = FileInput(filename, inplace=True)
    with closing(input):
        for line in input:
            for old, new in strings.items():
                line = line.replace(old, new)
            print(line, end="")


def register_namespaces(xmi_name):
    nsmap = {}
    for _, prefix_uri in ET.iterparse(xmi_name, events=("start-ns",)):
        nsmap[prefix_uri[0]] = prefix_uri[1]
    for prefix, uri in nsmap.items():
        ET.register_namespace(prefix, uri)
    return nsmap


def norm(uri):
    return "{" + uri + "}"


def expand(attrib, nsmap):
    qual_attr = attrib.split(":")
    if len(qual_attr) == 1:
        return attrib
    else:
        return norm(nsmap[qual_attr[0]]) + qual_attr[1]


def strip_xmi_file(xmi_name, nsmap):
    tree = ET.parse(xmi_name)
    tree.write("formatted_" + xmi_name, encoding="UTF-8", xml_declaration=True)
    pattern = re.compile("^a[0-9]{9}-[0-9]{4}(_collaboration)?$")
    for node in tree.iter():
        for key, val in node.attrib.items():
            if val[0] == "_" or pattern.match(val):
                del node.attrib[key]
        for attrib in ["xmi:id", "xmi:idref", "xmi:uuid"]:
            key = expand(attrib, nsmap)
            if key in node.attrib.keys():
                del node.attrib[key]
    tree.write("stripped_" + xmi_name, encoding="UTF-8", xml_declaration=True)


def convert_xmi_to_json(xmi_name):
    tree = ET.parse(xmi_name)
    root = tree.getroot()
    json_name = xmi_name.split(".")[0] + ".json"
    with open(json_name, "w") as outfile:
        json.dump(bf.data(root), outfile, indent=2)
    return json_name


def remap_urls(nsmap):
    url_remap = {}
    for prefix, uri in nsmap.items():
        url_remap[norm(uri)] = prefix + ":"
    return url_remap


def make_dir(path):
    p = "/".join(path)
    if not os.path.exists(p):
        os.makedirs(p)


def open_file(path, mode):
    make_dir(path[:-1])
    return open("/".join(path) + ".rs", mode)


def make_directory_struct(xmi_name, nsmap):
    path = ["src"]
    for event, elem in ET.iterparse(xmi_name, events=("start", "end",)):
        if "name" in elem.attrib.keys() \
                and not "&#10;" in elem.attrib["name"] \
                and not ":=" in elem.attrib["name"] \
                and elem.tag in [
            "nestedClassifier",
            "ownedAttribute",
            "ownedEnd",
            "ownedLiteral",
            "ownedOperation",
            "ownedParameter",
            "packagedElement",
        ]:
            if event == "start":
                name = elem.attrib["name"].replace("::", "/").split("[")[0]
                if not "=" in name:
                    name = name.replace(" ", "_")
                if elem.tag.startswith("owned"):
                    pass
                elif not name in path:
                    path.append(name)
                else:
                    path.append(".")
                xmi_type = expand("xmi:type", nsmap)
                if xmi_type in elem.attrib.keys():
                    uml_type = elem.attrib[xmi_type]
                    if uml_type in [
                        "uml:Model",
                        "uml:Package",
                        "uml:Profile",
                    ]:
                        pass
                    elif uml_type in [
                        "uml:AssociationClass",
                        "uml:Class",
                        "uml:DataType",
                        "uml:Enumeration",
                        "uml:Stereotype",
                    ]:
                        open_file(path, "a").close()
                    elif uml_type in [
                        "uml:Association",
                        "uml:EnumerationLiteral",
                        "uml:ExtensionEnd",
                        "uml:Operation",
                        "uml:Parameter",
                        "uml:Property",
                    ]:
                        if elem.tag.startswith("owned") and path[-1].endswith(".rs"):
                            with open_file(path, "a") as rs_file:
                                rs_file.write(name + ": " + uml_type + ",\n")
                        else:
                            print("/".join(path).replace(".rs/", "") +
                                  "..." + elem.tag + " is not owned")
                    elif uml_type in [
                        "uml:Actor",
                        "uml:Collaboration",
                        "uml:InstanceSpecification",
                        "uml:Node",
                        "uml:Profile",
                        "uml:Signal",
                        "uml:SignalEvent",
                        "uml:StateMachine",
                    ]:
                        print("- " + uml_type + " " + elem.attrib["name"])
                    else:
                        raise Exception("unsupported uml_type: " + uml_type)
            elif event == "end" and not elem.tag.startswith("owned"):
                path.pop()


def make_uml_struct(xmi_name, nsmap):
    path = ["uml"]
    xmi_type = expand("xmi:type", nsmap)
    for event, elem in ET.iterparse(xmi_name, events=("start", "end",)):
        if xmi_type in elem.attrib.keys():
            if event == "start":
                uml_type = elem.attrib[xmi_type][4:]
                if not uml_type in path:
                    path.append(uml_type)
                    make_dir(path)
                else:
                    path.append(".")
            elif event == "end":
                path.pop()


def shrink(tag, nsmap):
    for prefix, uri in nsmap.items():
        if tag.startswith(norm(uri)):
            return tag.replace(norm(uri), prefix + ":")
    return tag


def make_xmi_struct(xmi_name, nsmap):
    path = []
    for event, elem in ET.iterparse(xmi_name, events=("start", "end",)):
        if event == "start":
            elem_tag = shrink(elem.tag, nsmap)
            if not elem_tag in path:
                path.append(elem_tag)
                make_dir(path)
            else:
                path.append(".")
        elif event == "end":
            path.pop()


def make_data_type(elem_names):
    print(elem_names)
    data_type = ""
    for elem_name in elem_names:
        data_type += elem_name
        if str(elem_name[0]).islower():
            data_type += "::"
    if data_type.endswith("_t") or data_type.endswith("::"):
        data_type = data_type[:-2]
    return data_type


def remove_protocol_prefix(name):
    prefix = "Protocol::"
    return name[len(prefix):] if name.startswith(prefix) else name


def remove_trailing_one(name):
    return name[:-1] if name.endswith("1") else name


def get_uml_elements(xmi_name, nsmap, uml_elems):
    data_types = set()
    elem_names = []
    xmi_type = expand("xmi:type", nsmap)
    for event, elem in ET.iterparse(xmi_name, events=("start", "end",)):
        elem_name = elem.attrib.get("name")
        if elem_name and elem.attrib[xmi_type] != "uml:Model":
            elem_name = remove_protocol_prefix(elem_name)
            if elem_name != "Protocol":
                if event == "start":
                    if elem.attrib[xmi_type] == "uml:Package":
                        elem_name = make_snake_case(elem_name)
                    else:
                        elem_name = elem_name.split("[", 1)[0]
                    elem_names.append(remove_trailing_one(elem_name))
                    if elem.attrib[xmi_type] in uml_elems:
                        data_types.add(make_data_type(elem_names))
                elif event == "end":
                    elem_names.pop()
    return sorted(data_types)


def make_snake_case(name):
    s0 = re.sub("([A-Z0-9]{3})([a-z])", r"\1_\2", name)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s0)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def import_data_types(data_types):
    print(data_types)
    for data_type in data_types:
        data_type = data_type.split("::")
        data_type.insert(0, "src")
        if data_type[-1].islower():
            continue
        data_type[-1] = make_snake_case(data_type[-1])
        open_file(data_type, "a+").close()
        while len(data_type) > 2:
            pub_mod_text = "pub mod " + data_type[-1] + ";"
            data_type[-1] = "mod"
            with open_file(data_type, "a+") as mod_file:
                if not pub_mod_text in mod_file.read():
                    mod_file.write(pub_mod_text + "\n")
                    print(pub_mod_text + " added to " + mod_file.name)
                else:
                    print(pub_mod_text + " already in " + mod_file.name)
            data_type.pop()


def main():
    spec_url = "https://www.omg.org/spec/DDSI-RTPS/20131215/"
    xmi_name = "dds_rtps_uml_xmi.xmi"
    download_and_save_file(spec_url, xmi_name)
    nsmap = register_namespaces(xmi_name)
    import_data_types(get_uml_elements(
        xmi_name, nsmap, ["uml:DataType",]))
    # make_directory_struct(xmi_name, nsmap)
    # make_uml_struct(xmi_name, nsmap)
    # make_xmi_struct(xmi_name, nsmap)
    # strip_xmi_file(xmi_name, nsmap)
    # json_name = convert_xmi_to_json(xmi_name)
    # replace_inside_file(json_name, remap_urls(nsmap))


if __name__ == "__main__":
    main()
