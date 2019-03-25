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


# Initializing hardware environment
SIONodeHandler = SIONodeHandler(mdms=[
    {'node_ip': '10.234.210.22',
     'user': 'root',
     'password': 'password'}])


MDM1 = SIONodeHandler.known_hosts['92T-3']

FIO_instance = FIO(ssh_handle=MDM1.ssh)
SCLI = scli.SCLI(sio_config=SIO_configuration, ssh_handler=MDM1.ssh)


pool = ThreadPool()

base_volume = 'vol1'
vol_size_in_tb = 104
sdc_ip_A = '192.168.210.22'
sdc_ip_M = '10.234.210.22'


SCLI.login()


def make_mh_full_snap(scli_instance: SCLI, fio_instance: FIO, base_volume_func: str, snapshot_name_func: str, sdc_ip_a_func: str, sdc_ip_m_func: str, vol_size_in_tb_func: int):
    scini_guid = False
    write_offset = 8796093022208
    logger = logging.getLogger()
    logger.info('Starting new thread, snapshot_name: ' + str(snapshot_name_func))
    try:
        scini_guid = scli_instance.map_volume_to_sdc(
            volume_id=scli_instance.snapshot_volume(volume_name=base_volume_func, snapshot_name=snapshot_name_func), sdc_ip=sdc_ip_a_func)
        scini_name = get_ready_scini_device_name(server_ip=ipaddress.ip_address(sdc_ip_m_func), scini_guid=scini_guid)
        logger.info('snapshot_name: ' + str(snapshot_name_func) + ', scini_guid: ' + str(scini_guid) + ', scini_name: /dev/' + str(scini_name))
        for each_mh in range(0, int(vol_size_in_tb_func / 8)):
            current_offset = each_mh * write_offset
            logger.info('snapshot_name: ' + str(snapshot_name_func) + ', starting FIO against offset ' + str(current_offset) + ', inter#: ' + str(each_mh))
            fio_instance.launch_fio_custom_args(rw='write', ioengine='libaio', bs='1024k', direct='1', size='1G',
                                                numjobs='1', rwmixread='80', offset=current_offset,
                                                filename='/dev/' + scini_name, name='f_'+scini_name+'_'+ snapshot_name_func)
        scli_instance.unmap_volume_from_sdc(volume_name=snapshot_name_func)
        logger.info('Successfully finishing thread for snapshot: ' + str(snapshot_name_func))
        return snapshot_name_func, True

    except Exception as error:
        logger.error('Aborting thread for snapshot: ' + str(snapshot_name_func))
        logger.error(str(error))
        if scini_guid is not False:
            scli_instance.unmap_volume_from_sdc(volume_name=snapshot_name_func)
            logger.error('Volume unmapped due to an issue')



snapshot_names = []
for snapshot_num in range(0, 116):
    snapshot_name = base_volume + '_' + str(snapshot_num)
    snapshot_names.append(snapshot_name)
results = pool.starmap(make_mh_full_snap, zip((itertools.repeat(SCLI)),
                                               (itertools.repeat(FIO_instance)),
                                               itertools.repeat(base_volume),
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


