import ipaddress
import paramiko
import logging
import re
from modules.configuration import SIOconfiguration


class PhysNode(object):  # TODO: add args validation
    def __init__(self, node_ip: ipaddress, user: str = 'root',
                 password: str = 'password', pretty_name: str = None):
        self.logger = logging.getLogger("PhysNode")
        self.user = user
        self.password = password
        self.mgmt_ip = ipaddress.ip_address(node_ip)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(str(node_ip), username=self.user, password=self.password)
        self.verified_nic_list, self.data_nic_a, self.data_nic_b = self.get_network_data_passes()
        self.hostname = self.get_host_name()
        self.pretty_name = self.make_name(pretty_name)

    def ssh_execute(self, cmd_to_execute: str, ssh_handle: paramiko = None) -> dict:
        if ssh_handle is None:
            ssh_handler_func = self.ssh
        else:
            ssh_handler_func = ssh_handle
        self.logger.debug('Executing by SSH: "'+cmd_to_execute+'"')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
        result = str(ssh_stdout.read().decode('ascii').rstrip())
        if len(result) > 0:
            self.logger.debug(result)
            return {'status': True, 'result': result}
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            if len(error) > 0:
                self.logger.error(error)
            else:
                self.logger.error("ssh_execute: empty ssh_stderr")
            return {'status': False, 'result': error}

    def make_name(self, name_func: str):
        if name_func is None:
            # Using default naming conventions
            name = str(self.mgmt_ip).split('.')[2] + '_' + str(self.mgmt_ip).split('.')[3]
            return name
        else:
            return name_func

    def get_host_name(self):
        cmd_to_execute = 'hostname'
        result = self.ssh_execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            return result['result']
        elif result['status'] is False:
            # RAISING ERRORS
            raise Exception

    def get_network_data_passes(self):
        # HARDCODED PARAMS:!
        sio_config = SIOconfiguration()
        self.logger.debug('Searching for network A and B data passes')
        self.logger.debug('Mask: '+sio_config.data_A_mask+'*; '+sio_config.data_B_mask+'*')
        data_A_mask = sio_config.data_A_mask
        data_B_mask = sio_config.data_B_mask
        verified_nic_list = []
        data_nic_a = None
        data_nic_b = None
        cmd_to_execute = 'ip link show | grep -i ,up'
        result = self.ssh_execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            regex = r"\d:\s([\d\w]*):\s<"
            matches = re.finditer(regex, result['result'], re.MULTILINE | re.IGNORECASE)
            for match in matches:
                verified_nic_list.append([match.group(1), 'NULL'])
        elif result['status'] is False:
            raise Exception('Unable to get "ip link show" via ssh from '
                            + str(self.mgmt_ip))  # TODO: hardware network misconfig exeptions
        for index, each_nic in enumerate(verified_nic_list):
            cmd_to_execute = "ip addr show " + each_nic[0] + " | grep 'inet\\b' | awk '{print $2}' | cut -d/ -f1"
            result = self.ssh_execute(cmd_to_execute=cmd_to_execute)
            if result['status'] is True:
                verified_nic_list[index][1] = result['result']
            else:
                raise Exception('Unable to get "ip addr show" for nic ' + each_nic[0] + 'via ssh from ' + str(
                    self.mgmt_ip))  # TODO: hardware network misconfig exeptions
        # searching for valid nics to be assign to data A and data B
        if len(verified_nic_list) >= 4:
            data_nic_a = next((x for x in verified_nic_list if data_A_mask in x[1]), None)
            data_nic_b = next((x for x in verified_nic_list if data_B_mask in x[1]), None)
        self.logger.debug('verified_nic_list: ' + str(verified_nic_list))
        self.logger.debug('data_nic_a: ' + str(data_nic_a))
        self.logger.debug('data_nic_b: ' + str(data_nic_b))
        if data_nic_a is not None and data_nic_b is not None:
            try:
                data_nic_a = ipaddress.ip_address(data_nic_a[1])
                data_nic_b = ipaddress.ip_address(data_nic_b[1])
                return verified_nic_list, data_nic_a, data_nic_b
            except ValueError:
                raise Exception('Unable to get A abd B data nics from node ' + str(
                    self.mgmt_ip))  # TODO: hardware network misconfig exeptions
        else:
            raise Exception('Unable to get A abd B data nics from node ' + str(
                self.mgmt_ip))  # TODO: hardware network misconfig exeptions