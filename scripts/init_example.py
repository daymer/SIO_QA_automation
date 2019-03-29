from modules.SIOEcoSystem.PhysNode import PhysNode
from modules.SIOEcoSystem.SIOSystemHandler import SIOSystemHandler
from modules.Logger import logger_init
from modules import configuration

SIO_configuration = configuration.SIOconfiguration()
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)


MainLogger.info('Importing a live system based on MDMs')
# Define at least 1 MDM:
SIOSystemHandler = SIOSystemHandler(sio_config=SIO_configuration, mdms=[
    PhysNode('10.234.177.29'),  # Not a real MDM, will be skipped
    PhysNode('10.234.177.30'),
    PhysNode(node_ip='10.234.177.32', pretty_name='32', user='root', password='password')
])

'''
for each_PhysNode in SIOSystemHandler.known_hosts:
    MainLogger.info('Found and added to known hosts: ' + each_PhysNode.hostname)
'''
result_object = SIOSystemHandler.system.scli.query_vtree(volume_name='v1')
if result_object.status is True:
    vtree_info_list = result_object.to_list()
    print(vtree_info_list)
