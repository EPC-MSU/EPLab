import logging
import sys
from subprocess import PIPE, Popen
from platform import system
from typing import List, Optional
import chardet
import utils as ut


logger = logging.getLogger("eplab")


class UzfConnector:

    EXTENSION: str = ".uzf"
    FILE: str = "uzffile"

    def _check_app_path(self, ext_file: str) -> bool:
        """
        :param ext_file:
        :return: True if the system already has the correct application for files with the required extension.
        """

        stdout = self._execute_command("ftype", ext_file)
        logger.info("%s", stdout)
        if stdout:
            result = stdout.split("=")
            return len(result) == 2 and result[0] == ext_file and result[-1] == f"{sys.executable} %1"
        return False

    @staticmethod
    def _decode_bytes(data: bytes) -> str:
        """
        :param data: bytes to decode.
        :return: string.
        """

        encoding = chardet.detect(data)["encoding"]
        return data.decode(encoding).strip("\r\n")

    def _execute_command(self, *args) -> Optional[str]:
        """
        :param args: arguments to the command to be executed on the command line.
        :return: result of command execution.
        """

        process = Popen(args, stderr=PIPE, stdout=PIPE, shell=True)
        stdout, stderr = process.communicate()
        if stdout:
            try:
                stdout = self._decode_bytes(stdout)
                logger.info("stdout: %s", stdout)
                return stdout
            except Exception:
                pass

        if stderr:
            try:
                stderr = self._decode_bytes(stderr)
                logger.info("stderr: %s", stderr)
            except Exception:
                pass

        return None

    def _get_ext_file(self) -> Optional[str]:
        """
        :return:
        """

        stdout = self._execute_command("assoc", UzfConnector.EXTENSION)
        if stdout:
            return self._get_ext_file_from_stdout(stdout.split("="))
        return None

    @staticmethod
    def _get_ext_file_from_stdout(results: List[str]) -> Optional[str]:
        """
        :param results:
        :return:
        """

        if len(results) == 2 and results[0] == UzfConnector.EXTENSION:
            return results[-1]
        return None

    def _run(self) -> None:
        ext_file = self._get_ext_file()
        if ext_file is None:
            ext_file = self._set_ext_file()

        logger.info("ext_file = %s", ext_file)
        if ext_file is None:
            return

        if not self._check_app_path(ext_file):
            self._set_app_path(ext_file)

    def _set_app_path(self, ext_file: str) -> bool:
        """
        :param ext_file:
        :return: True if the application for files with the desired extension was successfully specified.
        """

        stdout = self._execute_command("ftype", f"{ext_file}={sys.executable}", "%1")
        logger.info("%s", stdout)
        if stdout:
            return True
        return False

    def _set_ext_file(self) -> Optional[str]:
        """
        :return:
        """

        stdout = self._execute_command("assoc", f"{UzfConnector.EXTENSION}={UzfConnector.FILE}")
        if stdout:
            return self._get_ext_file_from_stdout(stdout.split("="))
        return None

    def run(self) -> None:
        if system().lower() == "windows" and ut.check_is_running_from_exe():
            self._run()


def connect_uzf_to_eplab() -> None:
    connector = UzfConnector()
    connector.run()
