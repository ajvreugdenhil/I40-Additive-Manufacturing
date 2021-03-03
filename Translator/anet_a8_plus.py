import serial
import time

import logging
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG


class Printer:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.printing = False
        self.ready = False

    def start(self):
        # TODO: enumerate ports
        # TODO: make fault tolerant
        try:
            self.serial = serial.Serial(port=self.port, baudrate=self.baudrate)
        except:
            logger.critical("Printer unavailable!")

        # TODO: make more elgant
        self.serial.read_until("ok\n".encode())
        time.sleep(2)
        self.serial.reset_input_buffer()
        self.serial.write("M117 AAS module started!\n".encode())
        response = self.serial.readline()
        if response.decode() != "ok\n":
            logger.critical("Printer was not successfully started!")
            self.ready = False
        else:
            logger.info("Printer ready")
            self.ready = True

    def graceful_shutdown(self):
        if self.serial != None:
            # We're connected
            # Disconnecting resets the printer

            while self.is_active():
                time.sleep(1)

            # We can disconnect, sending message
            self.serial.reset_input_buffer()
            self.serial.write("M117 Shutting down!\n".encode())
            self.serial.readline()
            time.sleep(5)

            self.serial.reset_input_buffer()
            self.serial.write("M81\n".encode())
            self.serial.readline()
            self.serial = None
            self.ready = False

    def get_status(self):
        if self.ready:
            status = {}
            status["head"] = {}
            status["bed"] = {}
            status["head"]["x"] = 0
            status["head"]["y"] = 0
            status["head"]["z"] = 0
            status["head"]["temp"] = 0
            status["bed"]["temp"] = 0
            return status
        else:
            logger.error("Status asked of non-ready printer")
            return None

    def is_active(self):
        # TODO: Allow non-SD printing

        if self.ready == False:
            logger.info("is_active check on non-ready connection")
            return False

        # https://marlinfw.org/docs/gcode/M027.html
        self.serial.reset_input_buffer()
        self.serial.write("M27\n".encode())
        response = self.serial.readline().decode()
        logger.debug(response)
        if "SD printing byte 0/0" in response:
            return False
        elif "SD printing byte" in response:
            return True
        else:
            logger.error("Unexpected print status response from printer")
            return True  # Fail safe
