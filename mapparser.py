import xml.etree.cElementTree as ET
import pprint


def count_tags(filename):
    tags = {}
    for ev, el in ET.iterparse(filename):
        tag_count = el.tag
        if tag_count not in tags.keys():
            tags[tag_count] = 1
        else:
            tags[tag_count] += 1
    return tags

def test():
    tags = count_tags('map')
    pprint.pprint(tags)

if __name__ == "__main__":
    test()
