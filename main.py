import urwid
from tabbed_pane import TabbedPane
from data_source import LEDState, SlotMapDataSource
from slots_pane import SlotInfoPane, SlotsMapPane
import os
import os.path
import argparse
import math
import time

def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()
    elif key in ('t', 'T'):
        pass


def parse_args():
    parser = argparse.ArgumentParser(description='Hard Drive Enclosure Management')
    parser.add_argument('--configure', action='store_true',
                        help='run the interactive configuration management generator', default=False)

    return parser.parse_args()

# Ask the user a question, get confirmation on the answer
def _question(question):
    while True:
        ans = input("{}: ".format(question))
        print("I got: '{}'".format(ans))
        user_choice = _confirm("Is this correct")
        if user_choice == "Y":
            break
    return ans

# Ask the user to confirm something. Returns "Y" or "N"
def _confirm(prompt):
    while True:
        user_choice = input("{}? (Y / N): ".format(prompt))
        user_choice = user_choice.upper()
        if user_choice == "N" or user_choice == "Y":
            break
        else:
            print("Only enter Y or N")
    return user_choice

def configure():
    source = SlotMapDataSource()
    enclosures = source.get_enclosures()

    print("Found {} enclosures".format(len(enclosures)))
    
    for e in enclosures:
        enc = source.get_enclosure(e)
        print("Configure enclosure {}".format(enc.name))
        print("Enclosure {} has {} slots".format(enc.name, enc.slots))
        
        light_up_panel = _confirm("Illuminate LEDs on all slots to assist identification")

        if light_up_panel == "Y":
            for i in range(enc.slots):
                s = enc.get_slot(i)
                s.set_led_state(LEDState.LOCATE)
            while True:
                user_input = _confirm("Have you identified this enclosure")
                if user_input == "Y":
                    break
                else:
                    print("Keep looking then...")
            for i in range(enc.slots):
                s = enc.get_slot(i)
                s.set_led_state(LEDState.OFF)
        else:
            print("Skipping slot illumination")

        enc.name = _question("Enter a name for this enclosure")

        while True:
            width = _question("Enter the physical width of this enclosure")
            width = int(width)
            height = math.floor(enc.slots / width)
            print("Width of {} implies a height of {}".format(width, height))
            if width * height != enc.slots:
                print("Width of {} and height of {} does not match number of slots {}".format(width, height, enc.slots))
                print("Please enter a valid width, to match {} slots".format(enc.slots))
            else:
                break

        enc.dims = (height, width)

        while True:
            orig_slot_map = enc.slot_mapping
            print("Current Slot Mapping:")
            # slot_mapping keys are physical_indexes
            for physical_index in orig_slot_map:
                loc = enc._get_slot_location(physical_index)
                print("\t({}, {}) -> {}".format(loc[0], loc[1], orig_slot_map[physical_index]))
        
            new_slot_map = {}
            # Light up each physical slot one by one, building up a new slot map.
            # At each step, the user will be asked to confirm if the slot lit up makes sense.
            # if not, they will enter a new (row, col)
            for physical_index in orig_slot_map:
                row, col = enc._get_slot_location(physical_index)
                slot = enc.get_slot(physical_index)
                slot.set_led_state(LEDState.LOCATE)
                print("Physical Index: {}".format(physical_index))
                print("The Slot at (row, col) ({}, {}) should be blinking".format(row, col))
                user_input = _confirm("Is the correct slot blinking")
                if user_input == "Y":
                    # Current mapping is correct
                    new_slot_map[physical_index] = orig_slot_map[physical_index]
                else:
                    while True:
                        ans = _question("Enter coordinates as 'row col'")
                        ans = ans.split(" ")
                        if len(ans) != 2:
                            print("Answer in the format 'row col'")
                            continue
                        try:
                            row = int(ans[0])
                            col = int(ans[1])
                        except:
                            continue

                        break

                    new_phy_index = enc._get_physical_index(row, col)
                    print("Correct slot is ({}, {})".format(row, col))
                    print("Correct Physical Index is {}".format(new_phy_index))
                    new_slot_map[new_phy_index] = orig_slot_map[physical_index]

                slot.set_led_state(LEDState.OFF)

            print("New Slot Mapping:")
            # slot_mapping keys are physical_indexes
            for physical_index in new_slot_map:
                loc = enc._get_slot_location(physical_index)
                print("\t({}, {}) -> {}".format(loc[0], loc[1], new_slot_map[physical_index]))

            user_input = _confirm("Apply this mapping")
            if user_input == "Y":
                enc.slot_mapping = new_slot_map
            else:
                continue

            print("All slots should now light up in sequence")

            for physical_index in range(enc.slots):
                slot = enc.get_slot(physical_index)
                slot.set_led_state(LEDState.LOCATE)
                time.sleep(0.2)
                slot.set_led_state(LEDState.OFF)
            
            user_input = _confirm("Did the slots light up in sequence")
            if user_input == "Y":
                break
            else:
                print("Try configuration again")
                enc.slot_mapping = orig_slot_map
    
    print("Final Configuration Check")
    for e in enclosures:
        enc = source.get_enclosure(e)
        enc.debug()

    user_input = _confirm("Is this configuration correct")
    if user_input == "Y":
        source.write_config("./enclosure.json")
        print("To use this configuration, copy to ~/.config/server-dash/enclosure.json")


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

    palette = [
        # Palette description format
        # (name, foreground_settings, background_Settings, [mono], [foreground_high], [background_high])
        ('reversed', 'standout', ''),
        ('slot_filled', 'white', 'dark green'),
        ('slot_filled_highlighted', 'white', 'dark green'),
        ('slot_empty', '', ''),
        ('slot_empty_highlighted', 'standout', ''),
    ]

    loop = urwid.MainLoop(column, palette=palette, unhandled_input=exit_on_q)
    loop.run()

if __name__ == "__main__":
    args = parse_args()
    if args.configure == True:
        configure()
    else:
        main()
