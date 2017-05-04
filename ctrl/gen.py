from abc import ABCMeta, abstractmethod
from ctrl.ctrl import CtrlError

class KbGen(metaclass=ABCMeta):
    """
    Keyboard emulator controller base class.

    Defines the standard methods for coupling the main module to
    the hardware
    """

    def  __init__(self, logger, *args, **kwargs):
        self.logger = logger

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    def open(self):
        "Open device connection"

    @abstractmethod
    def perform(self, seq):
        "Type instructions from a sequence"

    @abstractmethod
    def release(self):
        "Release device resources of connection"


class KbHwError(CtrlError):
    def __init__(self, message = None, module = None):
        self.HW_module = module
        super().__init__(message = message)

class KbKeyError(CtrlError):
    def __init__(self, message = None, key_code = None):
        self.key_code = key_code
        super().__init__(message = message)

class KbSeqError(CtrlError):
    def __init__(self, message = None, seq = None):
        self.seq = seq
        super().__init__(message = message)


class PsGen(metaclass=ABCMeta):
    """
    Power switch controller base class.

    Defines the standard methods for coupling the main module to
    the hardware.
    """

    OUTLET_ON = '1'
    OUTLET_OFF = '0'

    def __init__(self, logger, outlet_count):
        self.logger = logger
        try:
            self.outlet_count = int(outlet_count)
        except ValueError as e:
            raise e('invalid outlet count argument')

    @abstractmethod
    def turn_all_outlets_on(self):
        """ Turn on all outlets. """

    @abstractmethod
    def turn_all_outlets_off(self):
        """ Turn off all outlets. """

    @abstractmethod
    def turn_outlet_on(self, outlet_number):
        """ Turn on a specific outlet by port num. """

    @abstractmethod
    def turn_outlet_off(self, outlet_number):
        """ Turn off a specific outlet by port num. """

    @abstractmethod
    def read_all_outlets(self):
        """ Get status of all outlets """

    @abstractmethod
    def read_outlet(self, outlet_number):
        """ Get status of an outlet by port num """


class PsOutletError(CtrlError):
    def __init__(self, message = None, outlet = None):
        self.outlet = outlet
        super().__init__(message = message)

class PsHwError(CtrlError):
    def __init__(self, message = None, module = None):
        self.HW_module = module
        super().__init__(message = message)
