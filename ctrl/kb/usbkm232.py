from ctrl.gen import KbGen
from ctrl.gen import KbHwError
from ctrl.gen import KbSeqError, KbKeyError

import time
import json
import serial
import logging
import os

impt_class='UsbKm232'

class UsbKm232(KbGen):

    __DEFAULT_CONN_BAUD_RATE = 9600
    __DEFAULT_CONN_TRY_TIMEOUT = 0.5
    __DEFAULT_CONN_WTRY_TIMEOUT = 0.5
    __DEFAULT_CONN_TRIES = 5
    __DEFAULT_CONN_RETRY_TIME = 2

    __US_KEY_TABLE_SIZE = 126
    __EMU_SCANCODES = {
        "`":1, "1":2, "2":3, "3":4, "4":5, "5":6, "6":7, "7":8, "8":9,
        "9":10, "0":11, "-":12, "=":13, "<undef1>":14, "<backspace>":15,
        "<tab>":16, "q":17, "w":18, "e":19, "r":20, "t":21, "y":22,
        "u":23, "i":24, "o":25, "p":26, "[":27, "]":28, "\\":29,
        "<capslock>":30, "a":31, "s":32, "d":33, "f":34, "g":35, "h":36,
        "j":37, "k":38, "l":39, ";":40, "'":41, "<undef2>":42,
        "<enter>":43, "<lshift>":44, "<undef3>":45, "z":46, "x":47,
        "c":48, "v":49, "b":50, "n":51, "m":52, ",":53, ".":54, "/":55,
        "[BUFFER_CLEAR]":56, "<rshift>":57, "<lctrl>":58, "<undef5>":59,
        "<lalt>":60, " ":61, "<ralt>":62, "<undef6>":63, "<rctrl>":64,
        "<undef7>":65, "<lwin>":70, "<rwin>":71, "<winapl>":72,
        "<insert>":75, "<delete>":76, "<undef16>":78, "<larrow>":79,
        "<home>":80, "<end>":81, "<undef23>":82, "<uparrow>":83,
        "<downarrow>":84, "<pgup>":85, "<pgdown>":86, "<rarrow>":89,
        "<numlock>":90, "<num7>":91, "<num4>":92, "<num1>":93,
        "<undef27>":94, "<num/>": 95, "<num8>": 96, "<num5>": 97,
        "<num2>": 98, "<num0>": 99, "<num*>":100, "<num9>":101,
        "<num6>":102, "<num3>":103, "<num.>":104, "<num->":105,
        "<num>":106, "<numenter>":107, "<undef28>":108, "<esc>":110,
        "<f1>":112, "<f2>":113, "<f3>":114, "<f4>":115, "<f5>":116,
        "<f6>":117, "<f7>":118, "<f8>": 119, "<f9>": 120, "<f10>": 121,
        "<f11>": 122, "<f12>": 123, "<prtscr>": 124, "<scrllk>": 125,
        "<pause/brk>": 126, "<mouse_left>": 66, "<mouse_right>": 67,
        "<mouse_up>": 68, "<mouse_down>": 69, "<mouse_lbtn_On>": 73,
        "<mouse_rbtn_On>": 74, "<mouse_mbtn_On>": 77,
        "<mouse_scr_up>": 87, "<mouse_scr_down>": 88,
        "<mouse_slow>": 109, "<mouse_fast>": 111, ":": 127, "@": 128,
        "~": 129, "!": 130, "#": 131, "$": 132, "%": 133, "*": 134,
        "?": 135, "(": 136, ")": 137, "<": 138, ">": 139, "_": 140,
        "{": 141, "}": 142, "+": 143, "|": 144, "\"": 145, "^": 146,
        "&": 147,
    }

    def __init__(self, logger, *args, **kwargs):
        super().__init__(logger)

        self.__conn_config = {
            'CONN_BAUD_RATE':kwargs.get('conn_baud_rate', self.__DEFAULT_CONN_BAUD_RATE),
            'CONN_TRY_TIMEOUT':kwargs.get('conn_try_timeout', self.__DEFAULT_CONN_TRY_TIMEOUT),
            'CONN_WTRY_TIMEOUT':kwargs.get('conn_wtry_timeout', self.__DEFAULT_CONN_WTRY_TIMEOUT),
            'CONN_TRIES':kwargs.get('conn_tries', self.__DEFAULT_CONN_TRIES),
            'CONN_RETRY_TIME':kwargs.get('conn_retry_time', self.__DEFAULT_CONN_RETRY_TIME),
        }

        try:
            self.__conn_config['CONN_TTY'] = kwargs['conn_tty']
        except (KeyError) as e:
            self.logger.error(e)
            raise KbHwError("conn_tty was not fed as parameter")


    def open(self):

        def connect_target():
            for t in range(0, self.__conn_config['CONN_TRIES']):
                try:
                    conn = serial.Serial(
                        self.__conn_config['CONN_TTY'],
                        write_timeout = self.__conn_config['CONN_WTRY_TIMEOUT'],
                        timeout = self.__conn_config['CONN_TRY_TIMEOUT'],
                        baudrate = self.__conn_config['CONN_BAUD_RATE']
                    )
                    return conn
                except serial.SerialException:
                    time.sleep(self.__conn_config['CONN_RETRY_TIME'])
            raise serial.SerialException('Too tries to connect target')


        try:
            self.__conn = connect_target()
        except (serial.SerialException) as e:
            self.logger.error(e)
            raise KbHwError("Problems performing serial connection")

    def perform(self, seq_file):

        if not seq_file:
            self.logger.fatal('A sequence file was not fed')
            raise KbHwError("sequence file can not be loaded")

        if not os.path.isfile(seq_file):
            self.logger.fatal("sequence file {0} is not a regular file".format(
                seq_file))
            raise KbHwError("sequence file can not be loaded")

        try:
            with open(seq_file) as sf:
                json_lines = sf.read()
                parsed_json = json.loads(json_lines)
                self.__plan = parsed_json['ktasks']
        except (KeyError, OSError, IOError) as e:
            self.logger.error(e)
            self.logger.fatal("malformed sequence file in: {0}".format(
                plan_file))
            raise KbHwError("sequence file can not be loaded")

        def exec_inst(inst, time_gap):

            # The scancode for key release (break) is obtained
            # from the scancode for key press (make)
            # by setting the high order bit
            RELEASE_KEY_MASK = 0x80
            release_sc = lambda sc: '%c' % (sc | RELEASE_KEY_MASK)

            if inst in self.__EMU_SCANCODES:
                sc = self.__EMU_SCANCODES[inst]
                if sc > self.__US_KEY_TABLE_SIZE:
                    self.__cover_virtual(sc)
                    return
                # clr_buff flag set on True ensures that all
                # made keys currently in USB buffer are released
                self.__send_octet(chr(sc), clr_buff=False)
                self.__send_octet(release_sc(sc))
            else:
                for ch in inst:
                    sc = self.__EMU_SCANCODES['%s' % ch]
                    if sc > self.__US_KEY_TABLE_SIZE:
                        self.__cover_virtual(sc)
                        continue
                    self.__send_octet(chr(sc), clr_buff=False)
                    self.__send_octet(release_sc(sc))
            self.logger.debug("Waiting {0} seconds to send next instruction".format(time_gap))
            time.sleep(time_gap)

        for task in self.__plan:
            try:
                desc = task['_desc']
                counter = int(task.get('_times', '1'))
                time_gap = int(task.get('_time_gap', '1'))
                inst = task['_inst']

                while counter > 0:
                    self.logger.debug("Sending {0} instruction : {1}".format(desc, inst))
                    exec_inst(inst, time_gap)
                    counter = counter - 1
            except KeyError:
                self.logger.fatal('One or more tasks upon sequence are badly conformed')
                raise KbSeqError('sequence badly conformed')
            except KbKeyError:
                raise
            except KbHwError:
                raise
            except (serial.SerialException) as e:
                self.logger.error(e)
                raise KbHwError('Experimenting serial connection problems')

    def release(self):

        if self.__conn and self.__conn.isOpen():
            self.logger.debug("Closing serial connection")
            self.__conn.close()


    def __send_octet(self, octet, check_resp=False, clr_buff=True):

        MAX_RSP_RETRIES = 10
        SILENCE_TIME = 0.09

        clear_sc = lambda: '%c' % self.__EMU_SCANCODES['[BUFFER_CLEAR]']

        def check(orig_octet):
            count = 0
            rsp = self.__conn.read(1)
            self.logger.debug("re-read rsp = " + str(rsp))
            while (len(rsp) != 1 or ord(orig_octet) != (~ord(rsp) & 0xff)) and count < MAX_RSP_RETRIES:
                rsp = self.__conn.read(1)
                self.logger.debug("re-read rsp = " + str(rsp))
                time.sleep(1)
                count += 1
            if count == MAX_RSP_RETRIES:
                raise KbHwError("Failed to get correct response from UsbKm232")

        try:
            self.logger.debug("Writing \\0%03o 0x%02x" % (ord(octet), ord(octet)))
            self.__conn.write(bytes(octet, 'UTF-8'))

            if check_resp:
                check(octet)

            time.sleep(SILENCE_TIME)

            if clr_buff:
                self.logger.debug("Clearing keystrokes")
                self.__conn.write(bytes(clear_sc(), 'UTF-8'))
                if check_resp:
                    check(clear_sc())
        except (serial.SerialException, KbHwError) as e:
            raise

    def __cover_virtual(self, sc):

        def l_shift(break_code):
            self.__send_octet(chr(self.__EMU_SCANCODES['<lshift>']), clr_buff=False)
            self.__send_octet(chr(break_code))

        cases = {
            self.__EMU_SCANCODES['+'] : lambda: l_shift(self.__EMU_SCANCODES['=']),
            self.__EMU_SCANCODES['_'] : lambda: l_shift(self.__EMU_SCANCODES['-']),
            self.__EMU_SCANCODES['|'] : lambda: l_shift(self.__EMU_SCANCODES['\\']),
            self.__EMU_SCANCODES['<'] : lambda: l_shift(self.__EMU_SCANCODES[',']),
            self.__EMU_SCANCODES['>'] : lambda: l_shift(self.__EMU_SCANCODES['.']),
            self.__EMU_SCANCODES['?'] : lambda: l_shift(self.__EMU_SCANCODES['/']),
            self.__EMU_SCANCODES[':'] : lambda: l_shift(self.__EMU_SCANCODES[';']),
            self.__EMU_SCANCODES['"'] : lambda: l_shift(self.__EMU_SCANCODES['\'']),
            self.__EMU_SCANCODES['~'] : lambda: l_shift(self.__EMU_SCANCODES['`']),
            self.__EMU_SCANCODES['{'] : lambda: l_shift(self.__EMU_SCANCODES['[']),
            self.__EMU_SCANCODES['}'] : lambda: l_shift(self.__EMU_SCANCODES[']']),
            self.__EMU_SCANCODES['!'] : lambda: l_shift(self.__EMU_SCANCODES['1']),
            self.__EMU_SCANCODES['@'] : lambda: l_shift(self.__EMU_SCANCODES['2']),
            self.__EMU_SCANCODES['#'] : lambda: l_shift(self.__EMU_SCANCODES['3']),
            self.__EMU_SCANCODES['$'] : lambda: l_shift(self.__EMU_SCANCODES['4']),
            self.__EMU_SCANCODES['%'] : lambda: l_shift(self.__EMU_SCANCODES['5']),
            self.__EMU_SCANCODES['^'] : lambda: l_shift(self.__EMU_SCANCODES['6']),
            self.__EMU_SCANCODES['&'] : lambda: l_shift(self.__EMU_SCANCODES['7']),
            self.__EMU_SCANCODES['*'] : lambda: l_shift(self.__EMU_SCANCODES['8']),
            self.__EMU_SCANCODES['('] : lambda: l_shift(self.__EMU_SCANCODES['9']),
            self.__EMU_SCANCODES[')'] : lambda: l_shift(self.__EMU_SCANCODES['0']),
        }

        try:
            cases[sc]()
        except KeyError:
            raise KbKeyError("Emulation for {0} key is not supported".format(sc))
