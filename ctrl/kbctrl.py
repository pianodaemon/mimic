from ctrl.ctrl import Ctrl
from ctrl.ctrl import CtrlError, CtrlModuleError
from ctrl.gen  import KbGen

class KbCtrl(Ctrl):
    """
    Keyboard emulator control class.
    """

    def __init__(self, logger, ctrl_info=None):
        super().__init__(logger, ctrl_info)

    def verify_model(self):
        if not isinstance(self.model, KbGen) and not issubclass(self.model.__class__, KbGen):
            msg = "unknown support library specification in {0}".format(self.model)
            raise CtrlModuleError(msg)

    def open(self):
        """"""
        self.logger.debug("asking the {0} handler to open".format(
            self.model.__str__()))
        self.model.open()
    
    def perform(self, seq_file):
        """"""
        self.logger.debug("asking the {0} handler to perform {1}".format(
            self.model.__str__(), seq_file))
        self.model.perform(seq_file)
    
    def release(self):
        """"""
        self.logger.debug("asking the {0} handler to release".format(
            self.model.__str__()))
        self.model.release()
