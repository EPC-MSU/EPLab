sudo sh -c 'echo 1CBC 0007 > /sys/bus/usb/drivers/cdc_acm/new_id'
sudo sh -c 'echo 1CBC 0008 > /sys/bus/usb/drivers/cdc_acm/new_id'
sudo adduser $USER dialout
