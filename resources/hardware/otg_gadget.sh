#!/bin/bash

MUSB_OTG_PORT="musb-hdrc.0.auto"
UDC_BASE_DIR="/sys/class/udc"
UDC_VIRTUAL_DIR="${UDC_BASE_DIR}/${MUSB_OTG_PORT}"
CONFIG_FS_DIR='/config'
GADGET_DIR="${CONFIG_FS_DIR}/usb_gadget/gadget"

SERVICE_IMAGES_DIR="/mnt/share/images/service"
SERVICE_IMAGE_SELECTED="service.img"

DUT_IFACE_NIC='usb0'
DUT_IFACE_IP="192.168.7.1"
DUT_IFACE_MASK="255.255.255.0"

driver_check_support() {

    if [ ! -d $UDC_VIRTUAL_DIR ]
        then            
            echo "It is not supporting musb otg port ${MUSB_OTG_PORT}" >&2
            exit 1
    fi
}

create_configfs() {

    res=`lsmod libcomposite | wc -l`
    if [ $res -eq 0 ]
        then
            modprobe libcomposite
    fi

    #Relative dirs for misc or basic configuration
    declare -a REL_MISC_CONF_DIRS=("strings/0x409" "configs/c.1/strings/0x409")

    #Relative dirs for gadgets functions
    declare -a REL_GADGETS_FUNC_DIRS=("functions/mass_storage.0" "functions/hid.usb0" "functions/ecm.usb0")

    if [ ! -d $CONFIG_FS_DIR ]
         then
             mkdir -p "${CONFIG_FS_DIR}"
    fi

    mount none $CONFIG_FS_DIR -t configfs
    if [ $? -eq 0 ]
        then
            for m in "${REL_MISC_CONF_DIRS[@]}"
	    do
                # Each gadget will consist of a number of configurations,
	        # their corresponding directories must be created.
                mkdir -p "${GADGET_DIR}/${m}"
            done
            for i in "${REL_GADGETS_FUNC_DIRS[@]}"
            do
                # The gadget will provide some functions,
                # for each function its corresponding directory must be created.
                mkdir -p "${GADGET_DIR}/${i}"
           done
        else
            echo "An error ocurried when mounting config filesystem" >&2
            exit 1
    fi
}

setup_gadget() {

    # Linux USB gadget configured through configfs (25th April 2013)
    # https://www.kernel.org/doc/Documentation/usb/gadget_configfs.txt

    VID='0x8086'
    PID='0xbeef'
    SN='1.0'
    MANUFACTURER='Intel'
    PRODUCT='Keyboard, mass storage and usb ethernet gadget'
    CONF_NAME='Config 1'

    # Maximum current to draw in mA
    MAX_POWER=120

    echo $VID > $GADGET_DIR/idVendor
    echo $PID > $GADGET_DIR/idProduct

    echo $SN > $GADGET_DIR/strings/0x409/serialnumber
    echo $MANUFACTURER > $GADGET_DIR/strings/0x409/manufacturer
    echo $PRODUCT > $GADGET_DIR/strings/0x409/product

    echo $MAX_POWER > $GADGET_DIR/configs/c.1/MaxPower
    echo $CONF_NAME > $GADGET_DIR/configs/c.1/strings/0x409/configuration	
}

config_kb() {

    # Standard HID keyboard configuration settings
    PROTOCOL=1
    SUBCLASS=1
    REPORT_LENGTH=8
    REPORT_DESC='\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0'
  
    echo $PROTOCOL > $GADGET_DIR/functions/hid.usb0/protocol
    echo $SUBCLASS > $GADGET_DIR/functions/hid.usb0/subclass
    echo $REPORT_LENGTH > $GADGET_DIR/functions/hid.usb0/report_length
    echo -ne $REPORT_DESC > $GADGET_DIR/functions/hid.usb0/report_desc

    # Placing the function into the configuration by creating a symlink
    ln -s $GADGET_DIR/functions/hid.usb0 $GADGET_DIR/configs/c.1
}

config_mass_storage() {
    img="${SERVICE_IMAGES_DIR}/${SERVICE_IMAGE_SELECTED}"
    dst="$GADGET_DIR/functions/mass_storage.0/lun.0/file"
    if [ ! -f $img ]
        then
            echo "Service image not found" >&2
            exit 1
    fi
    echo $img > $dst

    # Placing the function into the configuration by creating a symlink
    ln -s $GADGET_DIR/functions/mass_storage.0 $GADGET_DIR/configs/c.1
}

config_usb_ethernet() {
    # Placing the function into the configuration by creating a symlink
    ln -s $GADGET_DIR/functions/ecm.usb0 $GADGET_DIR/configs/c.1
}

case "$1" in

    "enable")
        driver_check_support   
        create_configfs
        setup_gadget
        config_mass_storage
        config_kb
        config_usb_ethernet
		
        echo "Binding gadget to UDC driver (brings gadget online)..."
        # This will only succeed if there are no gadgets already bound to
        # the driver. Otherwise you'll get "device or resource busy".
        echo $MUSB_OTG_PORT > $GADGET_DIR/UDC

        echo "Starting USB Ethernet interface..."
        ifconfig $DUT_IFACE_NIC up
        ifconfig $DUT_IFACE_NIC $DUT_IFACE_IP netmask $DUT_IFACE_MASK
    ;;
    "disable")
        driver_check_support

        ifconfig $DUT_IFACE_NIC down
        echo "" > $GADGET_DIR/UDC

        rm $GADGET_DIR/configs/c.1/*0
        rmdir $GADGET_DIR/configs/c.1/strings/0x409
        rmdir $GADGET_DIR/configs/c.1
        rmdir $GADGET_DIR/functions/*
        rmdir $GADGET_DIR/strings/0x409
        rmdir $GADGET_DIR

        rmmod usb_f_ecm usb_f_hid usb_f_mass_storage libcomposite
        umount $CONFIG_FS_DIR
    ;;
    "status")
        driver_check_support
        # TO DO
        # There is no code to scan status yet
    ;;
    *)
        echo "Usage: $0 {enable|disable|status}"
        exit 1
    ;;
esac
