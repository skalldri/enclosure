#!/usr/bin/python3

from data_source import SlotMapDataSource, Enclosure, Slot, LEDState

def SlotMapDataSourceTest():
    s = SlotMapDataSource(hint_width=4)
    print(s.get_enclosures())
    s.debug()

    s.load_config("/home/salldritt/.config/server-dash/enclosures.json")
    #s.write_config()
    #s.load_config("/home/salldritt/.config/server-dash/enclosures.json")

    s.debug()

    #s.get_slot("6:0:15:0", 5, 1).set_led_state(LEDState.LOCATE)
    s.get_slot("6:0:15:0", 5, 1).debug()
    #s.get_slot("6:0:15:0", 5, 1).set_led_state(LEDState.OFF)
    s.get_slot("6:0:15:0", 5, 1).debug()

def EnclosureTest():
    e = Enclosure("/sys/class/enclosure/6:0:15:0")
    e.debug("| \t")

if __name__ == "__main__":
    SlotMapDataSourceTest()
    #EnclosureTest()