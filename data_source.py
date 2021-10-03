import os
import os.path
import json
from typing import Dict
from enum import Enum
import math

def get_norm_path(path):
    # Expand any environment variables
    path = os.path.expandvars(path)
    # Expand ~
    path = os.path.expanduser(path)
    # Remove any special chars like .. or double-slash
    path = os.path.normpath(path)
    return path

class LEDState(Enum):
    OFF = 0
    LOCATE = 1
    FAULT = 2

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

    def _get_state(self, file):
        with open(file, 'r') as f:
            state = f.read()
            int_state = int(state)
            if int_state == 0:
                return False
            else:
                return True

    def _set_state(self, file, state):
        with open(file, 'w') as f:
            f.write(state)

    def set_led_state(self, state : LEDState):
        locate_file = os.path.join(self.slot_path, self.LOCATE_FILE)
        fault_file = os.path.join(self.slot_path, self.FAULT_FILE)

        locate_state = self._get_state(locate_file)
        fault_state = self._get_state(fault_file)

        if state == LEDState.OFF:
            if locate_state == True:
                self._set_state(locate_file, "0")
            if fault_state == True:
                self._set_state(fault_file, "0")
        elif state == LEDState.LOCATE:
            if locate_state == False:
                self._set_state(locate_file, "1")
            if fault_state == True:
                self._set_state(fault_file, "0")
        elif state == LEDState.FAULT:
            if locate_state == True:
                self._set_state(locate_file, "0")
            if fault_state == False:
                self._set_state(fault_file, "1")

    def get_led_state(self):
        locate_file = os.path.join(self.slot_path, self.LOCATE_FILE)
        fault_file = os.path.join(self.slot_path, self.FAULT_FILE)

        locate_state = self._get_state(locate_file)
        fault_state = self._get_state(fault_file)

        if locate_state == True and fault_state == True:
            return "LOCATE & FAULT"
        elif locate_state == True:
            return "LOCATE"
        elif fault_state == True:
            return "FAULT"
        else:
            return "OFF"
    
    # TODO: implement these (if possible?)
    def get_drive_serial_number(self):
        return "01234567"

    def get_drive_device_path(self):
        return "/dev/sda"

    def is_in_zfs_pool(self):
        return False

    def get_zfs_pool_membership(self):
        return "tank"

    def debug(self, prefix = ""):
        print("{}{}".format(prefix, os.path.basename(self.slot_path)))
        print("{}\tHas Drive: {}".format(prefix, self.has_drive()))
        print("{}\tPower Status: {}".format(prefix, self.get_power_status()))
        print("{}\tLED State: {}".format(prefix, self.get_led_state()))
        print("{}\tDrive Model: {}".format(prefix, self.get_drive_model()))
        print("{}\tDrive Serial Number: {}".format(prefix, self.get_drive_serial_number()))
        print("{}\tDrive Device: {}".format(prefix, self.get_drive_device_path()))
        print("{}\tIs In ZFS Pool: {}".format(prefix, self.is_in_zfs_pool()))
        print("{}\tZFS Pool Membership: {}".format(prefix, self.get_zfs_pool_membership()))


class Enclosure:
    ID_FILE = "id"
    COMPONENT_FILE = "components"

    # TODO: add getters / setters
    def __init__(self, path):
        self.full_path = "" # The path on the filesystem to the enclosure folder. Generally /sys/class/enclosure/XXXXXXXX
        self.dims = (0, 0)
        self.id = "" # A unique ID used to track this enclosure through reboots
        self.name = "" # The friendly-name of the enclosure
        self.slots = 0 # The number of slots in the enclosure
        self.dims = (0, 0) # The rows, cols in this enclosure. rows * cols must equal slots

        # Verify if this is a sane enclosure path
        path = get_norm_path(path)
        if not os.path.isdir(path):
            raise RuntimeError("Enclosure path '{}' is not a directory".format(path))

        self.full_path = path

        # Initialize name to the folder of this enclosure
        self.name = os.path.basename(self.full_path)

        # We expect the enclosure folder to contain a file called "components". This tells us how many slots 
        # are in this enclosure
        with open(os.path.join(self.full_path, self.COMPONENT_FILE)) as comp_file:
            components = comp_file.read()
            num_components = int(components.strip())
            self.slots = num_components
            self.dims = self.guess_dims(num_components)

        with open(os.path.join(self.full_path, self.ID_FILE)) as id_file:
            id = id_file.read()
            id = id.strip()
            self.id = id

        # Load slots within this enclosure
        slot_folders = [x for x in os.listdir(self.full_path) if os.path.isdir(os.path.join(self.full_path, x)) and "Slot" in x]
        self.slot_data = {}
        for s in slot_folders:
            slot_data = Slot(os.path.join(self.full_path, s))
            self.slot_data[s] = slot_data

        # this dict maps the "physical" index to a "logical" index.
        # a "physical" index is derived from a slot's physical location on the grid:
        # a "physical" index == ((slot_row * enclosure_columns) + slot_col)
        # a "logical" index is whatever index Linux decided to assign to each slot
        # "logical" indexes always start at 1
        # The default mapping just maps "physical index" -> "physical index" + 1
        self.slot_mapping = {}
        for i in range(self.slots):
            self.slot_mapping[i] = self._get_logical_index(i+1)

    def _get_slot_location(self, physical_index):
        rows, cols = self.dims
        row = math.floor(physical_index / cols)
        col = (physical_index - (row * cols))
        return (row, col)
    
    def _get_physical_index(self, row, col):
        rows, cols = self.dims
        physical_index = ((row * cols) + col)
        return physical_index

    # Return a string version of the slot logical index
    def _get_logical_index(self, i):
        return "Slot {0:02d}".format(i)

    def guess_dims(self, slots, hint_width = None, hint_height = None):
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

    # returns a Slot object at the given row / column index
    # if a slot-map is available from the configuration file, that is used.
    # otherwise, the default mapping is a 1:1 mapping between row / column and slot folder name
    def get_slot(self, row, col):
        physical_index = self._get_physical_index(row, col)
        slot_name = self.slot_mapping[physical_index]
        return self.slot_data[slot_name]

    # Return a Dict representing this enclosure, can be used to generate a JSON
    # for storage in a config file
    def to_dict(self):
        json_object = {}
        json_object['name'] = self.name
        json_object['id'] = self.id
        json_object['height'] = self.dims[0]
        json_object['width'] = self.dims[1]
        json_object['slots'] = self.slots
        json_object['slot_mapping'] = self.slot_mapping

        return json_object

    # Initialize enclosure using already-decoded JSON object data.
    # We expect pre-decoded JSON data since this is normally stored as a list of Enclosures in the config file
    def from_dict(self, json_object : Dict):
        # Sanity check... does the number of slots match ours?
        if json_object['slots'] != self.slots:
            raise RuntimeError("Tried to load config for enclosure {}. Config specifies {} slots, but filesystem scan detected {} slots.".format(self.name, json_object['slots'], self.slots))

        # Sanity check... does width * height == slots?
        if (json_object['width'] * json_object['height']) != json_object['slots']:
            raise RuntimeError("Tried to load config for enclosure {}. Config specifies dimensions {}x{}, but this does not equal {} slots", self.name, json_object['width'], json_object['height'], json_object['slots'])

        # Seems to be a match: apply JSON config to the data source
        self.name = json_object['name']
        self.dims = (json_object['height'], json_object['width'])

        for s in json_object['slot_mapping']:
            s_int = int(s)
            self.slot_mapping[s_int] = json_object['slot_mapping'][s]

    def debug(self, prefix = ""):
        print("{}Enclosure: {}".format(prefix, self.name))
        print("{}\tFull Path: {}".format(prefix, self.full_path))
        print("{}\tSlots: {}".format(prefix, self.slots))
        print("{}\tDims: {}x{}".format(prefix, self.dims[0], self.dims[1]))
        print("{}\tID: {}".format(prefix, self.id))

        print("{}\tSlot Mapping:".format(prefix))
        # slot_mapping keys are physical_indexes
        for physical_index in self.slot_mapping:
            loc = self._get_slot_location(physical_index)
            print("{}\t\t({}, {}) -> {}".format(prefix, loc[0], loc[1], self.slot_mapping[physical_index]))

        for slot in self.slot_data:
            self.slot_data[slot].debug("{}\t".format(prefix))


# Get information about the list of slots as well
# as the slot configurations from JSON config
class SlotMapDataSource:
    ENCLOSURE_PATH = "/sys/class/enclosure"

    CONFIG_DIR = "~/.config/server-dash"
    CONFIG_FILE = "enclosures.json"

    def __init__(self, hint_width=None, hint_height=None):
        # Start detecting enclosures
        if not os.path.isdir(self.ENCLOSURE_PATH):
            raise RuntimeError("The path '{}' is not a directory: do you have enclosures?".format(self.ENCLOSURE_PATH))

        # Get a list of subdirs in the folder: this represents the number of "enclosures" on this system, which will
        # translate to the number of panels
        self.enclosures = [x for x in os.listdir(self.ENCLOSURE_PATH) if os.path.isdir(os.path.join(self.ENCLOSURE_PATH, x))]
        self.enclosure_data = {}

        for enc in self.enclosures:
            self.enclosure_data[enc] = {}
            enclosure_path = os.path.join(self.ENCLOSURE_PATH, enc)
            self.enclosure_data[enc] = Enclosure(enclosure_path)
    
    # Get a list of "panels", which represents a planar grid of drives,
    # that can be enumerated by this data source
    def get_enclosures(self):
        return self.enclosures

    # Get the dimensions in (rows, columns) for a specific panel
    def get_dims(self, enclosure):
        return self.enclosure_data[enclosure].dims

    # Set the "friendly name" of an enclosure. Helpful for generating config
    def set_enclosure_name(self, enclosure, name):
        self.enclosure_data[enclosure].name = name

     # Get the "friendly name" of an enclosure, used for tab titles
    def get_enclosure_name(self, enclosure):
        return self.enclosure_data[enclosure].name

    def get_slot(self, enclosure, row, col):
        # TODO: need a better way to map slot co-ordinates to slot folder names
        # rows, cols = self.enclosure_data[enclosure].dims
        # slot_index = ((row * cols) + col) + 1
        # slot_name = "Slot {0:02d}".format(slot_index)
        # return self.enclosure_data[enclosure].slot_data[slot_name]
        
        return self.enclosure_data[enclosure].get_slot(row, col)

    # Write config to the default location
    def write_config(self, config_file = None):
        if config_file is None:
            norm_config_dir = get_norm_path(self.CONFIG_DIR)
            config_file = os.path.join(norm_config_dir, self.CONFIG_FILE)
        else:
            config_file = get_norm_path(config_file)
        
        # Ensure default location exists
        os.makedirs(norm_config_dir, exist_ok=True)
        self.write_json(config_file)

    # Write config data to a JSON file
    def write_json(self, json_file):
        json_config_data = []
        for enc in self.enclosure_data:
            json_config_data.append(self.enclosure_data[enc].to_dict())

        json_str = json.dumps(json_config_data)
        norm_path = get_norm_path(json_file)
        print("Writing to {}".format(norm_path))

        with open(norm_path, 'w') as f:
            f.write(json_str)

    # Write config to the default location
    def load_config(self, config_file = None):
        if config_file is None:
            norm_config_dir = get_norm_path(self.CONFIG_DIR)
            config_file = os.path.join(norm_config_dir, self.CONFIG_FILE)
        else:
            config_file = get_norm_path(config_file)
        
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
            if self.enclosure_data[enc].id == id:
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

            self.enclosure_data[enc].from_dict(enclosure_config)

    def debug(self, prefix = ""):
        for enc in self.enclosure_data:
            self.enclosure_data[enc].debug(prefix)