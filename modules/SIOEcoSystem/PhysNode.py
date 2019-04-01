import ipaddress
import paramiko
import logging
from modules.configuration import SIOconfiguration


class PhysNode(object):  # TODO: add args validation
    def __init__(self, node_ip: str, user: str = 'root',
                 password: str = 'password', pretty_name: str = None):
        if type(node_ip) == str:
            pass
        elif type(node_ip) == dict:
            incoming_dict = dict(node_ip)
            node_ip = incoming_dict['node_ip']
            user = incoming_dict.get('user', None)
            password = incoming_dict.get('password', None)
            pretty_name = incoming_dict.get('pretty_name', None)
            if user is None:
                user = 'root'
                password = 'password'
        self.logger = logging.getLogger("PhysNode")
        self.ssh_execute_logger = logging.getLogger("PhysNode_ssh_execute")
        self.user = user
        self.password = password
        self.mgmt_ip = ipaddress.ip_address(node_ip)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(str(node_ip), username=self.user, password=self.password)

        self.ip_list, self.data_nic_a, self.data_nic_b = self.get_network_data_passes()
        self.hostname = self.get_host_name()
        self.pretty_name = self.make_name(pretty_name)
        self.installed_components = {
            'mdm': False,
            'sds': False,
            'sdc': False
        }
        self.kvm_ip = self.make_kvm_ip()
        self.os_build = None
        self.os_type = None
        self.bkl_dev_list = []
        self.SIO_system_handler = None

    def ssh_execute(self, cmd_to_execute: str, ssh_handle: paramiko = None) -> dict:
        if ssh_handle is None:
            ssh_handler_func = self.ssh
        else:
            ssh_handler_func = ssh_handle
        self.ssh_execute_logger.debug('Executing by SSH: "'+cmd_to_execute+'"')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
        result = str(ssh_stdout.read().decode('ascii').rstrip())
        if len(result) > 0:
            self.ssh_execute_logger.debug(result)
            return {'status': True, 'result': result}
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            if len(error) > 0:
                self.ssh_execute_logger.error(error)
            else:
                self.ssh_execute_logger.error("ssh_execute: empty ssh_stderr")
            return {'status': False, 'result': error}

    def make_name(self, name_func: str):
        if name_func is None:
            # Using default naming conventions
            name = str(self.mgmt_ip).split('.')[2] + '_' + str(self.mgmt_ip).split('.')[3]
            return name
        else:
            return name_func

    def make_kvm_ip(self):
        ip_octets = str(self.mgmt_ip).split('.')
        kvm_ip = ip_octets[0]+'.'+ip_octets[1]+'.'+str(int(ip_octets[2])+1)+'.'+ip_octets[3]
        return ipaddress.ip_address(kvm_ip)

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
        cmd_to_execute = "ip addr show | grep -v '127.0.0.1' | grep 'inet\\b' | awk '{print  $7, $2}' | cut -d/ -f1"
        result = self.ssh_execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            for each_line in str(result['result']).splitlines():
                nic_name = each_line.split(' ')[0]
                nic_ip = each_line.split(' ')[1]
                verified_nic_list.append([nic_name, nic_ip])
        # searching for valid nics to be assign to data A and data B
        if len(verified_nic_list) >= 3:
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
                raise Exception('Unable to get valid ipaddress of A abd B data nics from node ' + str(
                    self.mgmt_ip))  # TODO: hardware network misconfig exeptions
        else:
            raise Exception('Unable to get A abd B data nics from node ' + str(
                self.mgmt_ip))  # TODO: hardware network misconfig exeptions