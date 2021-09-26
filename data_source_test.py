from data_source import SlotMapDataSource

s = SlotMapDataSource(hint_width=4)
print(s.get_enclosures())
s.debug()

#s.write_config()
s.load_config()

s.debug()