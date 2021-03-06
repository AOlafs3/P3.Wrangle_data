from collections import defaultdict
import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import schema

OSM_PATH = "map"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

street_types = defaultdict(set)
expected_street = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Road", "Lane", "Way"] #list of expected street names
mapping = {"St": "Street",
           "st": "Street",
           "STREET": "Street",    #mapping the audit street names to be updated
           "street": "Street",
           "ST": "Street",
           "Rd": "Road",
           "Ave": "Avenue",
           "Ave.": "Avenue",
           "place": "Place"
           }

def update_name(name, mapping):
    m = street_type_re.search(name)

    if m:
        for i in mapping:
            if i == m.group():
                name = re.sub(street_type_re, mapping[i], name)

    return name

def update_state(state):  #updates state abbreviation of WI to Wisconsin
    if state == expected_state:
        return state
    elif state == 'WI':
        return expected_state
    else:
        return "Not in Wisconsin"

expected_state = 'Wisconsin'


phone_re = re.compile(r'\+1*.262*.\d\d\d*.\d\d\d\d')


SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

# Clean and shape node or way XML element to Python dict
def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    nd_attribs = {} #shortened dict name here
    way_attribs = {}
    way_nodes = []
    tags = []
    #used a few sources to help aid understanding of ElemtTree
    #https://docs.python.org/3/library/xml.etree.elementtree.html#xml.etree.ElementTree.Element.remove
    #https://www.datacamp.com/community/tutorials/python-xml-elementtree
    if element.tag == 'node':

        el_attr = element.attrib

        nd_attribs['id'] = int(el_attr['id']) #declared data types for attributes
        nd_attribs['lat'] = float(el_attr['lat'])
        nd_attribs['lon'] = float(el_attr['lon'])
        nd_attribs['user'] = el_attr['user']
        nd_attribs['uid'] = int(el_attr['uid'])  # int
        nd_attribs['version'] = el_attr['version']
        nd_attribs['changeset'] = int(el_attr['changeset'])  # int
        nd_attribs['timestamp'] = el_attr['timestamp']

        # declare root
        root = element.iter('tag')
        for child in root: #loops of child attribute tags
            nd_tag_dict = {}
            child_attributes = child.attrib
            nd_tag_dict['id'] = int(el_attr['id'])
            c_attr_key = child_attributes['k']
            c_attr_value = child_attributes['v']

            if PROBLEMCHARS.match(c_attr_key): #remove problematic characters
                continue

            elif LOWER_COLON.match(c_attr_key): # update attribute keys with colons
                attribute_list = c_attr_key.split(':')
                nd_tag_dict['type'] = attribute_list[0]
                nd_tag_dict['key'] = attribute_list[1]
                if nd_tag_dict['key'] == "street":
                    nd_tag_dict['value'] = update_name(c_attr_value, mapping)
                elif nd_tag_dict['key'] == "state":
                    nd_tag_dict['value'] = update_state(c_attr_value)
                else:
                    nd_tag_dict['value'] = c_attr_value

            else: #handle all other attributes
                nd_tag_dict['type'] = default_tag_type
                nd_tag_dict['key'] = c_attr_key
                if nd_tag_dict['key'] == "street":
                    nd_tag_dict['value'] = update_name(c_attr_value, mapping)
                else:
                    nd_tag_dict['value'] = c_attr_value

            tags.append(nd_tag_dict) #append to tags

        return {'node': nd_attribs, 'node_tags': tags}

    elif element.tag == 'way':

        el_attr = element.attrib

        way_attribs['id'] = int(el_attr['id'])
        way_attribs['user'] = el_attr['user']
        way_attribs['uid'] = int(el_attr['uid'])
        way_attribs['version'] = el_attr['version']
        way_attribs['changeset'] = int(el_attr['changeset'])
        way_attribs['timestamp'] = el_attr['timestamp']

        root = element.iter('tag')
        for tag in root:
            way_tags_dict = {}

            tag_attr = tag.attrib

            way_tags_dict['id'] = int(el_attr['id'])
            tag_attr_key = tag_attr['k']
            tag_attr_value = tag_attr['v']

            if PROBLEMCHARS.match(tag_attr_key): # remove keys with problematic characters
                continue

            elif LOWER_COLON.match(tag_attr_key):  # u[pdate keys with colons
                attr_list = tag_attr_key.split(':')
                way_tags_dict['type'] = attr_list[0]
                way_tags_dict['key'] = attr_list[1]
                if way_tags_dict['key'] == "street":
                    way_tags_dict['value'] = update_name(tag_attr_value, mapping)
                elif way_tags_dict['key'] == "state":
                    way_tags_dict['value'] = update_state(tag_attr_value)
                else:
                    way_tags_dict['value'] = tag_attr_value

            else: # handle all attributes
                way_tags_dict['type'] = default_tag_type
                way_tags_dict['key'] = tag_attr_key
                if way_tags_dict['key'] == "street":
                    way_tags_dict['value'] = update_name(tag_attr_value)

                else:
                    way_tags_dict['value'] = tag_attr_value

            tags.append(way_tags_dict)  # Append tags


        pos = -1
        children_nd = element.iter('nd')

        for i in children_nd:
            nd_tags_dict = {}

            nd_attr = i.attrib

            nd_tags_dict['id'] = int(el_attr['id'])
            nd_tags_dict['node_id'] = int(nd_attr['ref'])

            pos += 1
            nd_tags_dict['position'] = int(pos)

            way_nodes.append(nd_tags_dict) #append way

        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, str) else v) for k, v in row.items()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
            codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
            codecs.open(WAYS_PATH, 'w') as ways_file, \
            codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
            codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=False)

