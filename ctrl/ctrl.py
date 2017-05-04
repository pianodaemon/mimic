import logging
import sys
import os

from custom.profile import ProfileTree, ProfileReader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "ps")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "kb")))

class CtrlError(Exception):
    def __init__(self, message = None):
        self.message = message
    def __str__(self):
        return self.message

class CtrlModuleError(CtrlError):
    def __init__(self, message = None, module = None):
        super().__init__(message = message)

class Ctrl(object):
    """
    Emulator control class.
    """
    
    def __init__(self, logger, ctrl_info=None):
        self.logger = logger

        if not ctrl_info:
            raise CtrlError("Control hardware info not passed")

        self.ctrl_info = ctrl_info
        self.__incept_impt()

    def verify_model(self):
        """verify module's origin"""
        # It should be implemented in case of neededing
        # addtional model verification upon child classes
        # of Ctrl
        self.logger.debug(
            "not attempting verifications for model {0}".format(self.model)
        )

    def __incept_impt(self):
        """
        load hw module required
        """
        m = ProfileReader.get_content(
            self.ctrl_info.selected.mod_name,
            ProfileReader.PNODE_UNIQUE
        )

        def setup_kwargs(l):
            n = {}
            for d in l:
                n[d["name"]] = d["value"]
            return n

        try:
            self.logger.debug("attempting the import of {0} library".format(m))
            hw_mod = __import__(m)

            if not hasattr(hw_mod, "impt_class"):
                msg = "module {0} has no impt_class attribute".format(m)
                raise CtrlModuleError(msg)

            cname = getattr(hw_mod, "impt_class")

            if not hasattr(hw_mod, cname):
                msg = "module {0} has no {1} class implemented".format(m, cname)
                raise CtrlModuleError(msg)

            self.model = getattr(hw_mod, cname)(
                self.logger,
                **setup_kwargs(
                    ProfileReader.get_content(
                        self.ctrl_info.selected.mod_params,
                        ProfileReader.PNODE_MANY
                    )
                )
            )

            self.verify_model()

        except (ImportError, CtrlModuleError) as e:
            self.logger.fatal("{0} support library failure".format(m))
            raise e
