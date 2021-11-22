import urwid

class SlotInfoPane(urwid.WidgetWrap):
    def __init__(self, data_source):
        
        slot_id = "XX"

        self.data_source = data_source

        # Text we want to display in the pane
        self.led_state = urwid.Text("LED State: ")
        self.drive_model = urwid.Text("Drive Model: ")
        self.enclosure_path = urwid.Text("Enclosure Path: ")
        info_list = []
        info_list.append(self.led_state)
        info_list.append(urwid.Divider())
        info_list.append(self.drive_model)
        info_list.append(urwid.Divider())
        info_list.append(self.enclosure_path)

        self.info_area = urwid.Filler(urwid.Pile(widget_list=info_list))
        self.lined_info_area = urwid.LineBox(self.info_area)

        # Generate a frame that has a header and footer
        self.header = urwid.Text("Slot Info: ")
        self.footer = urwid.Text("State: ")
        self.frame = urwid.Frame(self.lined_info_area, header=self.header, footer=self.footer)
        super(SlotInfoPane, self).__init__(self.frame)

    def pick_slot(self, enclosure, slot_id):
        row, col = slot_id
        slot_data = self.data_source.get_slot(enclosure, row, col)
        has_drive = slot_data.has_drive()

        self.led_state.set_text("LED State: {}".format(slot_data.get_led_state()))
        self.drive_model.set_text("Drive Model: {}".format(slot_data.get_drive_model()))
        self.header.set_text("Slot Info: {} - {}".format(self.data_source.get_enclosure_name(enclosure), slot_id))
        self.footer.set_text("State: {}".format("INSTALLED" if has_drive else "NOT INSTALLED"))
        self.enclosure_path.set_text("Enclosure Path: {}".format(slot_data.get_slot_path()))

class SlotsMapPane(urwid.WidgetWrap):
    def on_slot_press(self, button, user_data=None):
        if self.info_pane is not None:
            self.info_pane.pick_slot(self.enclosure, user_data)

    def __init__(self, data_source, enclosure, info_pane=None):
        self.data_source = data_source
        self.enclosure = enclosure
        self.info_pane = info_pane

        rows, cols = self.data_source.get_dims(self.enclosure)

        # List of widgets representing a single row of the
        # drive array
        drive_rows = []
        for r in range(rows):
            # List to keep track of all widgets in the current row
            current_row_widgets = []
            for c in range(cols):
                # Create a button
                slot_button = urwid.Button("[ {} -- {} ]".format(r, c), self.on_slot_press, (r, c))

                if self.data_source.get_slot(enclosure, r, c).has_drive():
                    # Wrap the button in an AttrMap so that when the button is focused it uses the 'reversed' Display Attribute
                    slot_button_wrapped = urwid.AttrMap(slot_button, attr_map='slot_filled', focus_map='slot_filled_highlighted')
                else:
                    # Wrap the button in an AttrMap so that when the button is focused it uses the 'reversed' Display Attribute
                    slot_button_wrapped = urwid.AttrMap(slot_button, attr_map='slot_empty', focus_map='slot_empty_highlighted')
                
                current_row_widgets.append((14, slot_button_wrapped))
                
            
            # Make a "Columns" widget out of all the widgets in the current row
            # This concatenates all widgets into a single entity
            current_row = urwid.Columns(current_row_widgets, dividechars=2)

            # Append the current row to the list of rows
            drive_rows.append(current_row)

        # Make the pile of rows
        self.interior = urwid.Filler(urwid.Pile(drive_rows))
        super(SlotsMapPane, self).__init__(self.interior)