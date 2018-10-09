#!/usr/bin/env python
# Generates UPPAAL file with node failures

import xml.etree.ElementTree as ET
import sys
import xml.dom.minidom as minidom

tree = ET.parse(sys.argv[1])
root = tree.getroot()

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t")

for child in root.findall('template'):
    name = child.find('name').text
    if name in ['GTSManager','CAPTransmission','GTSAllocationHelper']:
        init = child.find('init').attrib['ref']

        states = []
        for state in child.findall('location'):
            ref = state.attrib['id']
            states.append(ref)

        for state in states:
            transition = ET.SubElement(child,'transition')
            source = ET.SubElement(transition,'source')
            source.set('ref',state)
            target = ET.SubElement(transition,'target')
            target.set('ref',init)
            sync = ET.SubElement(transition,'label')
            sync.set('kind','synchronisation')
            sync.text = 'reset?'
            reset = ET.SubElement(transition,'label')
            reset.set('kind','assignment')
            reset.text = 'resetting()'

print prettify(root)
