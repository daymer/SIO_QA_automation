import ipaddress
import paramiko
import logging


class NodeInInstall(object):  # TODO: add args validation
    def __init__(self, node_ip: ipaddress, user: str = 'root',
                 password: str = 'password', pretty_name: str = None, mdm: bool = False, sds: bool = False, sdc: bool = False, manager: bool = False):
        self.logger = logging.getLogger("PhysNode")
        self.user = user
        self.password = password
        self.mgmt_ip = ipaddress.ip_address(node_ip)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(str(node_ip), username=self.user, password=self.password)
        self.data_nics = self.get_network_data_passes()
        self.hostname = self.get_host_name()
        self.pretty_name = self.make_name(pretty_name)
        self.is_mdm = mdm
        self.is_sds = sds
        self.is_sdc = sdc
        self.is_manager = manager

    def ssh_execute(self, cmd_to_execute: str, ssh_handle: paramiko = None) -> dict:
        if ssh_handle is None:
            ssh_handler_func = self.ssh
        else:
            ssh_handler_func = ssh_handle
        self.logger.debug('Executing by SSH: "'+cmd_to_execute+'"')
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_handler_func.exec_command(cmd_to_execute)
        try:
            result = str(ssh_stdout.read().decode('ascii').rstrip())
        except UnicodeDecodeError:
            self.logger.debug('Was unable to decode: "' + str(ssh_stdout.read()) + '"')
            result = ''
        if len(result) > 0:
            self.logger.debug(result)
            return {'status': True, 'result': result}
        else:
            try:
                error = ssh_stderr.read().decode('ascii').rstrip()
            except UnicodeDecodeError:
                self.logger.debug('Was unable to decode: "' + ssh_stderr.read() + '"')
                error = '0'
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
        self.logger.debug('Searching for network A and B data passes')
        cmd_to_execute = "ip addr show | grep -v '127.0.0.1' | grep -v '" + str(self.mgmt_ip) + "' | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"  # TODO: validate that all nics are present on all nodes
        nic_list = str(self.ssh_execute(cmd_to_execute=cmd_to_execute)).splitlines()  #TODO: add nic verification
        if nic_list is None:
            self.logger.debug('No nics found, exiting')
            raise Exception('No nics found on node {mgmt_ip}'.format(mgmt_ip=self.mgmt_ip))
        else:
            return nic_list
