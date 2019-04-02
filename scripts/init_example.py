from modules.SIOEcoSystem.PhysNode import PhysNode
from modules.SIOEcoSystem.SIOSystemHandler import SIOSystemHandler
from modules.Logger import logger_init
from modules import configuration
from multiprocessing.dummy import Pool as ThreadPool
import re

SIO_configuration = configuration.SIOconfiguration()
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)

MainLogger.info('Importing a live system based on MDMs')
# Creating a set of PhysNode in parallel:
value_list = [
    {'node_ip': '10.234.177.29'},  # Not a real MDM, will be skipped
    {'node_ip': '10.234.177.30'},
    {'node_ip': '10.234.177.32',
     'pretty_name': '32',
     'user': 'root',
     'password': 'password'}
]

with ThreadPool() as pool:
    mdms_PhysNode_list = pool.starmap(PhysNode, zip(value_list))
SIOSystemHandler = SIOSystemHandler(sio_config=SIO_configuration, mdms=mdms_PhysNode_list)

MainLogger.info('System imported, added: ' + str(len(SIOSystemHandler.MDM_list)) + ' MDM hosts')

'''
result = SIOSystemHandler.system.scli.query_properties(object_type='SYSTEM', preset='ALL')
result_list = result.to_list()
system_id = result_list[0]['id']
result_dict = result.to_dict()rt
print(result_dict[system_id]['VERSION_NAME'])
'''

result = SIOSystemHandler.system.scli.query_properties(object_type='SDS', preset='ALL')

result_list = result.to_list()
print(result_list)
