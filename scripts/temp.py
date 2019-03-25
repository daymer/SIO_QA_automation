import ipaddress
from modules.SIOHardwareHandler.main_classes import MDM, SDS, SDC
from modules.SIOHardwareHandler.hardware_handler import SIONodeHandler
from modules.Logger import logger_init
from modules import configuration
from multiprocessing.dummy import Pool as ThreadPool
from modules.SIOSCLI import scli
import logging
import itertools
from modules.SIOHardwareHandler.DiskTools.disk_tools import get_ready_scini_device_name
from modules.IOTools.FIO import FIO

SIO_configuration = configuration.SIOconfiguration()
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)


MainLogger.info('Importing a live system based on MDMs')
SIONodeHandler = SIONodeHandler(mdms=[
    {'node_ip': '10.234.179.90'},
    {'node_ip': '10.234.179.92',
     'name': '92',
     'user': 'root',
     'password': 'password'}
])

MDM_90 = SIONodeHandler.known_hosts['92']['mdm']
MDM_92 = SIONodeHandler.known_hosts['179_90']['mdm']
