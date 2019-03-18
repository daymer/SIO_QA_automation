from modules import configuration, scli
from modules import logger_init


SIO_configuration = configuration.SIOconfiguration()
SCLI = scli.SCLI(sio_config=SIO_configuration)
SIOInfraHandler = scli.SIOInfraHandler()
SIOInfraGather = scli.SIOInfraGather(SCLI, SIOInfraHandler)
IntegrationConfigInstance = configuration.Integration


MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='INFO', log_to_file=False, executable_path=__file__)

SCLI.login()

SCLI.logout()
