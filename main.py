import urwid
from tabbed_pane import TabbedPane
from data_source import SlotMapDataSource
from slots_pane import SlotInfoPane, SlotsMapPane
import os
import os.path

def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()
    elif key in ('t', 'T'):
        pass

# Desired application layout:
#  ______________________________________________________________
# |                                     |                       |
# |                                     |                       |
# |                                     |                       |
# |        ENCLOSURE TABS               |         CURRENT       |
# |                                     |          SLOT         |
# |                                     |          INFO         |
# |                                     |                       |
# ---------------------------------------------------------------

def main():
    # Data source for slot information
    slot_data = SlotMapDataSource()
    
    # Load user config json, if any
    slot_data.load_config()

    # Create a panel to show information about the currently selected slot
    info_pane = SlotInfoPane(data_source=slot_data)

    # List of all tabs, one tab per enclosure
    tabs = []

    for e in slot_data.get_enclosures():
        pane = SlotsMapPane(data_source=slot_data, enclosure=e, info_pane=info_pane)
        tabs.append((slot_data.get_enclosure_name(e), pane))
    
    # The left half of the application window will be a tabbed panel that has the front and rear 
    # widgets selectable from the top tab
    left_pane = TabbedPane(tabs=tabs)
    column = urwid.Columns([('weight', 0.6, left_pane), ('weight', 0.4, info_pane)], dividechars=1)

    loop = urwid.MainLoop(column, palette=[('reversed', 'standout', '')], unhandled_input=exit_on_q)
    loop.run()

if __name__ == "__main__":
    main()
