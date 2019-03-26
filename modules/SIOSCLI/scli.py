from modules import configuration
import paramiko
import re
import logging
from modules.SIOSCLI.scli_exeptions import BadArgumentsException


class SCLI:
    def __init__(self, sio_config: configuration.SIOconfiguration, ssh_handler: paramiko):
        self.logger = logging.getLogger(__name__)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.sio_config = sio_config
        self.ssh = ssh_handler
        self.infra = SIOInfraHandler('NONE')

    def execute(self, cmd_to_execute: str, ssh_handle: paramiko = None) -> dict:
        if ssh_handle is None:
            ssh_handler_func = self.ssh
        else:
            ssh_handler_func = ssh_handle
        self.logger.debug('Executing by SSH: "'+cmd_to_execute+'')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
        result = str(ssh_stdout.read().decode('ascii').rstrip())
        if len(result) > 0:
            self.logger.debug(result)
            return {'status': True, 'result': result}
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            if 'Error: MDM failed command.  Status: Invalid session. Please login and try again.' in error:
                self.login()
                ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
                result = str(ssh_stdout.read().decode('ascii').rstrip())
                if len(result) > 0:
                    self.logger.debug(result)
                    return {'status': True, 'result': result}
                else:
                    if len(error) > 0:
                        self.logger.error(error)
                    else:
                        self.logger.error("ssh_execute: empty ssh_stderr")
                    return {'status': False, 'result': error}
            else:
                if len(error) > 0:
                    self.logger.error(error)
                else:
                    self.logger.error("ssh_execute: empty ssh_stderr")
                return {'status': False, 'result': error}

    def login(self, username: str = 'admin', password: str = 'password')->bool:
        if username == self.sio_config.admin_username:
            cmd_to_execute = 'scli --login --username '+self.sio_config.admin_username+' --password '+self.sio_config.admin_password
        else:
            cmd_to_execute = 'scli --login --username ' + username + ' --password ' + password
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            if result['result'].startswith('Logged in'):
                self.logger.info(str(result))
                return True
        elif result['status'] is False:
            # RAISING ERRORS
            raise Exception

    def logout(self)->bool:
        cmd_to_execute = 'scli --logout'
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            if result['result'].startswith('Logged out'):
                self.logger.info(str(result))
                return True
        elif result['status'] is False:
            # RAISING ERRORS
            raise Exception

    def query_volume(self, volume_id: str=None, volume_name: str=None)->bool:
        cmd_to_execute = 'scli --query_volume'
        if volume_id is None and volume_name is None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            return result['result']
        elif result['status'] is False:
            raise Exception

    def query_all(self)->str:
        cmd_to_execute = 'scli --query_all'
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            return result['result']
        elif result['status'] is False:
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
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            return result['result']
        elif result['status'] is False:
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
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            return result['result']
        elif result['status'] is False:
            raise Exception

    def snapshot_volume(self, volume_id: str=None, volume_name: str=None, snapshot_name: str=None)->str:
        cmd_to_execute = 'scli --snapshot_volume'
        if volume_id is None and volume_name is None or volume_id is not None and volume_name is not None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        if snapshot_name is None:
            raise Exception
        cmd_to_execute += ' --snapshot_name ' + snapshot_name
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            regex = r"=>\s(([\d\w]{16}))\s"
            matches = re.finditer(regex, result['result'], re.MULTILINE | re.IGNORECASE)
            if matches:
                for matchNum, match in enumerate(matches, start=1):
                    snapshot_id = match.group(1)
                    return snapshot_id
            else:
                raise Exception  # TODO: add snap id parsing error
        elif result['status'] is False:
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
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            return True
        elif result['status'] is False:
            if 'The volume is not mapped to SDC' in result['result']:
                return True
            else:
                # Error: MDM failed command.  Status: Invalid session. Please login and try again.
                raise Exception

    def map_volume_to_sdc(self, volume_id: str=None, volume_name: str=None, sdc_id: str=None, sdc_name: str=None,
                          sdc_guid: str=None, sdc_ip: str=None, allow_multi_map: bool=True)->str:
        # Description: Map a volume to SDC node
        # scli --map_volume_to_sdc (--volume_id <ID> | --volume_name <NAME>) (--sdc_id <ID> | --sdc_name <NAME>
        # | --sdc_guid <GUID> | --sdc_ip <IP>) [--allow_multi_map]

        # Generate a cmd_to_execute
        cmd_to_execute = 'scli --map_volume_to_sdc'
        if volume_id is None and volume_name is None or volume_id is not None and volume_name is not None:
            raise BadArgumentsException('Bad volume args', {volume_id, volume_name})
        if sdc_id is None and sdc_name is None and sdc_guid is None and sdc_ip is None:
            raise BadArgumentsException('Bad sdc args, note: that only 1 sdc-related arg in time', {sdc_id, sdc_name, sdc_guid, sdc_ip})
        if sdc_ip is not None:
            cmd_to_execute += ' --sdc_ip ' + sdc_ip
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        elif volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        if allow_multi_map is True:
            cmd_to_execute += ' --allow_multi_map'
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            regex = r"Successfully mapped volume with ID\s(([\d\w]{16}))\sto SDC"
            matches = re.finditer(regex, result['result'], re.MULTILINE | re.IGNORECASE)
            if matches:
                for matchNum, match in enumerate(matches, start=1):
                    return match.group(1)
            # TODO: add check if device is ready and visible on a target side
        elif result['status'] is False:
            #Error: MDM failed command.  Status: Could not find the SDC
            raise Exception

    def query_user(self, username: str='admin', silent_mode: bool = True):
        cmd_to_execute = 'scli --query_user --username' + username
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            return True
        elif result['status'] is False:
            return False


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


