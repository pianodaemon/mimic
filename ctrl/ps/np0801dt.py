"""
np0801dt Remote power switch control implementation

At the time of the implementation, the reference website is:

http://www.synaccess-net.com/np-0801dt/
"""

from ctrl.gen import PsGen
from ctrl.gen import PsHwError, PsOutletError

import struct
import time
import logging
import os

impt_class='Np0801dt'

class Np0801dt(PsGen):

    __SLOT_STATUS = {'ON':1, 'OFF':0}
    __SLOT_MAX = 8
    __DEFAULT_SERVER_IP = '192.168.1.100'
    __DEFAULT_ADMIN = 'admin'
    __DEFAULT_PASSWORD = 'admin'
    __FAIL_CODE = b'$AF'
    __ACTIONS = {
        'AlterAllSlots':{'inst_code':'$A7', 'breathe_time':6},
        'AlterSlot':{'inst_code':'$A3', 'breathe_time':2},
        'MonitorDevice':{'inst_code':'$A5', 'breathe_time':2},
    }

    def __init__(self, logger, *args, **kwargs):
        super().__init__(logger, self.__SLOT_MAX)
        self.__device_ip = kwargs.get('device_ip', self.__DEFAULT_SERVER_IP)
        self.__adm_auth_info = {
            'username':kwargs.get('username', self.__DEFAULT_ADMIN),
            'password':kwargs.get('password', self.__DEFAULT_PASSWORD),
        }


    def __exec_inst(self, inst_code, breathe_time, cmd_arg_1, cmd_arg_2):
        """Execute instruction over switch."""
        import urllib.parse
        import urllib.error
        import time
        url_params = [inst_code]
        args = [ d for d in (cmd_arg_1, cmd_arg_2) if d or d == 0 ]
        for a in (args):
            arg_str = a if isinstance(a, str) else str(a)
            if arg_str:
                url_params.append(" ")
                url_params.append(arg_str)
        try:
            reply = self.__inject(urllib.parse.unquote(''.join(url_params)))
            time.sleep(breathe_time)
            return reply
        except (urllib.error.URLError, urllib.error.HTTPError):
            raise PsHwError("Problems with np-0801dt CGI-API")


    def __inject(self, data):
        """Injects an instruction in np-0801dx CGI-API.

        It shall receive an unquote string to be pushed as parameters of a
        HTTP-GET request
        """
        import urllib.request
        import base64
        from array import array

        auth_str = "{0}:{1}".format(self.__adm_auth_info['username'],
            self.__adm_auth_info['password'])
        answer = "http://{0}/cmd.cgi?{1}".format(self.__device_ip,
            urllib.request.pathname2url(data))
        basic64 = b"Basic " + base64.encodestring(
            auth_str.encode('ascii')).replace(b'\n', b'')
        req = urllib.request.Request(answer)
        req.add_header("Authorization", basic64)
        with urllib.request.urlopen(req) as response:
            resp = response.read().replace(b'\r\n', b'')
            self.logger.debug("RPS command response: {0}".format(resp))
            return resp


    def __parse_monitor_reply(self, reply):
        """Returns monitoring info."""
        values = reply.decode('utf-8').split(',')

        if values[0] == '$A0':
            # Status vector should be 4 fields long hence the magic number
            if len(values) == 4:
                rv = {}
                # data comes reversed so needs reversing
                rv['ss'] = values[1][::-1]
                rv['amps'] = values[2]
                rv['temp'] = values[3]
                return rv
        elif values[0] == '$AF':
            raise PsHwError("RPS returned error code: {0}".format(
                values[0]))
        else:
            raise PsHwError("RPS unknown error")


    def read_outlet(self, outlet_number):
        try:
            i_onum = int(outlet_number)
        except ValueError as e:
            self.logger.debug(e)
            msg = "incorrect type of outlet indexing, expecting an int"
            raise PsOutletError(msg)
        if i_onum < 1 or i_onum > self.outlet_count:
            raise PsOutletError("requested outlet {0} is out of range".format(
                outlet_number))
        return self.read_all_outlets()[i_onum]


    def read_all_outlets(self):
        """Reads all outlets from RPS device."""
        action = self.__ACTIONS['MonitorDevice']
        try:
            reply = self.__exec_inst(
                action['inst_code'], action['breathe_time'],
                None, None)
            self.logger.debug("raw outlet status: {0}".format(
                self.__parse_monitor_reply(reply)['ss']))
            d_outlet_status={}
            for si in range(self.outlet_count):
                status = self.__SLOT_STATUS['OFF']
                if self.__parse_monitor_reply(reply)['ss'][si] == '1':
                    status = self.__SLOT_STATUS['ON']

                # npd0801dt indexing is from 1 to 8 so +1 here
                d_outlet_status[si + 1] = status

            self.logger.debug("parsed outlet status: {0}".format(
                d_outlet_status))
            return d_outlet_status
        except (PsHwError, PsOutletError):
            raise

    def turn_outlet_on(self, outlet_number):
        """Turns a specified outlet on in RPS device."""
        action = self.__ACTIONS['AlterSlot']
        i_onum = int(outlet_number)
        if not i_onum or i_onum > self.outlet_count:
            raise PsOutletError("requested outlet {0} is out of range".format(
                outlet_number))
        try:
            reply = self.__exec_inst(
                action['inst_code'], action['breathe_time'],
                outlet_number, self.__SLOT_STATUS['ON'])
            if reply == self.__FAIL_CODE:
                self.logger.fatal("RPS returned fail code on cmd {0}", format(
                    action['inst_code']))
                raise PsOutletError("RPS failed when turn outlet {0} on".format(
                    outlet_number))
        except (PsHwError, PsOutletError):
            raise


    def turn_outlet_off(self, outlet_number):
        """Turns a specified outlet off in RPS device."""
        action = self.__ACTIONS['AlterSlot']
        i_onum = int(outlet_number)
        if not i_onum or i_onum > self.outlet_count:
            raise PsOutletError("requested outlet {0} is out of range".format(
                outlet_number))
        try:
            reply = self.__exec_inst(
                action['inst_code'], action['breathe_time'],
                outlet_number, self.__SLOT_STATUS['OFF'])
            if reply == self.__FAIL_CODE:
                self.logger.fatal("RPS returned fail code on cmd {0}", format(
                    action['inst_code']))
                raise PsOutletError(
                        "RPS failed turn outlet {0} off".format(outlet_number))
        except (PsHwError, PsOutletError):
            raise


    def turn_all_outlets_on(self):
        """Turns all outlets on in RPS device."""
        action = self.__ACTIONS['AlterAllSlots']
        try:
            reply = self.__exec_inst(
                action['inst_code'], action['breathe_time'],
                self.__SLOT_STATUS['ON'], None)
            if reply == self.__FAIL_CODE:
                self.logger.fatal("RPS returned fail code on cmd {0}", format(
                    action['inst_code']))
                raise PsOutletError("RPS failed when turn all outlets on")
        except (PsHwError, PsOutletError):
            raise


    def turn_all_outlets_off(self):
        """Turns all outlets off in RPS device."""
        action = self.__ACTIONS['AlterAllSlots']
        try:
            reply = self.__exec_inst(
                action['inst_code'], action['breathe_time'],
                self.__SLOT_STATUS['OFF'], None)
            if reply == self.__FAIL_CODE:
                self.logger.fatal("RPS returned fail code on cmd {0}", format(
                    action['inst_code']))
                raise PsOutletError("RPS failed when turn all outlets off")
        except (PsHwError, PsOutletError):
            raise
