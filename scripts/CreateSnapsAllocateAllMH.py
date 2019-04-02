# DEPRECATED

from modules import configuration
from modules.SIOSCLI import SCLI
from modules.Logger import logger_init
import ipaddress
from modules.SIOEcoSystem.DiskTools.disk_tools import get_ready_scini_device_name
from modules.IOTools.FIO import FIO
from multiprocessing.dummy import Pool as ThreadPool
import logging
import itertools

SIO_configuration = configuration.SIOconfiguration()
FIO_instance = FIO('10.139.218.26')
SCLI = SCLI.SCLI(sio_config=SIO_configuration)
SIOInfraHandler = SCLI.SIOInfraHandler()
SIOInfraGather = SCLI.SIOInfraGather(SCLI, SIOInfraHandler)
IntegrationConfigInstance = configuration.Integration()


MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)
pool = ThreadPool(5)

base_volume = 'vol1'
vol_size_in_tb = 32
sdc_ip_A = '192.168.247.16'
sdc_ip_M = '10.139.218.26'


SCLI.login()


def make_mh_full_snap(base_volume_func: str, snapshot_name_func: str, sdc_ip_a_func: str, sdc_ip_m_func: str, vol_size_in_tb_func: int):
    scini_guid = False
    write_offset = 8796093022208
    logger = logging.getLogger()
    logger.info('Starting new thread, snapshot_name: ' + str(snapshot_name_func))
    try:
        scini_guid = SCLI.map_volume_to_sdc(
            volume_id=SCLI.snapshot_volume(volume_name=base_volume_func, snapshot_name=snapshot_name_func), sdc_ip=sdc_ip_a_func)
        scini_name = get_ready_scini_device_name(server_ip=ipaddress.ip_address(sdc_ip_m_func), scini_guid=scini_guid)
        logger.info('snapshot_name: ' + str(snapshot_name_func) + ', scini_guid: ' + str(scini_guid) + ', scini_name: /dev/' + str(scini_name))
        for each_mh in range(0, int(vol_size_in_tb_func / 8)):
            current_offset = each_mh * write_offset
            logger.info('snapshot_name: ' + str(snapshot_name_func) + ', starting FIO against offset ' + str(current_offset) + ', inter#: ' + str(each_mh))
            FIO_instance.launch_fio_custom_args(rw='write', ioengine='libaio', bs='1024k', direct='1', size='1G',
                                                numjobs='1', rwmixread='80', offset=current_offset,
                                                filename='/dev/' + scini_name, name='f_'+scini_name+'_'+ snapshot_name_func)
        SCLI.unmap_volume_from_sdc(volume_name=snapshot_name_func)
        logger.info('Successfully finishing thread for snapshot: ' + str(snapshot_name_func))
        return True
    except Exception as error:
        logger.error('Aborting thread for snapshot: ' + str(snapshot_name_func))
        logger.error(str(error))
        if scini_guid is not False:
            SCLI.unmap_volume_from_sdc(volume_name=snapshot_name_func)
            logger.error('Volume unmapped due to an issue')


snapshot_names = []
for snapshot_num in range(0, 116):
    snapshot_name = base_volume + '_' + str(snapshot_num)
    snapshot_names.append(snapshot_name)
results = pool.starmap(make_mh_full_snap, zip(itertools.repeat(base_volume),
                                              snapshot_names,
                                              (itertools.repeat(sdc_ip_A)),
                                              (itertools.repeat(sdc_ip_M)),
                                              (itertools.repeat(vol_size_in_tb))
                                              )
                       )

pool.close()
pool.join()
MainLogger.info(str(results))
SCLI.logout()
