INSTRUCTIONS TO ENABLE CONTROL HARDWARE

-----------------------------------------------------------------------------

* Enabling for Beagle bone black

This sections outline how to enable control hardware when BBB is loaded with
Debian Jessie for BeagleBone (via microSD card). The overall of files needed
to do so, are within the current directory where this document stays.

The next files should will be copied into "/etc/systemd/system".

gpio_relay.service
otg_gadget.service

Once it is done, enable them as services

systemctl enable gpio_relay.service
systemctl enable otg_gadget.service

To ensure good working of services mentioned above we should permantly 
remove sundry default boot scripts as follows

rm /opt/scripts/boot/am335x_evm.sh
rm /opt/scripts/boot/autoconfigure_usb0.sh 
rm /opt/scripts/boot/capemgr.sh

-----------------------------------------------------------------------------

CONTACT

If you have problems, question, ideas or suggestions please contact us by
sending emails to edwin.plauchu.camacho@linux.intel.com.
