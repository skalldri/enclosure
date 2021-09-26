import os
import os.path
import json

def get_norm_path(path):
    # Expand any environment variables
    path = os.path.expandvars(path)
    # Expand ~
    path = os.path.expanduser(path)
    # Remove any special chars like .. or double-slash
    path = os.path.normpath(path)
    return path

class Slot:
    ACTIVE_FILE = "active"
    FAULT_FILE = "fault"
    LOCATE_FILE = "locate"
    STATUS_FILE = "status"
    POWER_STATUS_FILE = "power_status"

    # Subfolder for device info
    DEVICE_FOLDER = "device"
    DEVICE_MODEL_FILE = "model"

    def __init__(self, slot_path):
        self.slot_path = get_norm_path(slot_path)
        print("Created slot for path {}".format(self.slot_path))

    def get_slot_path(self):
        return self.slot_path

    # Return true if the slot has a drive installed
    def has_drive(self):
        status_file = os.path.join(self.slot_path, self.STATUS_FILE)
        with open(status_file, 'r') as f:
            s = f.read()
            s = s.strip()
            if s == "not installed":
                return False

        return True

    def get_power_status(self):
        power_status_file = os.path.join(self.slot_path, self.POWER_STATUS_FILE)
        with open(power_status_file, 'r') as f:
            s = f.read()
            s = s.strip()
            if s == "on":
                return "ON"

        return "OFF"

    def get_drive_model(self):
        if not self.has_drive():
            return None

        drive_model_file = os.path.join(self.slot_path, self.DEVICE_FOLDER, self.DEVICE_MODEL_FILE)

        with open(drive_model_file, 'r') as f:
            s = f.read()
            s = s.strip()
            return s

        return None

    def get_led_state(self):
        return "OFF"

# Get information about the list of slots as well
# as the slot configurations from JSON config
class SlotMapDataSource:
    ENCLOSURE_PATH = "/sys/class/enclosure"
    COMPONENT_FILE = "components"
    ID_FILE = "id"

    CONFIG_DIR = "~/.config/server-dash"
    CONFIG_FILE = "enclosures.json"

    def guess_dims(self, slots, hint_width, hint_height):
        # If we got a hint_width, try to guess the number of rows
        if hint_width is not None:
            if slots % hint_width == 0:
                return (int(slots / hint_width), hint_width)

        # If we got a hint_height, try to guess the number of cols
        if hint_height is not None:
            if slots % hint_height == 0:
                return (hint_height, int(slots / hint_height))

        # If we got neither, just return (slots, 1)
        return (slots, 1)

    def __init__(self, hint_width=None, hint_height=None):
        # Start detecting enclosures
        if not os.path.exists(self.ENCLOSURE_PATH):
            raise RuntimeError("The path '{}' does not exist: do you have enclosures?".format(self.ENCLOSURE_PATH))

        if not os.path.isdir(self.ENCLOSURE_PATH):
            raise RuntimeError("The path '{}' is not a directory: do you have enclosures?".format(self.ENCLOSURE_PATH))

        # Get a list of subdirs in the folder: this represents the number of "enclosures" on this system, which will
        # translate to the number of panels
        self.enclosures = [x for x in os.listdir(self.ENCLOSURE_PATH) if os.path.isdir(os.path.join(self.ENCLOSURE_PATH, x))]
        self.enclosure_data = {}

        for enc in self.enclosures:
            self.enclosure_data[enc] = {}
            self.enclosure_data[enc]['full_path'] = os.path.join(self.ENCLOSURE_PATH, enc)
            self.enclosure_data[enc]['name'] = enc

            # Start with empty dimensions
            self.enclosure_data[enc]['slots'] = -1
            self.enclosure_data[enc]['dims'] = ()

            with open(os.path.join(self.enclosure_data[enc]['full_path'], self.COMPONENT_FILE)) as comp_file:
                components = comp_file.read()
                num_components = int(components.strip())
                self.enclosure_data[enc]['slots'] = num_components
                self.enclosure_data[enc]['dims'] = self.guess_dims(num_components, hint_width=hint_width, hint_height=hint_height)

            # Start with ID == enclosure folder
            self.enclosure_data[enc]['id'] = enc
            with open(os.path.join(self.enclosure_data[enc]['full_path'], self.ID_FILE)) as id_file:
                id = id_file.read()
                id = id.strip()
                self.enclosure_data[enc]['id'] = id

            # Load slots within this enclosure
            slot_folders = [x for x in os.listdir(self.enclosure_data[enc]['full_path']) if os.path.isdir(os.path.join(self.enclosure_data[enc]['full_path'], x)) and "Slot" in x]
            self.enclosure_data[enc]['slot_data'] = {}
            for s in slot_folders:
                slot_data = Slot(os.path.join(self.enclosure_data[enc]['full_path'], s))
                print(slot_data.get_power_status())
                print(slot_data.has_drive())
                print(slot_data.get_drive_model())
                self.enclosure_data[enc]['slot_data'][s] = slot_data

    
    # Get a list of "panels", which represents a planar grid of drives,
    # that can be enumerated by this data source
    def get_enclosures(self):
        return self.enclosures

    # Get the dimensions in (rows, columns) for a specific panel
    def get_dims(self, enclosure):
        return self.enclosure_data[enclosure]['dims']

    # Set the "friendly name" of an enclosure. Helpful for generating config
    def set_enclosure_name(self, enclosure, name):
        self.enclosure_data[enclosure]['name'] = name

     # Get the "friendly name" of an enclosure, used for tab titles
    def get_enclosure_name(self, enclosure):
        return self.enclosure_data[enclosure]['name']

    def get_slot(self, enclosure, row, col):
        # TODO: need a better way to map slot co-ordinates to slot folder names
        rows, cols = self.enclosure_data[enclosure]['dims']
        slot_index = ((row * cols) + col) + 1
        slot_name = "Slot {0:02d}".format(slot_index)
        return self.enclosure_data[enclosure]['slot_data'][slot_name]

    # Write config to the default location
    def write_config(self):
        norm_config_dir = get_norm_path(self.CONFIG_DIR)
        # Ensure default location exists
        os.makedirs(norm_config_dir, exist_ok=True)
        self.write_json(os.path.join(norm_config_dir, self.CONFIG_FILE))

    # Write config data to a JSON file
    def write_json(self, json_file):
        json_config_data = []
        for enc in self.enclosure_data:
            config_data = {}
            config_data['name'] = self.enclosure_data[enc]['name']
            config_data['id'] = self.enclosure_data[enc]['id']
            rows, cols = self.enclosure_data[enc]['dims']
            config_data['width'] = cols
            config_data['height'] = rows
            config_data['slots'] = self.enclosure_data[enc]['slots']

            json_config_data.append(config_data)

        json_str = json.dumps(json_config_data)
        norm_path = get_norm_path(json_file)
        print("Writing to {}".format(norm_path))

        with open(norm_path, 'w') as f:
            f.write(json_str)

    # Write config to the default location
    def load_config(self):
        norm_config_dir = get_norm_path(self.CONFIG_DIR)
        config_file = os.path.join(norm_config_dir, self.CONFIG_FILE)
        # Check if config exists
        if not os.path.exists(config_file):
            print("Cannot load config from {}, file does not exist".format(config_file))

        if not os.path.isfile(config_file):
            print("Cannot load config from {}, path is not a file".format(config_file))

        self.load_json(config_file)

    # Get the key of an enclosure by searching through self.enclosure_data and finding
    # an entry with an id that matches the provided id, then return the key
    def find_enclosure_by_id(self, id):
        for enc in self.enclosure_data:
            if self.enclosure_data[enc]['id'] == id:
                return enc
        return None

    # Load user config data from a json file
    def load_json(self, json_file):
        json_config_data = []
        
        norm_path = get_norm_path(json_file)
        print("Reading config from {}".format(norm_path))

        with open(norm_path, 'r') as f:
            json_string = f.read()
            json_config_data = json.loads(json_string)
        
        for enclosure_config in json_config_data:
            print(enclosure_config)
            enc = self.find_enclosure_by_id(enclosure_config['id'])

            if enc is None:
                print("ERROR: Configuration entry '{}' does not match any discovered enclosures".format(enclosure_config))
                continue

            # Sanity check... does the number of slots match?
            if enclosure_config['slots'] != self.enclosure_data[enc]['slots']:
                print("ERROR: Configuration entry for enclosure {} specifies {} slots, but filesystem scan detected {} slots.".format(enc, enclosure_config['slots'], self.enclosure_data[enc]['slots']))
                continue

            # Sanity check... does width * height == slots?
            if (enclosure_config['width'] * enclosure_config['height']) != enclosure_config['slots']:
                print("ERROR: Configuration entry for enclosure {} specifies dimensions {}x{}, but this does not equal {} slots", enc, enclosure_config['width'], enclosure_config['height'], enclosure_config['slots'])
                continue

            # Seems to be a match: apply JSON config to the data source
            self.enclosure_data[enc]['name'] = enclosure_config['name']
            self.enclosure_data[enc]['dims'] = (enclosure_config['height'], enclosure_config['width'])

    def debug(self):
        for enc in self.enclosure_data:
            print("Found Enclosure: {}".format(enc))
            print("Enclosure Data: {}".format(self.enclosure_data[enc]))