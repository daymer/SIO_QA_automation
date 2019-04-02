from modules.SIOEcoSystem.PhysNode import PhysNode
from modules.SIOEcoSystem.SIOSystemHandler import SIOSystemHandler
from modules.Logger import logger_init
from modules import configuration
from multiprocessing.dummy import Pool as ThreadPool

SIO_configuration = configuration.SIOconfiguration()
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)

MainLogger.info('Importing a live SYSTEM based on MDMs')
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

MainLogger.info('System imported, added: ' + str(len(SIOSystemHandler.MDM_LIST)) + ' MDM hosts')


system_properties_response = SIOSystemHandler.SYSTEM.scli.query_properties(object_type='SYSTEM', preset='ALL')
system_properties_dict = system_properties_response.to_dict()
MainLogger.info('Example of system_properties_dict: \n' + str(system_properties_dict))
system_id = list(system_properties_dict)[0]
MainLogger.info('Example of calling system_properties_dict for system_id: \n' + str(system_id))
MainLogger.info('Example of calling system_properties_dict for DAYS_INSTALLED: \n' + str(system_properties_dict[system_id]['DAYS_INSTALLED']))


sdc_properties_response = SIOSystemHandler.SYSTEM.scli.query_properties(object_type='SDC', preset='ALL')
sdc_properties_list = sdc_properties_response.to_list()
MainLogger.info('Example of sdc_properties_list: \n' + str(sdc_properties_list))
for each_node in sdc_properties_list:
    MainLogger.info('Example of calling sdc_properties_list for IP: \n' + each_node['IP'])


'''
#  OTHER POSSIBLE  QUERIES, SET DEBUG FOR MORE INFO:
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='SDS', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='MDM', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='SYSTEM', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='PROTECTION_DOMAIN', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='STORAGE_POOL', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='FAULT_SET', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='VOLUME', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='DEVICE', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='VTREE', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='SP_SDS', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='ACCELERATION_POOL', preset='ALL')
SIOSystemHandler.SYSTEM.scli.query_properties(object_type='SNAPSHOT_POLICY', preset='ALL')
'''