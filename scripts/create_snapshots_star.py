from modules import configuration
from modules.SIOSCLI import scli
from modules.Logger import logger_init

SIO_configuration = configuration.SIOconfiguration()
SCLI = scli.SCLI(sio_config=SIO_configuration)
SIOInfraHandler = scli.SIOInfraHandler()
SIOInfraGather = scli.SIOInfraGather(SCLI, SIOInfraHandler)
IntegrationConfigInstance = configuration.Integration()


MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='INFO', log_to_file=False, executable_path=__file__)

SCLI.login()
volume_base = 'v1'
for snap_num in range(1, 117):
    SCLI.snapshot_volume(volume_name=volume_base, snapshot_name=volume_base+'_'+str(snap_num))
    SCLI.m

SCLI.logout()
