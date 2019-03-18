from modules import configuration
import paramiko
import re
import logging


def make_message(text: str):
    text = str(text).rstrip()
    return text


class SCLI:
    def __init__(self, sio_config: configuration.SIOconfiguration):
        self.logger = logging.getLogger()
        self.sio_config = sio_config
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.sio_config.mdm_ip, username=self.sio_config.server_user, password=self.sio_config.server_password)
        self.infra = SIOInfraHandler('NONE')

    def login(self, username: str = 'admin')->bool:
        if username == self.sio_config.admin_username:
            cmd_to_execute = 'scli --login --username '+self.sio_config.admin_username+' --password '+self.sio_config.admin_password
            ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
            result = ssh_stdout.read().decode('ascii').rstrip()
            if str(result).startswith('Logged in'):
                self.logger.info(str(result))
                return True
            else:
                raise Exception

    def logout(self)->bool:
        cmd_to_execute = 'scli --logout'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if str(result).startswith('Logged out'):
            self.logger.info(str(result))
            return True
        else:
            raise Exception

    def query_volume(self, volume_id: str=None, volume_name: str=None)->bool:
        cmd_to_execute = 'scli --query_volume'
        if volume_id is None and volume_name is None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            return result
        else:
            raise Exception

    def query_volume_tree(self, volume_id: str=None, volume_name: str=None, vtree_id: str=None)->str:
        cmd_to_execute = 'scli --query_volume_tree'
        if volume_id is None and volume_name is None and vtree_id is None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        if vtree_id is not None:
            cmd_to_execute += ' --vtree_id ' + vtree_id
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            return str(result)
        else:
            raise Exception

    def delete_volume(self, volume_id: str=None, volume_name: str=None)->bool:
        self.unmap_volume_from_sdc(volume_id=volume_id, volume_name=volume_name)
        cmd_to_execute = 'scli --remove_volume'
        if volume_id is None and volume_name is None or volume_id is not None and volume_name is not None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        cmd_to_execute += ' --i_am_sure'
        print(cmd_to_execute)
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            print(result)
            return True
        else:
            raise Exception

    def unmap_volume_from_sdc(self, volume_id: str=None, volume_name: str=None, sdc_id: str=None, sdc_name: str=None, sdc_guid: str=None, sdc_ip: str=None)->bool:
        cmd_to_execute = 'scli --unmap_volume_from_sdc'
        all_sdc = False
        if volume_id is None and volume_name is None or volume_id is not None and volume_name is not None:
            raise Exception
        if sdc_id is None and sdc_name is None and sdc_guid is None and sdc_ip is None:
            all_sdc = True
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        if all_sdc is True:
            cmd_to_execute += ' --all_sdc --i_am_sure'
        else:
            # TODO: add remove from 1 sdc
            cmd_to_execute += ' --i_am_sure'
        print(cmd_to_execute)
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            print(result)
            return True
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            print(error)
            if 'The volume is not mapped to SDC' in error:
                return True
            else:
                raise Exception

    def query_user(self, username: str='admin', silent_mode: bool = True):
        cmd_to_execute = 'scli --query_user --username' + username
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            if silent_mode is True:
                return True
            return result



class SIOInfraHandler:
    def __init__(self, system_id: str = 'NONE'):
        self.system_id = system_id


class SIOInfraGather:
    def __init__(self, scli_handler: SCLI, sio_infa_handler: SIOInfraHandler):
        self.scli = scli_handler
        self.sio_infa_handler = sio_infa_handler

    def get_vtree_list(self, volume_id: str=None, volume_name: str=None, vtree_id: str=None)-> list:
        vtree_data = self.scli.query_volume_tree(volume_id, volume_name, vtree_id)
        vtree_info_lines = vtree_data.splitlines()
        list_volumes = []  # [ID, name, type]
        for idx, line in enumerate(vtree_info_lines):
            regex = r"Volume ID:\s([\d\w]{16})\sName:\s([\S]*)"
            matches = re.finditer(regex, line, re.MULTILINE | re.IGNORECASE)
            if matches:
                for matchNum, match in enumerate(matches, start=1):
                    volume_id = match.group(1)
                    volume_name = match.group(2)
                    if not len(vtree_info_lines) == idx:
                        next_line = vtree_info_lines[idx + 1]
                        if 'Provisioning' in next_line:
                            list_volumes.append([volume_id, volume_name, 'volume'])
                        elif 'Snapshot' in next_line:
                            list_volumes.append([volume_id, volume_name, 'snapshot'])
        return list_volumes
