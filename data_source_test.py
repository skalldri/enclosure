#!/usr/bin/python3

from data_source import SlotMapDataSource, Enclosure, Slot

def SlotMapDataSourceTest():
    s = SlotMapDataSource(hint_width=4)
    print(s.get_enclosures())
    s.debug()

    #s.write_config()
    s.load_config()

    s.debug()

def EnclosureTest():
    e = Enclosure("/sys/class/enclosure/6:0:15:0")
    e.debug("| \t")

if __name__ == "__main__":
    SlotMapDataSourceTest()
    #EnclosureTest()