import serial
import time

import logging
logger = logging.getLogger(__name__)
logger.level = logging.INFO


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

    def send_command(self, code):
        # TODO: parse code to check if no funky messages get sent through
        whitelist = ["M20", "M27", "M31", "M78",
                     "M114", "M115", "M119"]
        '''
        M20 List SD card                            None
        M27 - Report SD print status                C for filename, S<seconds> for auto report
        M31 Print elapsed time                      None
        M78 - Print Job Stats                       None
        M105 get temps (see also auto report temps) T<index> for hotend index !! PROBLEMATIC
        M114 - Get Current Position                 D for extra details
        M115 - Firmware Info                        None
        M119 - Endstop States                       None
        '''

        self.serial.reset_input_buffer()
        self.serial.write(f"{code}\n".encode())
        #response = self.serial.read_until(b"ok\n")
        response = self.serial.readline()
        while b"ok" not in response:
            response += b"\n" + self.serial.readline()
        return response

    def get_status_location(self):
        data = self.send_command("M114").decode()
        # X:0.00 Y:0.00 Z:0.00 E:0.00 Count X:0 Y:0 Z:0\nok\n
        result = {}
        x_index = data.index("X")
        x = float(data[x_index+2:x_index+6])
        result["x"] = x
        y_index = data.index("Y")
        y = float(data[y_index+2:y_index+6])
        result["y"] = y
        z_index = data.index("Z")
        z = float(data[z_index+2:z_index+6])
        result["z"] = z
        e_index = data.index("E")
        e = float(data[e_index+2:e_index+6])
        result["e"] = e
        return result

    def get_status_uuid(self):
        data = self.send_command("M115").decode()
        # b'FIRMWARE_NAME:Marlin A8 PLUS V1.6 (Github) SOURCE_CODE_URL:https://github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:3D Printer EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff\nCap:SERIAL_XON_XOFF:0\n

    def get_status_temperatures(self):
        data = self.send_command("M105").decode()
        # b'ok T:18.40 /0.00 B:18.28 /0.00 @:0 B@:0\n'

        t_actual_start_index = data.index("T")+2
        t_actual_end_index = data.index(" ", t_actual_start_index)
        t_a = (data[t_actual_start_index:t_actual_end_index])

        t_goal_start_index = data.index("/")+1
        t_goal_end_index = data.index(" ", t_goal_start_index)
        t_g = (data[t_goal_start_index:t_goal_end_index])

        b_actual_start_index = data.index("B")+2
        b_actual_end_index = data.index(" ", b_actual_start_index)
        b_a = (data[b_actual_start_index:b_actual_end_index])

        b_goal_start_index = data.index("/", b_actual_start_index)+1
        b_goal_end_index = data.index(" ", b_goal_start_index)
        b_g = (data[b_goal_start_index:b_goal_end_index])

        result = {}
        result["temp_hotend_actual"] = t_a
        result["temp_hotend_goal"] = t_g
        result["temp_bed_actual"] = b_a
        result["temp_bed_goal"] = b_g
        return result

    def get_status(self):
        if self.ready:
            status = {}
            # TODO: make more AAS-y
            status["location"] = self.get_status_location()
            status["temperatures"] = self.get_status_temperatures()
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


if __name__ == "__main__":
    logger.debug("TEST")


'''
2021-03-03 21:12:26,431 - __main__ - DEBUG - Sent `{'head': {'x': 0, 'y': 0, 'z': 0, 'temp': 0}, 'bed': {'temp': 0}}` to mqtt topic `aas/proof_of_concept`
Printing commands
M20
-
b'Begin file list\nAA8P_F~1.GCO 1170882\nAA8P_A~2.GCO 3092211\nAA8P_E~2.GCO 2985358\nAA8P_P~3.GCO 4165637\nAA8P_P~4.GCO 3860693\nAA8P_W~1.GCO 3416636\nAA8P_T~4.GCO 4066768\nAA8P_W~2.GCO 4759247\nAA8P_K~2.GCO 2815890\nAA8P_F~2.GCO 614837\nAA8P_V~1.GCO 2424322\nAA8P_H~1.GCO 1200671\n/OLD/WLOCKB~1.GCO 4975292\n/OLD/AA8P_A~1.GCO 10498289\n/OLD/AA8P_A~2.GCO 601538\n/OLD/AA8P_A~3.GCO 172783\n/OLD/AA8P_F~1.GCO 194276\n/OLD/AA8P_P~1.GCO 11474346\n/OLD/AA8P_P~2.GCO 253226\n/OLD/AA8P_P~3.GCO 446753\n/OLD/AIRLOC~1.GCO 467394\n/OLD/BAYMAX~1.GCO 10269757\n/OLD/FU-175~1.GCO 1458217\nAIRLOC~1.GCO 10498289\nFINGER~1.GCO 988709\nAA8P_K~1.GCO 896341\nAA8P_S~1.GCO 263597\nAA8P_S~2.GCO 421957\nAA8P_S~3.GCO 2771405\nAA8P_S~4.GCO 2763339\nAA8P_T~1.GCO 103981\nAA8P_T~2.GCO 166080\nAA8P_T~3.GCO 180038\nAA8P_A~1.GCO 1441484\nAA8P_P~1.GCO 342722\nAA8P_P~2.GCO 282898\nAAEE1A~1.GCO 2155365\nAA8P_G~1.GCO 4000547\nAA8P_M~1.GCO 1279363\nAA8P_M~2.GCO 1088180\nAA8P_I~1.GCO 4458364\nAA8P_W~3.GCO 4796798\nEnd file list\nok\n'
---
M27
-
b'SD printing byte 0/0\nok\n'
---
M31
-
b'echo:Print time: 0s\nok\n'
---
M78
-
b'ok\n'
---
M114
-
b'X:0.00 Y:0.00 Z:0.00 E:0.00 Count X:0 Y:0 Z:0\nok\n'
---
M115
-
b'FIRMWARE_NAME:Marlin A8 PLUS V1.6 (Github) SOURCE_CODE_URL:https://github.com/MarlinFirmware/Marlin PROTOCOL_VERSION:1.0 MACHINE_TYPE:3D Printer EXTRUDER_COUNT:1 UUID:cede2a2f-41a2-4748-9b12-c55c62f367ff\nCap:SERIAL_XON_XOFF:0\nCap:EEPROM:0\nCap:VOLUMETRIC:1\nCap:AUTOREPORT_TEMP:1\nCap:PROGRESS:0\nCap:PRINT_JOB:1\nCap:AUTOLEVEL:0\nCap:Z_PROBE:0\nCap:LEVELING_DATA:0\nCap:BUILD_PERCENT:0\nCap:SOFTWARE_POWER:0\nCap:TOGGLE_LIGHTS:0\nCap:CASE_LIGHT_BRIGHTNESS:0\nCap:EMERGENCY_PARSER:0\nok\n'
---
M119
-
b'Reporting endstop status\nx_min: open\ny_min: open\nz_min: open\nok\n'
---
Done printing commands
'''
