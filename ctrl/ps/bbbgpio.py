from ctrl.gen import PsGen
from ctrl.gen import PsHwError, PsOutletError

import struct
import time
import logging
import os

impt_class='BBBGpio'

class BBBGpio(PsGen):
    """
    Control class for a bbb gpio
    """

    __SLOT_MAX = 1
    __GPIOS_BASE_DIR = '/sys/class/gpio'

    def __init__(self, logger, *args, **kwargs):

        super().__init__(logger, self.__SLOT_MAX)

        def det_noc(v):
            if v == self.OUTLET_ON:
                return (self.OUTLET_OFF, self.OUTLET_ON)
            if v == self.OUTLET_OFF:
                return (self.OUTLET_ON, self.OUTLET_OFF)

            raise PsHwError(
                'It was not possible to determine relay behaviour'
            )

        self.__gpio_conf = {
            'GPIO_PIN': kwargs.get('gpio_pin', None),
            'GPIO_CUTTER_ON': None,
            'GPIO_CUTTER_OFF': None
        }

        if not self.__gpio_conf['GPIO_PIN']:
            raise PsError('gpio pin has not been defined')

        self.__gpio_conf['GPIO_CUTTER_ON'], self.__gpio_conf['GPIO_CUTTER_OFF'] = det_noc(
           kwargs.get('gpio_noc', self.OUTLET_ON)
        )

        self.__gpio_abs_path = "{0}/{1}/value".format(
            self.__GPIOS_BASE_DIR,
            self.__gpio_conf['GPIO_PIN']
        )

    def turn_outlet_off(self, outlet_number):
        """Turns a specified outlet off in cutter device"""
        self.__verify_outlet_range(outlet_number)
        self.__act_upon_outlet(self.__gpio_conf['GPIO_CUTTER_OFF'])


    def turn_outlet_on(self, outlet_number):
        """Turns a specified outlet on in cutter device"""
        self.__verify_outlet_range(outlet_number)
        self.__act_upon_outlet(self.__gpio_conf['GPIO_CUTTER_ON'])


    def turn_all_outlets_on(self):
        """Turns all outlets on in cutter device."""
        self.__act_upon_outlet(self.__gpio_conf['GPIO_CUTTER_ON'])


    def turn_all_outlets_off(self):
        """Turns all outlets off in cutter device."""
        self.__act_upon_outlet(self.__gpio_conf['GPIO_CUTTER_OFF'])


    def read_outlet(self, outlet_number):
        """Reads the requested outlet from cutter device"""
        return self.read_all_outlets()[self.__verify_outlet_range(outlet_number)]

    def read_all_outlets(self):
        """Reads all outlets from cutter device."""
        _UNIQUE_SLOT_INDEX = 1
        rd = {}
        fd = self.__open_virt_file()
        gpio_val = fd.readline()
        rd[_UNIQUE_SLOT_INDEX] = gpio_val.replace('\n', '')
        fd.close()
        return rd

    def __verify_outlet_range(self, outlet_number):
        i_onum = None
        try:
            i_onum = int(outlet_number)
        except ValueError as e:
            self.logger.debug(e)
            msg = "incorrect type of outlet indexing, expecting an int"
            raise PsOutletError(msg)
        if i_onum < 1 or i_onum > self.outlet_count:
            raise PsOutletError("requested outlet {0} is out of range".format(
                outlet_number))
        return i_onum

    def __open_virt_file(self, writeable=False):
        """opens sys virtual as per gpio"""
        if not os.path.isfile(self.__gpio_abs_path):
            emsg = "GPIO file {0} is not found".format(gpio_abs_path)
            self.logger.error(emsg)
            raise PsOutletError(emsg)
        fd = None
        try:
            mode = 'w' if writeable else 'r'
            fd = open(self.__gpio_abs_path, mode)
        except (OSError, IOError) as e:
            self.logger.error(e)
            emsg = "GPIO file {0} can not be opened".format(gpio_abs_path)
            self.logger.error(emsg)
            raise PsOutletError("GPIO file can not be loaded")
        return fd

    def __act_upon_outlet(self, state):
        """
        set GPIO pin to state
        """
        switcher = [
            (lambda f: f.write('0')),
            (lambda f: f.write('1'))
        ]
        st = int(state)

        if st < 0:
            raise PsOutletError("There is not any negative gpio state")

        fd = self.__open_virt_file(writeable=True)
        switcher[st](fd)
        fd.close()
