import ipaddress
import paramiko


def get_ready_scini_device_name(server_ip: ipaddress, scini_guid: str):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(str(server_ip), username='root', password='password')
    cmd_to_execute = 'lsblk -b -o NAME -r'
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)
    result = str(ssh_stdout.read().decode('ascii').rstrip())
    if result.startswith('NAME'):
        scini_devices = []
        result_lines = result.splitlines()
        for line in result_lines:
            if line.startswith('scini'):
                scini_devices.append([line, 'NULL'])
    else:
        raise Exception  # TODO: add error for no device found
    if len(scini_devices) > 0:
        for index, each_scini_device in enumerate(scini_devices):
            cmd_to_execute = '/opt/emc/scaleio/sdc/bin/drv_cfg --query_block_device_id --block_device /dev/'+str(each_scini_device[0])
            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)
            result = str(ssh_stdout.read().decode('ascii').rstrip())
            if result:
                scini_devices[index][1] = result
            else:
                raise Exception  # TODO: add error for no device ID
        scini_name = next((x for x in scini_devices if scini_guid in x[1]), None) # TODO: disk looks like 38909c3378fd890f-9a1fc5bd0000000b, need to add system_id validation
        if scini_name is not None:
            # TODO: add write validation
            return scini_name[0]
        else:
            raise Exception  # TODO: scini wasn't recognized
    else:
        raise Exception  # TODO: add error for no scini found