from abc import ABCMeta
import ipaddress
import paramiko
import logging
import re


class NodeGlobal(object):  # TODO: add args validation
    __metaclass__ = ABCMeta

    def __init__(self, node_ip: ipaddress,
                 user: str = 'root',
                 password: str = 'password'):
        self.logger = logging.getLogger()
        self.node_ip_m = node_ip
        self.user = user
        self.password = password
        self.ssh = paramiko.SSHClient()
        self.ssh_control_session = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(str(node_ip), username=self.user, password=self.password)
        self.verified_nic_list, self.data_nic_a, self.data_nic_b = self.get_network_data_passes()
        self.hostname = self.get_host_name()

    def get_host_name(self):
        cmd_to_execute = 'hostname'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            return result
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            self.logger.error(error)
            raise Exception('Unable to get hostname via ssh from '
                            + str(self.node_ip_m))  # TODO: hardware network misconfig exeptions

    def get_network_data_passes(self):
        verified_nic_list = []
        data_nic_a = None
        data_nic_b = None
        cmd_to_execute = 'ip link show | grep -i ,up'
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            regex = r"\d:\s([\d\w]*):\s<"
            matches = re.finditer(regex, result, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                verified_nic_list.append([match.group(1), 'NULL'])
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            self.logger.error(error)
            raise Exception('Unable to get "ip link show" via ssh from '
                            + str(self.node_ip_m))  # TODO: hardware network misconfig exeptions
        for index, each_nic in enumerate(verified_nic_list):
            cmd_to_execute = "ip addr show " + each_nic[0] + " | grep 'inet\\b' | awk '{print $2}' | cut -d/ -f1"
            ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
            result = ssh_stdout.read().decode('ascii').rstrip()
            if len(result) > 0:
                verified_nic_list[index][1] = result
            else:
                error = ssh_stderr.read().decode('ascii').rstrip()
                self.logger.error(error)
                raise Exception('Unable to get "ip addr show" for nic ' + each_nic[0] + 'via ssh from ' + str(
                    self.node_ip_m))  # TODO: hardware network misconfig exeptions
        # searching for valid nics to be assign to data A and data B
        if len(verified_nic_list) >= 4:
            data_nic_a = next((x for x in verified_nic_list if '192.168.' in x[1]), None)
            data_nic_b = next((x for x in verified_nic_list if '172.16.' in x[1]), None)
        if data_nic_a or data_nic_b is not None:
            try:
                data_nic_a = ipaddress.ip_address(data_nic_a[1])
                data_nic_b = ipaddress.ip_address(data_nic_b[1])
                return verified_nic_list, data_nic_a, data_nic_b
            except ValueError:
                raise Exception('Unable to get A abd D data nics from node ' + str(
                    self.node_ip_m))  # TODO: hardware network misconfig exeptions
        else:
            raise Exception('Unable to get A abd D data nics from node ' + str(
                self.node_ip_m))  # TODO: hardware network misconfig exeptions


class MDM(NodeGlobal):
    def __init__(self, **kwargs):
        NodeGlobal.__init__(self, **kwargs)
        self.type = 'mdm'
        self.installation_package = self.get_mdm_version()

    def get_mdm_version(self):
        cmd_to_execute = "rpm -qa | grep -i EMC-ScaleIO-mdm"
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            return result
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            self.logger.error(error)
            raise Exception('Unable to get mdm_version via ssh from ' + str(
                self.node_ip_m))  # TODO: software misconfig exeptions


class SDS(NodeGlobal):
    def __init__(self, **kwargs):
        NodeGlobal.__init__(self, **kwargs)
        self.type = 'sds'


class SDC(NodeGlobal):
    def __init__(self, **kwargs):
        NodeGlobal.__init__(self, **kwargs)
        self.type = 'sdc'


'''
def validate(f,**kwargs):
    try:
        if 'node_ip' and 'user' and 'password' in kwargs:
            return f(**kwargs)
    except KeyError:
        return None

@validate(MDM(f))
'''