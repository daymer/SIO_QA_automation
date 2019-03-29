from modules import configuration
import paramiko
import re
import logging
from modules.SIOSCLI.scli_exeptions import BadArgumentsException
import sys


# from modules.SIOEcoSystem.SIOSystemHandler import SIOSystemHandler


class SCLI:

    def __init__(self, sio_config: configuration.SIOconfiguration, ssh_handler: paramiko, sio_system_handler):
        self.logger = logging.getLogger(__name__)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.sio_config = sio_config
        self.ssh = ssh_handler
        self.sio_system_handler = sio_system_handler
        self.allow_errors = True  # TODO: HARDCODED PARAMETER

    def execute(self, cmd_to_execute: str, scli_command_name: str, ssh_handle: paramiko = None,
                locally: bool = False) -> dict:
        if ssh_handle is None:
            ssh_handler_func = self.ssh
        else:
            ssh_handler_func = ssh_handle
        if locally is False:
            cmd_to_execute += ' --approve_certificate --mdm_ip ' + self.sio_system_handler.system_mgmt_ips
        self.logger.debug('Executing by SSH: "' + cmd_to_execute + '')
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
            cmd_to_execute = 'scli --login --username ' + self.sio_config.admin_username + ' --password ' + self.sio_config.admin_password
        else:
            cmd_to_execute = 'scli --login --username ' + username + ' --password ' + password

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    def logout(self):
        cmd_to_execute = 'scli --logout'

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    # Volume actions

    def delete_volume(self, volume_id: str = None, volume_name: str = None):
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

    def snapshot_volume(self, volume_id: str = None, volume_name: str = None, snapshot_name: str = None) -> object:
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

    def unmap_volume_from_sdc(self, volume_id: str = None, volume_name: str = None, sdc_id: str = None,
                              sdc_name: str = None, sdc_guid: str = None, sdc_ip: str = None) -> object:
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

    def map_volume_to_sdc(self, volume_id: str = None, volume_name: str = None, sdc_id: str = None, sdc_name: str = None,
                          sdc_guid: str = None, sdc_ip: str = None, allow_multi_map: bool = True) -> object:
        # Description: Map a volume to SDC node
        # scli --map_volume_to_sdc (--volume_id <ID> | --volume_name <NAME>) (--sdc_id <ID> | --sdc_name <NAME>
        # | --sdc_guid <GUID> | --sdc_ip <IP>) [--allow_multi_map]
        cmd_to_execute = 'scli --map_volume_to_sdc'
        if volume_id is None and volume_name is None or volume_id is not None and volume_name is not None:
            raise BadArgumentsException('Bad volume args', {volume_id, volume_name})
        if sdc_id is None and sdc_name is None and sdc_guid is None and sdc_ip is None:
            raise BadArgumentsException('Bad sdc args, note: that only 1 sdc-related arg in time',
                                        {sdc_id, sdc_name, sdc_guid, sdc_ip})
        if sdc_ip is not None:
            cmd_to_execute += ' --sdc_ip ' + sdc_ip
        if volume_name is not None:
            cmd_to_execute += ' --volume_name ' + volume_name
        elif volume_id is not None:
            cmd_to_execute += ' --volume_id ' + volume_id
        if allow_multi_map is True:
            cmd_to_execute += ' --allow_multi_map'

        return self.return_result(
            self.execute(cmd_to_execute=cmd_to_execute, scli_command_name=sys._getframe().f_code.co_name))

    # Queries

    def query_volume(self, volume_id: str = None, volume_name: str = None):
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

    def query_vtree(self, volume_id: str = None, volume_name: str = None, vtree_id: str = None):
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

    def query_user(self, username: str = 'admin', silent_mode: bool = True):
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
            logger = logging.getLogger('SCLIResult_' + self.command)
            logger.setLevel(logging.WARNING)
            logger.debug('Starting to_list validation, result = "' + self.result + '"')
            supported_commands = ('query_volume_tree', 'query_vtree')
            if self.status is False:
                raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"
            if self.command not in supported_commands:
                raise Exception  # TODO: add SCLIResult like "this command cannot be used for this type of query"
            elif self.command == 'query_volume_tree' or self.command == 'query_vtree':
                result_by_nodes = str(self.result).split('>>')
                vtree_info_raw = result_by_nodes.pop(0)
                volumes_info = []

                def make_volume_info_dict(each_volume_func):
                    volume_info_dict = {
                        'type': None,
                        'ID': None,
                        'name': None,
                        'size_in_gb': None,  # check for variants
                        'creation_time': None,
                        'num_of_direct_snaps': None,
                        'reads': None,
                        'writes': None,
                        'mappings': None,
                        'SCSI_reserv': None,
                        'RAM_RC': None,
                        'provisioning': None,  # volume_only
                        'parent_volume': None,
                        'capacity_in_use_mg': None  # volume_only # check for variants
                    }
                    values_regex_dict = {
                        'ID': [r'Volume ID:\s([\d\w]{16})'],
                        'name': [r"\sName:\s([-\w]*)\s"],  # watch out for SDC names
                        'size_in_gb': [r'Size:\s[^(]*\((\d*)'],
                        'creation_time': [r'Creation time:\s(\d)*'],
                        'num_of_direct_snaps': [r'Number of Direct Snapshots:\s(\d)*'],
                        'reads': [r'Reads:\s*(\d)*'],
                        'writes': [r'Writes:\s*(\d)*'],
                        'mappings': [
                            r'(Volume is not mapped)',
                            r'\sSDC ID:\s([\w]{16}) IP:\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\sName:\s(.[^\s]*)\s',
                            # All about SDCs, (ID), (IP), (NAME)
                            ],
                        'SCSI_reserv': None, # TODO: ADD  SCSI_reserv parsing for query_volume_tree # {No SCSI reservations, ---}
                        'RAM_RC': None,  # TODO: ADD  RAM_RC parsing for query_volume_tree {doesn't use RAM Read Cache, ---}
                        'provisioning&parent_volume': [r'Provisioning: (\w*)',  # volume_only
                                                       r'Snapshot of ([-\w_]*)'],
                        'capacity_in_use_mg': [r'Capacity in use:\s[^(]*\((\d*)']  # volume_only
                    }
                    for each_value, each_regex_list in values_regex_dict.items():
                        def parse_by_list(volume_info_to_parse: str, each_regex_list):
                            if type(each_regex_list) == list:
                                pass
                            else:
                                # unsupported value
                                return None
                            found_value_func = []
                            try:
                                for each_regex in each_regex_list:

                                    matches_func = re.finditer(each_regex, volume_info_to_parse.replace('\n', ' ').replace('\t', '').replace('\r', '').rstrip(), re.MULTILINE | re.IGNORECASE)
                                    if matches_func:
                                        for matchNum, match in enumerate(matches_func, start=1):
                                            if 'SDC ID' in each_regex:
                                                found_value_func.append({'ID': match.group(1), 'IP': match.group(2), 'name': match.group(3)})
                                            else:
                                                found_value_func.append(match.group(1))

                                    else:
                                        logger.debug('failed to parse: ' + str(each_regex_list) + ', ' + volume_info_to_parse)
                                        continue
                                if len(found_value_func) == 0:
                                    logger.debug(
                                        'failed to parse: ' + str(each_regex_list) + ', ' + volume_info_to_parse)
                                    return None
                                else:
                                    return found_value_func
                            except re.error:
                                logger.error('Parsing failed on: ' + str(each_regex_list) + ', ' + volume_info_to_parse)
                                return None
                        found_value = parse_by_list(each_volume_func, each_regex_list)
                        if found_value and len(found_value) == 1:
                            found_value = found_value[0]
                        if each_value == 'provisioning&parent_volume':
                            if found_value in ('Thin', 'Thick'):
                                volume_info_dict['provisioning'] = found_value
                                volume_info_dict['type'] = 'volume'
                            else:
                                volume_info_dict['parent_volume'] = found_value
                                volume_info_dict['type'] = 'snapshot'
                        elif each_value == 'mappings':
                            if found_value == 'Volume is not mapped':
                                volume_info_dict[each_value] = None
                            elif found_value is None:
                                volume_info_dict[each_value] = found_value
                            else:
                                # Adding SDCs
                                volume_info_dict[each_value] = found_value
                        elif each_value == 'name':
                            volume_info_dict[each_value] = found_value
                        else:
                            volume_info_dict[each_value] = found_value
                    return volume_info_dict

                def make_vtree_info_dict(vtree_info_raw_func):
                    vtree_info_raw_func = vtree_info_raw_func.replace('\n', ' ').replace('\t', '')
                    vtree_info_dict = {
                        'sp_id': None,
                        'sp_name': None,
                        'pd_id': None,
                        'pd_name': None,
                        'ID': None,
                        'name': None,
                        'data_layout': None,
                        'num_of_vols': None,
                        'migration': None,
                        'provisioning': None,
                        'snapshots_capacity': None,
                        'capacity_in_use_mg': None,
                        'base_capacity_in_use_mg': None
                    }
                    values_regex_dict = {
                        'sp_id': [r'Storage Pool\s([\w]{16})\sName'],
                        'sp_name': [r'\sName:\s.*\sName:\s(.*)\sProtection'],
                        'pd_id': [r'Protection Domain\s([\w]{16})'],
                        'pd_name': [r'\sName:\s(\w*)\sData layout'],
                        'ID': [r'VTree ID:\s([\d\w]{16})'],
                        'name': [r"\sName:\s(.*)\sStor"],  # watch out for other names
                        'data_layout': [r'\sData layout:\s([\w\s]*)\sProvisioning'],
                        'num_of_vols': [r'Number of Volumes:\s(\d*)\sMigration'],
                        'migration': [r'Migration status:\s([\w\s]*)'],
                        'provisioning': [r'Provisioning:\s(\w*)\sTotal'],
                        'snapshots_capacity': [r'Total snapshots capacity:\s(\d*)\s'],
                        'base_capacity_in_use_mg': [r'Total base capacity in use:\s.[^\(]*\((\d*)\s.[^\)]*'],
                        'capacity_in_use_mg': [r'Total capacity in use:\s.[^\(]*\((\d*)\s.[^\)]*']
                    }
                    for each_value, each_regex_list in values_regex_dict.items():
                        def parse_by_list(vtree_info_to_parse: str, each_regex_list):
                            if type(each_regex_list) == list:
                                pass
                            else:
                                # unsupported value
                                return None
                            found_value_func = []
                            try:
                                for each_regex in each_regex_list:
                                    matches_func = re.finditer(each_regex, vtree_info_to_parse, re.MULTILINE | re.IGNORECASE)
                                    if matches_func:
                                        for matchNum, match in enumerate(matches_func, start=1):
                                            found_value_func.append(match.group(1))

                                    else:
                                        logger.warning('failed to parse: ' + str(each_regex_list) + ', ' + vtree_info_to_parse)
                                        continue
                                if len(found_value_func) == 0:
                                    logger.warning(
                                        'failed to parse: ' + str(each_regex_list) + ', ' + vtree_info_to_parse)
                                    return None
                                else:
                                    return found_value_func
                            except re.error:
                                logger.error('Parsing failed on: ' + str(each_regex_list) + ', ' + vtree_info_to_parse)
                                return None
                        found_value = parse_by_list(vtree_info_raw_func, each_regex_list)
                        if found_value and len(found_value) == 1:
                            found_value = found_value[0]

                        if each_value == 'migration':
                            if 'Not in migration' in found_value:
                                vtree_info_dict[each_value] = False
                        elif found_value is None:
                            vtree_info_dict[each_value] = found_value
                        else:
                            vtree_info_dict[each_value] = found_value
                    return vtree_info_dict
                # searching for volumes&information
                for each_volume in result_by_nodes:
                    volumes_info.append(make_volume_info_dict(each_volume))
                vtree_info = make_vtree_info_dict(vtree_info_raw)
                return vtree_info, volumes_info
            else:
                # unspecified general processing
                return None

        def get_id(self):
            supported_commands = ('snapshot_volume', 'map_volume_to_sdc')
            #  Returns:
            #  snapshot_volume: ID of a new created snapshot
            #  map_volume_to_sdc: ID of a mapped volume

            if self.status is False:
                raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"

            if self.command not in supported_commands:
                raise Exception  # TODO: add SCLIResult like "this command cannot be used for this type of query"
            elif self.command == 'snapshot_volume':
                regex = r"=>\s(([\d\w]{16}))\s"
                matches = re.finditer(regex, self.result, re.MULTILINE | re.IGNORECASE)
                if matches:
                    for matchNum, match in enumerate(matches, start=1):
                        snapshot_id = match.group(1)
                        return snapshot_id
                else:
                    raise Exception  # TODO: add snap id parsing error
            elif self.command == 'map_volume_to_sdc':
                regex = r"Successfully mapped volume with ID\s(([\d\w]{16}))\sto SDC"
                matches = re.finditer(regex, self.result, re.MULTILINE | re.IGNORECASE)
                if matches:
                    for matchNum, match in enumerate(matches, start=1):
                        volume_id = match.group(1)
                        return volume_id
            else:
                # unspecified general processing
                return None


