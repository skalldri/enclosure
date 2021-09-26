import urwid
import os

# Simple button wrapper class that supports packing based on the label length
class TabbedPaneTabButton(urwid.WidgetWrap):
    def __init__(self, label, on_press=None, user_data=None):
        self.label = label
        self.button = urwid.Button(label, on_press=on_press, user_data=user_data)
        self.attr_map = urwid.AttrMap(self.button, None, focus_map='reversed')
        super(TabbedPaneTabButton, self).__init__(self.attr_map)

    def pack(self, size, focus=False):
        return (len(self.label) + 4, )

class TabbedPane(urwid.WidgetWrap):

    def keypress(self, size, key):
        # If the header is currently focused and we press "down", then make the Body the focus. 
        # The Body needs to return focus to us when it can't handle an "up" event
        if key == 'down' and self.frame.focus_position == 'header':
            self.frame.focus_position = 'body'
            # Return None to indicate we handled this keypress event
            return None
        # If the body is currently in focus and we get an 'up' event,
        # first give the body a chance to handle the event.
        # If it doesn't get handled, move focus back up to the header
        elif key == 'up' and self.frame.focus_position == 'body':
            body_widget, options = self.frame.contents['body']
            try:
                handled = body_widget.keypress(size, key)

                # If handled == key, then the body did not handle the keypress
                # and we should return focus to the header
                if handled == key:
                    self.frame.focus_position = 'header'
                    return None
            
                # Else, just bubble status up
                return handled
            except:
                # Exception occurred. The current Body likely can't handle keypresses at all,
                # so go back up to the header
                self.frame.focus_position = 'header'
                return None
        # Default case: pass keypress into the currently focused element
        else:
            current_widget, options = self.frame.contents[self.frame.focus_position]
            try:
                return current_widget.keypress(size, key)
            except:
                # Exception occurred. The current widget likely can't handle keypresses at all,
                # so return key to indicate we didn't handle this keypress
                return key

        return key

    def change_tab(self, title):
        # Change the body to a different widget
        self.frame.contents['body'] = (self.tab_widgets[title], self.frame.options())

    def on_tab_click(self, button, data=None):
        self.change_tab(data)

    def __init__(self, tabs = []):
        
        self.header_buttons = []
        self.tab_widgets = {}
        
        # Create buttons for each tab title, store widgets in a dict for later use
        for title, widget in tabs:
            self.header_buttons.append(TabbedPaneTabButton(title, on_press=self.on_tab_click, user_data=title))
            self.tab_widgets[title] = urwid.LineBox(widget)
        
        # Create a divider for the header buttons
        self.header = urwid.Columns((('pack', x) for x in self.header_buttons), dividechars=2)
        
        sysname, nodename, release, version, machine = os.uname()

        self.footer = urwid.Text("{}, {} - {}  | q = Quit".format(nodename, sysname, release))
        self.blank_placeholder = urwid.SolidFill(' ')
        self.frame = urwid.Frame(self.blank_placeholder, header=self.header, footer=self.footer, focus_part='header')

        self.change_tab(self.header.focus.label)

        super(TabbedPane, self).__init__(self.frame)
        return