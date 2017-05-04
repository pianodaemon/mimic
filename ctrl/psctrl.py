from ctrl.ctrl import Ctrl
from ctrl.ctrl import CtrlError, CtrlModuleError
from ctrl.gen  import PsGen


class PsCtrl(Ctrl):
    """
    Power switch control class.
    """

    def __init__(self, logger, ctrl_info=None):
        super().__init__(logger, ctrl_info)

    def verify_model(self):
        if not isinstance(self.model, PsGen) and not issubclass(self.model.__class__, PsGen):
            msg = "unknown support library specification in {0}".format(self.model)
            raise CtrlModuleError(msg)

    def turn_all_outlets_on(self):
        """turns all the power switch outlets on."""
        self.logger.debug("asking the PS handler to turn all on")
        self.model.turn_all_outlets_on()

    def turn_all_outlets_off(self):
        """turns all the power switch outlets off."""
        self.logger.debug("asking the PS handler to turn all off")
        self.model.turn_all_outlets_off()

    def turn_outlet_on(self, outlet_number):
        """turns a single power switch outlet on."""
        self.logger.debug(
            "asking the PS handler to turn {0} outlet on".format(
                outlet_number)
        )
        self.model.turn_outlet_on(outlet_number)

    def turn_outlet_off(self, outlet_number):
        """turns a single power switch outlet off."""
        self.logger.debug(
            "asking the PS handler to turn {0} outlet off".format(
                outlet_number)
        )
        self.model.turn_outlet_off(outlet_number)

    def read_all_outlets(self):
        """reads all the power switch outlets."""
        self.logger.debug(
            "asking the PS handler to read all outlets"
        )
        return self.model.read_all_outlets()

    def read_outlet(self, outlet_number):
        """reads a single power switch outlet."""
        self.logger.debug(
            "asking the PS handler to read {0} outlet".format(
                outlet_number)
            )
        return self.model.read_outlet(outlet_number)
