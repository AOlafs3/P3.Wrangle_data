import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
from typing import Set, Any, Tuple

OSMFILE = 'map'

# looks for type of street in a street address
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

# Audit street types
street_types = defaultdict(set)

expected_street = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Road", "Lane", "Way"]
mapping = {"St": "Street",
           "st": "Street",
           "STREET": "Street",
           "street": "Street",
           "ST": "Street",
           "Rd": "Road",
           "Ave": "Avenue",
           "Ave.": "Avenue",
           "place": "Place"
           }


def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected_street:
            street_types[street_type].add(street_name)


def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")


# audit phone #'s
# looks for phone numbers with +1 country code and 262 area code(https://www.areacodehelp.com/wicode/kenosha_area_code.shtml)
# with or with hyphens and spaces between
phone_re = re.compile(r'\+1*.262*.\d\d\d*.\d\d\d\d')


def audit_phone(phone_types, phnumber):
    good_phone = phone_re.search(phnumber)
    if not good_phone:
        phone_types.add(phnumber)


def is_phone_number(elem):
    return elem.attrib['k'] == 'phone'


# audit postal codes
# found list of expected postal codes for Kenosha, WI(https://www.geonames.org/postal-codes/US/WI/059/kenosha.html)
expected = ['53140', '53141', '53142', '53143', '53144']
# returns all postal codes that are good postal codes
postalcode_re = re.compile(r'5314[0-4]')


def audit_postalcode(bad_postalcodes, postalcode):
    m = postalcode_re.search(postalcode)
    if m:
        postcode = m.group()
        if postcode not in expected:  # checks postal code vs. list of expected postal codes
            bad_postalcodes[postcode] += 1  # if not in expected, adds to bad_postalcodes
    else:
        bad_postalcodes[postalcode] += 1


def is_postalcode(elem):
    return elem.attrib['k'] == 'addr:postcode'


expected_state = ['Wisconsin']

def is_state(elem):
    return elem.attrib['k'] == 'addr:state'


# perform all of the above audits on the file
def audit(osmfile):
    osm_file = open(osmfile, "r", encoding='utf-8')

    phone_types = set()
    bad_postalcodes = defaultdict(int)
    street_types = defaultdict(set)
    bad_state = defaultdict(set)

    for ev, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
                if is_phone_number(tag):
                    audit_phone(phone_types, tag.attrib['v'])
                if is_postalcode(tag):
                    audit_postalcode(bad_postalcodes, tag.attrib['v'])
    osm_file.close()

    return street_types,phone_types, bad_postalcodes


pprint.pprint(audit(OSMFILE))






