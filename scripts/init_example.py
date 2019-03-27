from modules.SIOHardwareHandler.PhysNode import PhysNode
from modules.SIOHardwareHandler.SIOSystemHandler import SIOSystemHandler
from modules.Logger import logger_init
from modules import configuration

SIO_configuration = configuration.SIOconfiguration()
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)


MainLogger.info('Importing a live system based on MDMs')
# Define at least 1 MDM:
SIONodeHandler = SIOSystemHandler(mdms=[

    PhysNode('10.234.177.34'),  # Not a real MDM, will be skipped
    PhysNode('10.234.177.29'),
    PhysNode(node_ip='10.234.177.32', pretty_name='32', user='root', password='password')
])

MDM_29 = SIONodeHandler.known_hosts['177_29']['mdm']

result = MDM_29.scli.query_all()
print(result)
