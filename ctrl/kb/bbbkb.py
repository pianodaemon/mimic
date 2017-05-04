from ctrl.gen import KbGen
from ctrl.gen import KbHwError
from ctrl.gen import KbSeqError, KbKeyError
from multiprocessing import Process
from time import sleep

import struct
import time
import logging
import os

impt_class='BBBKb'

class BBBKb(KbGen):
    '''
    Keyboard emulator class which has methods for sending key strokes through
    usb port using Linux g_hid module.
    '''

    __DEFAULT_PORT = "/dev/hidg0"

    # HID keyboard hex codes for modifier keys
    __MODIFIER_CODES = {
        "CONTROL_L":  0x01, "SHIFT_L":    0x02, "ALT_L":            0x04,
        "SUPER_L":    0x08, "MULTI":      0x08, "CONTROL_R":        0x10,
        "SHIFT_R":    0x20, "MENU":       0x80, "ISO_LEVEL3_SHIFT": 0x40,
    }

    # HID keyboard hex codes for specific keys
    __KEY_CODES = {
        # Function keys
        'F1': 0x3A,  'F2': 0x3B,  'F3': 0x3C,  'F4': 0x3D,
        'F5': 0x3E,  'F6': 0x3F,  'F7': 0x40,  'F8': 0x41,
        'F9': 0x42, 'F10': 0x43, 'F11': 0x44, 'F12': 0x45,

        # Symbols above the row of numbers
        '!':  0x1E, '@':  0x1F, '#':  0x20, '$':  0x21, '%':  0x22, '^':  0x23,
        '&':  0x24, '*':  0x25, '(':  0x26, ')':  0x27,

        # Row of numbers
        '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22,
        '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,

        # Navigation/Editing
        'INSERT': 0x49, 'HOME': 0x4A, 'PRIOR': 0x4B,
        'DELETE': 0x4C, 'END':  0x4D, 'NEXT':  0x4E,

        'ENTER': 0x28, 'ESCAPE': 0x29, 'BACKSPACE': 0x2A,
        'TAB':    0x2B, ' ':  0x2C,

        # Miscellaneous Symbols - grouped by key (one per row)
        '-': 0x2D, '_':  0x2D,
        '=': 0x2E, '+':  0x2E,
        '[': 0x2F, '{':  0x2F,
        ']': 0x30, '}':  0x30,
        '\\':0x31, "|":  0x31,
        ';': 0x33, ':':  0x33,
        "'": 0x34, '"':  0x34,
        '`': 0x35, '~':  0x35,
        ',': 0x36, '<':  0x36,
        '.': 0x37, '>':  0x37,
        '/': 0x38, '?':  0x38,

        #Arrow Keys
        'RIGHT': 0x4f, 'LEFT': 0x50, 'DOWN': 0x51, 'UP': 0x52,
    }

    # Some keys use the same hex code for example '1' and '!'. To get '!', SHIFT
    # modifier has to be used. This list contains these keys that need SHIFT.
    __KEYS_WITH_SHIFT = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_',
                       '+', '{', '}', '|', ':', '"', '~', '<', '>', '?']


    def __init__(self, logger, *args, **kwargs):
        super().__init__(logger)
        self.emulator = kwargs.get('pem_port', self.__DEFAULT_PORT) # Initialize path to HID keyboard emulator
        self.filepath = "" # Initialize filepath for send_keystrokes_from_file()
        self.delays = 0 # Delay (seconds) between keystrokes
        self.modifier = 0 # On default don't use modifier key
        self.line_number = 0 # Line number we are parsing from filepath

    def open(self):
        pass

    def release(self):
        pass

    def perform(self, filepath):
        '''
        Send keystrokes from a file to USB.

        Args:
            filepath: Path to the text file that contains keystrokes to send.

        The text file needs to have special syntax. Example:

            # These lines are comments
            # Set delay between keystrokes with 'DELAY' at the start of a line
            DELAY = 0.1
            # Send text by using ""
            "Hello world!"
            # Sending " is done by \"
            "\"Hello world!\""
            # Send special keys with < >
            <F2> <ENTER> <ESCAPE>
            # Use modifiers with < >, modifiers can have start and end
            <SHIFT_R> "hello world1" <SHIFT_R>
            # Spaces outside of "" and <> will be ignored
                   "This and the enter key will be sent to usb"    <ENTER>
            # Newlines are ignored

            # Everything else outside of "" and <> will raise an error
            this text will raise an error
            # Mix everything, but have a separate line for 'DELAY='
            DELAY=0.2
            <F2> "Hello world!" <ENTER> <SHIFT_L> "uppercase" <SHIFT_L>

        '''

        self.delays = 0
        self.modifier = 0
        self.filepath = filepath

        with open(filepath, "r") as f:
            self.line_number = 1
            for line in f:
                line = line.strip()
                if line:
                    self.__parse_line(line)
                self.line_number += 1


    def __parse_line(self, line):
        '''
        Parse a text file line.

        Args:
            line: Line from a text file.
        '''
        # If line starts with 'DELAY' set the delay
        if line[0:5] == "DELAY":
            try:
                self.delays = float(line.split('=')[1].strip())
            except ValueError:
                raise KbSeqError(
                        "Error in file " + os.path.abspath(self.filepath) +
                        " on line " + str(self.line_number) + ": " +
                        "'" + line[6:].strip() + "' not a number")
        else:
            # Parse lines keys one at a time
            i = 0
            while i < len(line):
                key = line[i]

                # If key is "<" parse special key
                if key == "<":
                    i = self.__parse_special(line, i)

                # If key is " start parsing text
                elif key == "\"":
                    i = self.__parse_text(line, i)

                # If key is '#' ignore rest of the line
                elif key == "#":
                    return 0

                # If key is ' ', just ignore it
                elif key == " ":
                    pass

                # If key is anything else raise error
                else:
                    raise KbSeqError(
                            "Error in file " + os.path.abspath(self.filepath) + 
                            " on line " + str(self.line_number) + ": " +
                            "Found '" + key + "' outside of <> and \"\"")
                i += 1

    def __parse_special(self, line, i):
        '''
        Parse a special key that starts with '<' and ends with '>'.

        Args:
            line: Line from a text file that contains a special key.
            i: Iterator for the line that tells where the special key starts.

        Returns:
            i: Iterator for the line that tells where the special key ends.
        '''

        i += 1
        special = ""
        try:
            # Add letters to 'special' until '>' is found
            while line[i] != ">":
                special += line[i]
                i += 1
        except IndexError:
            raise KbSeqError(
                "Error in file " + os.path.abspath(self.filepath) +
                " on line " + str(self.line_number) + ": " +
                "Didn't find closing '>'")

        # If the special key is a modifier, toggle it
        if special in self.__MODIFIER_CODES:
            if self.__MODIFIER_CODES[special] == self.modifier:
                self.modifier = 0
            else:
                self.modifier = self.__MODIFIER_CODES[special]

        # If special key is a normal key, send it
        else:
            self.__send_a_key(special)
            sleep(self.delays)

        return i

    def __parse_text(self, line, i):
        '''
        Parse text that starts and ends with ".

        Args:
            line: Line from a text file that contains "".
            i: Iterator for the line that tells where the starting " is.

        Returns:
            i: Iterator for the line that tells where the ending " is.
        '''
        i += 1
        try:
            # Send keys until " is found.
            while line[i] != "\"":
                key = line[i]
                # Allow sending ", by using '\'
                if key == "\\":
                    i += 1
                    key = line[i]

                self.__send_a_key(key)
                sleep(self.delays)
                i += 1

        except IndexError:
            raise KbSeqError(
                "Error in file " + os.path.abspath(self.filepath) +
                " on line " + str(self.line_number) + ": " +
                "Didn't find closing \"")
        return i

    def __send_a_key(self, key, timeout=20):
        '''
        HID keyboard message length is 8 bytes and format is:

            [modifier, reserved, Key1, Key2, Key3, Key4, Key6, Key7]

        So first byte is for modifier key and all bytes after third one are for
        normal keys. After sending a key stroke, empty message with zeroes has
        to be sent to stop the key being pressed. Messages are sent by writing
        to the emulated HID usb port in /dev/. US HID keyboard hex codes
        are used for translating keys.

        Args:
            key: A key to send, for example: "a", "z", "3", "F2", "ENTER"
            timeout: how long sending a key will be tried until quitting [s]
        '''
        def writer(path, message, empty):
            while True:
                try:
                    with open(path, "w") as emulator:
                        emulator.write(message.decode()) # Send the key
                        emulator.write(empty) # Stop the key being pressed
                except IOError:
                    sleep(1)
                else:
                    return 0

        def key_to_hex(k):
            '''
            Returns the given keys (US) HID keyboard hex code and possible modifier
            key.

            Args:
                k: A key to translate for example: "a", "z", "3", "F2", "ENTER"
            '''
            modifier_key = 0 # Initialize modifier_key as 0

            # Check if the key is in __KEY_CODES
            if k in list(self.__KEY_CODES.keys()):
                hex_key = self.__KEY_CODES[k]

                # Check if the key needs SHIFT modifier
                if k in self.__KEYS_WITH_SHIFT:
                    modifier_key = self.__MODIFIER_CODES["SHIFT_L"]

            # If the key isn't in __KEY_CODES, it should be a normal letter
            elif len(k) == 1:
                if 'A' <= k and k <= 'Z':
                    hex_key = ord(k) - ord('A') + 0x04
                    # Uppercase letters need SHIFT modifier
                    modifier_key = self.__MODIFIER_CODES["SHIFT_L"]

                elif 'a' <= k and k <= 'z':
                    hex_key = ord(k) - ord('a') + 0x04

                else:
                    raise KbSeqError(
                        "Error in file " + os.path.abspath(self.filepath) +
                        " on line " + str(self.line_number) + ": " +
                        "Couldn't translate key: '" + k +"'")
            else:
                raise KbSeqError(
                    "Error in file " + os.path.abspath(self.filepath) +
                    " on line " + str(self.line_number) + ": " +
                     "Couldn't translate key: <" + k + ">")
            return hex_key, modifier_key


        # Empty message which will be sent to stop any keys being pressed
        empty = "\x00\x00\x00\x00\x00\x00\x00\x00"
        usb_message = bytearray(empty.encode()) # Initialize usb message
        hex_key, _modifier = key_to_hex(key) # Translate key to hex code

        # Override self.modifier if the key needs a specific one
        if _modifier:
            modifier = _modifier
        else:
            modifier = self.modifier

        usb_message[2] = hex_key
        usb_message[0] = modifier

        # Do the writing in a subprocess as it hangs in some rare cases
        writer = Process(target=writer, args=(self.emulator, usb_message, empty))
        writer.start()
        writer.join(20)
        if writer.is_alive():
            writer.terminate()
            msg = "Keyboard emulator couldn't connect to host or it froze"
            self.logger.error(msg, "kb_emulator.log")
            raise KbHwError(msg)

        self.logger.info("Sent key: " + key.ljust(5) + "  hex code: " +
                    format(hex_key, '#04x') + "  modifier: " +
                    format(modifier, '#04x'), "kb_emulator.log")
        return 0
