#!/bin/sh


GPIO_NUM=60
GPIO_BDIR="/sys/class/gpio"
GPIO_VDIR="${GPIO_BDIR}/gpio${GPIO_NUM}"
RELAY_GAP=5

gpio_check_support() {

    if [ ! -d $GPIO_VDIR ]
        then
            echo ${GPIO_NUM} > /sys/class/gpio/export
    fi

    res=`grep gpio-${GPIO_NUM} /sys/kernel/debug/gpio | wc -l`
    if [ $res -eq 0 ]
        then
            echo "It is not supporting GPIO ${GPIO_NUM}" >&2
            exit 1
    fi
}

relay_on() {
    echo 0 > $GPIO_VDIR/value
    sleep $RELAY_GAP
}

relay_off() {
    echo 1 > $GPIO_VDIR/value
    sleep $RELAY_GAP
}

case "$1" in

    "enable")
        gpio_check_support

        # Alter GPIO to use relay connected
        echo "Enabling GPIO ${GPIO_NUM} as relay..."
        echo out > $GPIO_VDIR/direction
        relay_off
    ;;
    "disable")
        gpio_check_support

        # Returns GPIO to default settings
        echo "Disabling GPIO ${GPIO_NUM} as relay..."
        relay_on
        echo in > $GPIO_VDIR/direction
    ;;
    "status")
        gpio_check_support

        grep gpio-${GPIO_NUM} /sys/kernel/debug/gpio | \
        awk '{printf "label: %s\nsense: %s\nstate: %s\n", $1, $5, $6}'
    ;;
    *)
        echo "Usage: $0 {enable|disable|status}"
        exit 1
    ;;
esac
