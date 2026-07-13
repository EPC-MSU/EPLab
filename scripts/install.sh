sudo sh -c 'echo 1CBC 0007 > /sys/bus/usb/drivers/cdc_acm/new_id'
sudo sh -c 'echo 1CBC 0008 > /sys/bus/usb/drivers/cdc_acm/new_id'
sudo adduser $USER dialout
echo -e "\n========================================= \n\
If you encounter problems connecting to the EyePoint device in the next steps, please restart the PC, in some cases adding the user to the \"dialout\" registers only after full restart.\n\
-----------------------------------------\n\
Если у Вас далее возникнут трудности при подключении к устройству EyePoint, пожалуйста перезагрузите ПК, в некоторых случаях процесс добавления пользователя в группу \"dialout\" окончательно завершается только после полной перезарузки.\n\
========================================="