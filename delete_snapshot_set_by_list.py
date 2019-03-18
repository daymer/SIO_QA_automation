from modules import configuration, scli

SIO_configuration = configuration.SIOconfiguration()
SCLI = scli.SCLI(sio_config=SIO_configuration)
SIOInfraHandler = scli.SIOInfraHandler()
SIOInfraGather = scli.SIOInfraGather(SCLI, SIOInfraHandler)
SCLI.login()

list_volumes = SIOInfraGather.get_vtree_list(volume_name='vol_3')
snapshot_set_unsorted = [79, 58, 65, 15, 104, 23, 121, 3, 22, 103, 93, 75, 47, 68, 106, 116, 94, 66, 115, 12, 124, 46, 100, 90, 51, 43, 70, 96, 28, 38, 57, 89, 77, 1, 117, 20, 16, 122, 92, 113, 72, 102, 73, 112, 61, 82, 52, 34, 44, 81, 14, 56, 10, 62, 99, 45, 123, 84, 41, 53, 2]
snapshots_to_delete = []
# find snaps to delete:
for each_num in snapshot_set_unsorted:
    snapshot_numm = 'vol_3_' + str(each_num)
    snapshots_to_delete.append(next(iter([x for x in list_volumes if x[1] == snapshot_numm and x[2] == 'snapshot']), None))


for each_volume in snapshots_to_delete:
    if each_volume[2] == 'snapshot':
        result = SCLI.delete_volume(volume_id=each_volume[0])
    else:
        pass
SCLI.logout()
