#!/usr/bin/env python
"""
Inmarsat Modbus Proxy Adapter for ClearBlade connects to your ClearBlade cloud/platform using secure credentials.
In ClearBlade you define Collections that map an IDP MobileID to a proxy IP address and TCP port.
The Adapter runs on an Edge device such as Raspberry Pi, reads the mapping from the platform
and sets up concurrent Modbus servers using PyModbus and the Twisted.internet framework.
The Adapter creates IP aliases on the Edge and listens for Modbus TCP connections on each of the virtual interfaces.

ClearBlade Collection Example ``ModbusProxyRtus`` for mapping MobileID to a local IP address:

+-----------------+---------------+----------+----------+-------------+----------+-----------+----------+
|    mobile_id    |  ip_address   | tcp_port | slave_id | config_file | latitude | longitude | altitude |
+-----------------+---------------+----------+----------+-------------+----------+-----------+----------+
| 00000000SKYEE3D | 192.168.1.200 |   502    |     1    |    <blob>   |  <meta>  |  <meta>   |  <meta>  |
+-----------------+---------------+----------+----------+-------------+----------+-----------+----------+

ClearBlade Collection Example ``ModbusProxyData`` that holds the latest reported data from the field:

+---------------+----------+----------+------------------+---------------+---------------+---------------------+
|  ip_address   | tcp_port | slave_id | register_address | register_data | register_type |     timestamp       |
+---------------+----------+----------+------------------+---------------+---------------+---------------------+
| 192.168.1.200 |    502   |     1    |       0          |     123       |      ir       | 01/21/2019 07:00:00 |
+---------------+----------+----------+------------------+---------------+---------------+---------------------+

Register Types:

   * ``ir`` **Input Register** also sometimes referred to as read-only analog inputs
   * ``hr`` **Holding Register** sometimes referred to as read/write or output registers
   * ``di`` **Discrete Input** read-only boolean values sometimes called digital inputs or contact closures
   * ``co`` **Coil** read/write boolean values associated with digital outputs


.. todo::
   * Setup for multiple instances running on virtual IP address/ports from a single host
   * Proper credits for ClearBlade / Jim Bouquet

"""

__version__ = "0.1.0"

import sys
import argparse
import subprocess
import time
from clearblade.ClearBladeCore import System, Query
from pymodbus.server.async import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from twisted.internet import reactor

import headless
from context import ClearBladeModbusProxyServerContext
from constants import ADAPTER_DEVICE_ID, ADAPTER_CONFIG_COLLECTION, DEVICE_PROXY_CONFIG_COLLECTION, DATA_COLLECTION
from constants import COL_PROXY_IP_ADDRESS, COL_PROXY_IP_PORT


def get_parser():
    """
    Parses the command line arguments

    .. todo::
       Adapter services related to alerts/messaging, and local device/Edge management

    :returns: An object with attributes based on the arguments
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(description="Inmarsat Modbus Proxy Adapter for ClearBlade")

    parser.add_argument('--url', default='https://platform.clearblade.com',
                        help="The URL of the ClearBlade Platform the adapter will connect to.")

    parser.add_argument('--systemKey', required=True,
                        help="The System Key of the ClearBlade platform System the adapter will connect to.")

    parser.add_argument('--systemSecret', required=True,
                        help="The System Secret of the ClearBlade plaform System the adapter will connect to.")

    parser.add_argument('--deviceName', default=ADAPTER_DEVICE_ID,
                        help="The id/name of the device that will be used for device \
                        authentication against the ClearBlade platform or Edge, defined \
                        within the devices table of the ClearBlade platform.")

    parser.add_argument('--deviceKey', required=True,
                        help="The active key of the device that will be used for device \
                        authentication against the ClearBlade platform or Edge, defined within \
                        the Devices table of the ClearBlade platform.")

    parser.add_argument('--_slaves', dest='slaves_collection', default=DEVICE_PROXY_CONFIG_COLLECTION,
                        help="The ClearBlade Collection name with RTU proxy definitions")

    parser.add_argument('--data', dest='data_collection', default=DATA_COLLECTION,
                        help="The ClearBlade Collection name with proxy data")

    parser.add_argument('--net', dest='net_if', default='eth0',
                        help="The physical port of the network listener")

    parser.add_argument('--ip', dest='ip_address', default='localhost',
                        help="The local IP Address the PyModbus server will listen on")

    parser.add_argument('--tcp', dest='tcp_port', default=502,
                        help="The local TCP Port the PyModbus server will listen on")

    parser.add_argument('--logLevel', dest='log_level', default='INFO',
                        choices=['INFO', 'DEBUG'],
                        help="The level of logging that will be utilized by the adapter.")

    parser.add_argument('--heartbeat', dest='heartbeat', default=30,
                        help="The logging heartbeat interval in seconds.")

    # parser.add_argument('--messagingUrl', dest='messagingURL', default='localhost',
    #                     help="The MQTT URL of the ClearBlade Platform or Edge the adapter will connect to.")
    #
    # parser.add_argument('--messagingPort', dest='messagingPort', default=1883,
    #                     help="The MQTT Port of the ClearBlade Platform or Edge the adapter will connect to.")
    #
    # parser.add_argument('--topicRoot', dest='adapterTopicRoot', default='modbusProxy',
    #                     help="The root of MQTT topics this adapter will subscribe and publish to.")
    #
    # parser.add_argument('--deviceProvisionSvc', dest='deviceProvisionSvc', default='',
    #                     help="The name of a service that can be invoked to provision IoT devices \
    #                     within the ClearBlade Platform or Edge.")
    #
    # parser.add_argument('--deviceHealthSvc', dest='deviceHealthSvc', default='',
    #                     help="The name of a service that can be invoked to provide the health of \
    #                     an IoT device to the ClearBlade Platform or Edge.")
    #
    # parser.add_argument('--deviceLogsSvc', dest='deviceLogsSvc', default='',
    #                     help="The name of a service that can be invoked to provide IoT device \
    #                     logging information to the ClearBlade Platform or Edge.")
    #
    # parser.add_argument('--deviceStatusSvc', dest='deviceStatusSvc', default='',
    #                     help="The name of a service that can be invoked to provide the status of \
    #                     an IoT device to the ClearBlade Platform or Edge.")
    #
    # parser.add_argument('--deviceDecommissionSvc', dest='deviceDecommissionSvc', default='',
    #                     help="The name of a service that can be invoked to decommission IoT \
    #                     devices within the ClearBlade Platform or Edge.")

    return parser


def get_adapter_config(cb_system, cb_auth, log):
    """
    Retrieve the runtime configuration for the adapter from a ClearBlade platform Collection

    .. todo::
       Not implemented

    :param clearblade.ClearBladeCore.System cb_system: the ClearBlade System being used
    :param clearblade.ClearBladeCore.System.Device cb_auth: the ClearBlade device authentication
    :param logging.Logger log: a logger
    """
    log.warning("get_adapter_config not implemented for {}".format(ADAPTER_CONFIG_COLLECTION))
    # collection = cb_system.Collection(authenticatedUser=cb_auth, collectionName=ADAPTER_CONFIG_COLLECTION)
    # query = Query()
    # rows = collection.getItems(query)
    # # Iterate through rows and display them
    # for row in rows:
    #     log.info("ClearBlade Adapter Config: {}".format(row))


def _heartbeat(log, time_ref, interval=30):
    """
    Logs a heartbeat message intended to be show the service still running if no data is flowing from polling clients

    :param logging.Logger log: the service logger
    :param float time_ref: a time.time() reference for the first heartbeat
    :param int interval: seconds between heartbeat messages
    """
    if headless.is_logger(log):
        log.debug("Starting heartbeat ({}s)".format(interval))
        while True:
            if time.time() - time_ref >= interval:
                log.debug("Heartbeat ({}s)".format(interval))
                time_ref = time.time()
            time.sleep(1)


def run_async_server():
    """
    The main loop instantiates one or more PyModbus servers mapped to ClearBlade Modbus proxies based on
    IP address and port defined in a ClearBlade platform Collection
    """
    log = None
    virtual_ifs = []
    err_msg = None
    defer_reactor = False

    try:
        parser = get_parser()
        user_options = parser.parse_args()
        local_ip_address = user_options.ip_address
        local_tcp_port = user_options.tcp_port
        net_if = user_options.net_if
        if user_options.log_level == 'DEBUG':
            _debug = True
        else:
            _debug = False
        HEARTBEAT = user_options.heartbeat

        log = headless.get_wrapping_logger(name=ADAPTER_DEVICE_ID, debug=_debug)
        server_log = headless.get_wrapping_logger(name="pymodbus.server", debug=_debug)

        log.info("Initializing ClearBlade System connection")
        cb_system = System(systemKey=user_options.systemKey, systemSecret=user_options.systemSecret, url=user_options.url)
        cb_auth = cb_system.Device(name=user_options.deviceName, key=user_options.deviceKey)
        cb_slave_config = user_options.slaves_collection
        cb_data = user_options.data_collection

        ip_proxies = []
        proxy_ports = []
        ip_address = None
        collection = cb_system.Collection(cb_auth, collectionName=cb_slave_config)
        query = Query()
        query.notEqualTo(COL_PROXY_IP_ADDRESS, '')
        rows = collection.getItems(query)
        for row in rows:
            # TODO: allow for possibility of multiple IPs with same port or same IP with multiple ports
            ip_address = str(row[COL_PROXY_IP_ADDRESS])
            tcp_port = int(row[COL_PROXY_IP_PORT])
            if ip_address not in ip_proxies:
                log.info("Found slave at {} on ClearBlade adapter config".format(ip_address))
                ip_proxies.append(ip_address)
                proxy_ports.append(tcp_port)
            else:
                log.warning("Duplicate proxy IP address {} found in configuration - ignoring".format(ip_address))

        log.debug("Processing {} slaves".format(len(ip_proxies)))
        for i in range(0, len(ip_proxies)):
            log.debug("Getting server context for {}".format(ip_proxies[i]))
            context = ClearBladeModbusProxyServerContext(cb_system=cb_system, cb_auth=cb_auth,
                                                         cb_slaves_config=cb_slave_config, cb_data=cb_data,
                                                         ip_address=ip_proxies[i], log=log)
            # Create IP aliases
            local_ip_address = ip_proxies[i]
            ip_mask = '255.255.255.0'
            local_tcp_port = proxy_ports[i]
            if sys.platform.startswith('win'):
                log.info("I'm on Windows!")
                local_ip_address = 'localhost'
            elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                virtual_if = '{nif}:{alias}'.format(nif=net_if, alias=i)
                virtual_ifs.append(virtual_if)
                linux_command = "ifconfig {vif} {ip}".format(vif=virtual_if, ip=local_ip_address)
                if ip_mask is not None:
                    linux_command += " netmask {mask}".format(mask=ip_mask)
                log.info("Creating virtual IP address / alias via $ {}".format(linux_command))
                subprocess.call(linux_command, shell=True)

            # Create Server Identification
            identity = ModbusDeviceIdentification()
            identity.VendorName = 'PyModbus'
            identity.VendorUrl = 'http://github.com/bashwork/pymodbus/'
            identity.ProductName = 'Inmarsat/ClearBlade Modbus Server Adapter'
            identity.ModelName = ip_proxies[i]
            identity.MajorMinorRevision = '1.0'

            # Setup Modbus TCP Server
            log.info("Starting Modbus TCP server on {}:{}".format(local_ip_address, local_tcp_port))
            modbus_server_args = {
                'context': context,
                'identity': identity,
                'address': (local_ip_address, local_tcp_port),
                # 'console': _debug,
                'defer_reactor_run': True,
            }
            if modbus_server_args['defer_reactor_run']:
                defer_reactor = True
            reactor.callInThread(StartTcpServer, **modbus_server_args)

            if local_ip_address == 'localhost':
                log.info("Windows retricted environment prevents IP alias - running localhost for {}"
                         .format(ip_proxies[i]))
                break

        reactor.callInThread(_heartbeat, log, time.time(), HEARTBEAT)
        if defer_reactor:
            reactor.suggestThreadPoolSize(len(ip_proxies))
            reactor.run()

    except KeyboardInterrupt:
        err_msg = "modbus_server_adapter.py halted by Keyboard Interrupt"
        if log is not None:
            log.info(err_msg)
        else:
            print(err_msg)
        sys.exit("modbus_server_adapter.py halted by Keyboard Interrupt")

    except Exception as e:
        err_msg = "EXCEPTION: {}".format(e)
        if log is not None:
            log.info(err_msg)
        else:
            print(err_msg)
        sys.exit("modbus_server_adapter.py halted by exception {}".format(e))

    finally:
        if defer_reactor and reactor.running:
            reactor.stop()
        for vif in virtual_ifs:
            debug_msg = "Taking down virtual interface {}".format(vif)
            if log is not None:
                log.debug(debug_msg)
            else:
                print(debug_msg)
            linux_command = "ifconfig {} down".format(vif)
            subprocess.call(linux_command, shell=True)
        print("Exiting...")


if __name__ == '__main__':
    run_async_server()
