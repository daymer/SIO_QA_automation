# DEPRECATED

from modules import configuration
from modules.SIOSCLI import scli

SIO_configuration = configuration.SIOconfiguration()
SCLI = scli.SCLI(sio_config=SIO_configuration)
SIOInfraHandler = scli.SIOInfraHandler()
SIOInfraGather = scli.SIOInfraGather(SCLI, SIOInfraHandler)
SCLI.login()

list_volumes = SIOInfraGather.get_vtree_list(volume_name='vol_1')
snapshot_set_unsorted = [7, 8, 9, 11]
snapshots_to_delete = []
# find snaps to delete:
for each_num in snapshot_set_unsorted:
    snapshot_numm = 'vol_1_' + str(each_num)
    snapshots_to_delete.append(next(iter([x for x in list_volumes if x[1] == snapshot_numm and x[2] == 'snapshot']), None))


for each_volume in snapshots_to_delete:
    if each_volume[2] == 'snapshot':
        result = SCLI.delete_volume(volume_id=each_volume[0])
    else:
        pass
SCLI.logout()
