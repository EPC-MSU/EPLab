from .launcher import get_launch_info_from_config, get_command_from_file, command_is_valid,\
    ask_for_device_urls, get_device_urls_from_command, check_device_urls, make_command_file,\
    make_dummy_command_file

import sys
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    logging.info("Get launch info")
    launch_info = get_launch_info_from_config()
    logging.info("Get command from existing file")
    launch_info.command = get_command_from_file()

    logging.info("Validate command")
    if command_is_valid(launch_info.command, launch_info.template):
        launch_info.device_urls = get_device_urls_from_command(launch_info.command, launch_info.template)
        if check_device_urls(launch_info):
            logging.info("Everything is OK. Existing command can be launched.")
            sys.exit(0)

    logging.info("Ask user for device urls")
    launch_info.device_urls = ask_for_device_urls(launch_info.num_devices, launch_info.device_types)

    if len(launch_info.device_urls) != launch_info.num_devices:
        logging.info("Incorrect manual device setup. Exiting...")
        make_dummy_command_file(launch_info)
        sys.exit()

    logging.info("Make new command file")
    make_command_file(launch_info)
