from anet_a8_plus import Printer
import json
import time
from paho.mqtt import client as mqtt_client
import signal
import logging
import socket

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.level = logging.INFO


printer_shutdown_function = None


def signal_handler(sig, frame):
    logger.info("SIGINT. Gracefully shutting down!")
    signal.signal(signal.SIGINT, signal_handler_hard_shutdown)
    if printer_shutdown_function != None:
        printer_shutdown_function()
    logger.info("Done.")
    exit(0)


def signal_handler_hard_shutdown(sig, frame):
    logger.error("SIGINT. Hard shutdown!")
    exit(1)


# MQTT
broker = 'otpi.home'
port = 1883
topic = "aas/proof_of_concept"
client_id = 'python-mqtt-5'
username = 'streamsheets'
password = 'w2FXLOgMD1'

# Printer
printer_port = "/dev/ttyUSB0"
printer_baud = 115200


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker!")
    else:
        logger.info("Failed to connect, return code %d\n", rc)


def connect_mqtt():
    client = None
    try:
        client = mqtt_client.Client(client_id)
    except socket.gaierror:
        logger.critical("MQTT domain error!")
        return None
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    try:
        client.connect(broker, port)
    except ConnectionRefusedError:
        logger.critical("MQTT connection refused!")
        return None
    logger.info("MQTT setup successful")
    return client


def update_loop(mqtt_client, printer):
    logger.info("Starting update loop")

    while True:
        time.sleep(0.5)
        msg = printer.get_status()
        # TODO: check msg validity
        result = mqtt_client.publish(topic, json.dumps(msg))
        status = result[0]
        if status == 0:
            logger.debug(f"Sent `{msg}` to mqtt topic `{topic}`")
        else:
            logger.error("Failed to send mqtt message")


def main():
    logger.info("Starting!")

    # MQTT
    client = connect_mqtt()
    if client is None:
        exit()
    client.loop_start()

    # Printer
    p = Printer(printer_port, printer_baud)
    p.start()
    if p.ready == False:
        logger.error("Printer was not ready")
        exit()
    signal.signal(signal.SIGINT, signal_handler)
    global printer_shutdown_function
    printer_shutdown_function = p.graceful_shutdown

    update_loop(client, p)

    logger.info("Exiting!")


if __name__ == '__main__':
    main()
