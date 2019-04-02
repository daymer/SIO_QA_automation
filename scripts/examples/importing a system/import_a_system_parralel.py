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

with ThreadPool(processes=3) as pool:
    mdms_PhysNode_list = pool.starmap(PhysNode, zip(value_list))
SIOSystemHandler = SIOSystemHandler(sio_config=SIO_configuration, mdms=mdms_PhysNode_list)

MainLogger.info('System imported, added: ' + str(len(SIOSystemHandler.MDM_LIST)) + ' MDM hosts')

# NODE ADDRESSING EXAMPLE

for each_PhysNode in SIOSystemHandler.KNOWN_HOSTS:
    MainLogger.info('Found and added to known hosts: ' + each_PhysNode.hostname)

# query_vtree to list EXAMPLE
result_object = SIOSystemHandler.SYSTEM.scli.query_vtree(volume_name='v1')
if result_object.status is True:
    vtree_info_list = result_object.to_list()
    print(vtree_info_list)