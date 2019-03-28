from modules import configuration
import paramiko
import re
import logging
from modules.SIOSCLI.scli_exeptions import BadArgumentsException
import sys
#from modules.SIOEcoSystem.SIOSystemHandler import SIOSystemHandler


class SCLI:
    def __init__(self, sio_config: configuration.SIOconfiguration, ssh_handler: paramiko, sio_system_handler):
        self.logger = logging.getLogger(__name__)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.sio_config = sio_config
        self.ssh = ssh_handler
        self.sio_system_handler = sio_system_handler
        self.allow_errors = True  # TODO: HARDCODED PARAMETER

    def execute(self, cmd_to_execute: str, scli_command_name: str, ssh_handle: paramiko = None, locally: bool = False) -> dict:
        if ssh_handle is None:
            ssh_handler_func = self.ssh
        else:
            ssh_handler_func = ssh_handle
        if locally is False:
            cmd_to_execute += ' --approve_certificate --mdm_ip ' + self.sio_system_handler.system_mgmt_ips
        self.logger.debug('Executing by SSH: "'+cmd_to_execute+'')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
        result = str(ssh_stdout.read().decode('ascii').rstrip())
        if len(result) > 0:
            # FALSE-GOOD result handling
            if 'Usage: scli' in result:
                self.logger.error('ERROR: ' + result)
                return {'status': False, 'result': result, 'command': scli_command_name}
            self.logger.debug('SUCCESS: ' + result)
            return {'status': True, 'result': result, 'command': scli_command_name}
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()  # TODO: add cert -y
            if 'Error: MDM failed command.  Status: Invalid session. Please login and try again.' in error:
                self.login()
                ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
                result = str(ssh_stdout.read().decode('ascii').rstrip())
                if len(result) > 0:
                    self.logger.debug('SUCCESS: ' + result)
                    return {'status': True, 'result': result, 'command': scli_command_name}
                else:
                    if len(error) > 0:
                        self.logger.error('ERROR: ' + error)
                    else:
                        self.logger.error("ssh_execute: empty ssh_stderr")
                    return {'status': False, 'result': error, 'command': scli_command_name}
            else:
                if len(error) > 0:
                    self.logger.error('ERROR: ' + error)
                else:
                    self.logger.error("ssh_execute: empty ssh_stderr")
                return {'status': False, 'result': error, 'command': scli_command_name}

    def return_result(self, result: dict):
        if self.allow_errors is False and result['status'] is False:
            # RAISING ERRORS
            raise Exception
        else:
            return self.SCLIResult(result)

# General actions

    def login(self, username: str = 'admin', password: str = 'password'):
        if username == self.sio_config.admin_username:
            cmd_to_execute = 'scli --login --username '+self.sio_config.admin_username+' --password '+self.sio_config.admin_password
        else:
            cmd_to_execute = 'scli --login --username ' + username + ' --password ' + password

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def logout(self):
        cmd_to_execute = 'scli --logout'

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    # Volume actions

    def delete_volume(self, volume_id: str=None, volume_name: str=None):
        self.unmap_volume_from_sdc(volume_id=volume_id, volume_name=volume_name)
        cmd_to_execute = 'scli --remove_volume'
        if volume_id is None and volume_name is None or volume_id is not None and volume_name is not None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        cmd_to_execute += ' --i_am_sure'

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def snapshot_volume(self, volume_id: str=None, volume_name: str=None, snapshot_name: str=None)->object:
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

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def unmap_volume_from_sdc(self, volume_id: str=None, volume_name: str=None, sdc_id: str=None, sdc_name: str=None, sdc_guid: str=None, sdc_ip: str=None)->object:
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
        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def map_volume_to_sdc(self, volume_id: str=None, volume_name: str=None, sdc_id: str=None, sdc_name: str=None,
                          sdc_guid: str=None, sdc_ip: str=None, allow_multi_map: bool=True)->object:
        # Description: Map a volume to SDC node
        # scli --map_volume_to_sdc (--volume_id <ID> | --volume_name <NAME>) (--sdc_id <ID> | --sdc_name <NAME>
        # | --sdc_guid <GUID> | --sdc_ip <IP>) [--allow_multi_map]
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

        return self.return_result(self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

# Queries

    def query_volume(self, volume_id: str=None, volume_name: str=None):
        cmd_to_execute = 'scli --query_volume'
        if volume_id is None and volume_name is None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def query_all(self):
        cmd_to_execute = 'scli --query_all'

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def query_volume_tree(self, volume_id: str = None, volume_name: str = None, vtree_id: str = None):
        # This command is DEPRECATED. Please use query_vtree
        if volume_id is None and volume_name is None and vtree_id is None:
            raise Exception
        if volume_name is not None:
            self.query_vtree(volume_name=volume_name)
        if volume_id is not None:
            self.query_vtree(volume_id=volume_id)
        if vtree_id is not None:
            self.query_vtree(vtree_id=vtree_id)

    def query_vtree(self, volume_id: str=None, volume_name: str=None, vtree_id: str=None):
        cmd_to_execute = 'scli --query_vtree'
        if volume_id is None and volume_name is None and vtree_id is None:
            raise Exception
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        if volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        if vtree_id is not None:
            cmd_to_execute += ' --vtree_id ' + vtree_id

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def query_user(self, username: str='admin', silent_mode: bool = True):
        cmd_to_execute = 'scli --query_user --username' + username
        result = self.execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            return True
        elif result['status'] is False:
            return False

    class SCLIResult(object):
        def __init__(self, result: dict):
            self.status = result['status']
            self.result = result['result']
            self.command = result['command']

        # CUSTOM REWORK FOR FALSE-GOOD and FALSE-BAD RESULTS
            if self.command == 'unmap_volume_from_sdc':
                # In some cases you may try to unmap a non-mapped volume
                #  We don't need to rise any exception in this case
                if self.status is False:
                    if 'The volume is not mapped to SDC' in result['result']:
                        self.status = True

        def to_list(self):
            supported_commands = ('query_volume_tree', 'query_vtree')
            if self.status is False:
                raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"

            if self.command not in supported_commands:
                raise Exception  # TODO: add SCLIResult like "this command cannot be used for this type of query"
            elif self.command == 'query_volume_tree' or self.command == 'query_vtree':
                result_by_nodes = str(self.result).split('>>')
                vtree_info = result_by_nodes.pop(0)
                volumes_info = []
                #  searching for volumes&information
                for each_volume in result_by_nodes:
                    info_dict = {
                        'type': None,
                        'ID': None,
                        'name': None,
                        'size_in_gb': None,
                        'creation_time': None,
                        'num_of_direct_snaps': None,
                        'reads': None,
                        'writes': None,
                        'mappings': None,
                        'SCSI_reserv': None,
                        'RAM_RC': None,
                        'provisioning': None,  # volume_only
                        'capacity_in_use': None  # volume_only
                    }
                    regex = r"Volume ID:\s([\d\w]{16})\sName:\s([\S]*)"
                    matches = re.finditer(regex, each_volume, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        for matchNum, match in enumerate(matches, start=1):
                            info_dict['ID'] = match.group(1)
                            info_dict['name'] = match.group(2)
                    else:
                        raise Exception  # TODO: add snap id parsing error
                    regex = r'Provisioning: (\w*)'
                    matches = re.finditer(regex, each_volume, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        for matchNum, match in enumerate(matches, start=1):
                            info_dict['provisioning'] = match.group(1)
                            info_dict['type'] = 'volume'
                    else:
                        info_dict['type'] = 'snapshot'
                    regex = r'Size:\s[^(]*\((\d*)'
                    matches = re.finditer(regex, each_volume, re.MULTILINE | re.IGNORECASE)
                    if matches:
                        for matchNum, match in enumerate(matches, start=1):
                            info_dict['size_in_gb'] = match.group(1)


                    volumes_info.append(info_dict)
                return volumes_info
            else:
                # unspecified general processing
                return None

        def get_id(self):
            supported_commands = ('snapshot_volume')
            if self.status is False:
                raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"

            if self.command not in supported_commands:
                raise Exception  # TODO: add SCLIResult like "this command cannot be used for this type of query"
            elif self.command == 'query_volume_tree':
                regex = r"=>\s(([\d\w]{16}))\s"
                matches = re.finditer(regex, self.result['result'], re.MULTILINE | re.IGNORECASE)
                if matches:
                    for matchNum, match in enumerate(matches, start=1):
                        snapshot_id = match.group(1)
                        return snapshot_id
                else:
                    raise Exception  # TODO: add snap id parsing error

            else:
                # unspecified general processing
                return None

            '''
            map_volume_to_sdc:
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
            '''
