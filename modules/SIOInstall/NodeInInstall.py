import ipaddress
import paramiko
import logging
import re
import datetime


class NodeInInstall(object):  # TODO: add args validation
    def __init__(self, node_ip: ipaddress, user: str = 'root',
                 password: str = 'password', pretty_name: str = None, mdm: bool = False, sds: bool = False, sdc: bool = False, manager: bool = False):
        self.logger = logging.getLogger("PhysNode")
        self.user = user
        self.password = password
        self.set_time()
        self.mgmt_ip = ipaddress.ip_address(node_ip)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(str(node_ip), username=self.user, password=self.password)
        self.data_nics = self.get_network_data_passes()
        self.data_nic_a = self.get_network_data_passes()[0]
        self.hostname = self.get_host_name()
        self.pretty_name = self.make_name(pretty_name)
        self.is_mdm = mdm
        self.is_sds = sds
        self.is_sdc = sdc
        #self.hdds, self.ssds, self.pmem, self.dax = self.get_block_devices()
        self.hdds, self.ssds, self.pmem, self.dax = self.get_dev()
        self.is_manager = manager

    def ssh_execute(self, cmd_to_execute: str, ssh_handle: paramiko = None) -> dict:
        """
        This function executes provided command line over ssh.

        :param cmd_to_execute: command line to  execute over ssh
        :param ssh_handle: paramiko ssh_handler object
        :return: dict, with status and result keys. Status is bool, result is the output of the command.
        """
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
        """
        Creates a shroter, more human readible aka pretty name for a server.

        :param name_func: provide a 'pretty name' for a server
        :return: either a provided server name, either a name created by default naming convention
        """
        if name_func is None:
            # Using default naming conventions
            name = str(self.mgmt_ip).split('.')[2] + '_' + str(self.mgmt_ip).split('.')[3]
            return name
        else:
            return name_func

    def get_host_name(self):
        """
        This function queries the server for it's hostname

        :return: server hostname
        """
        cmd_to_execute = 'hostname'
        result = self.ssh_execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            # IDENTIFYING RESULTS
            return result['result']
        elif result['status'] is False:
            # RAISING ERRORS
            raise Exception

    def set_time(self):
        """
        This function sets the same time on all servers

        """
        self.logger.debug('Setting date time on server')
        cmd_to_execute = "timedatectl set-timezone 'Asia/Jerusalem'; timedatectl set-time " + \
                         datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.ssh_execute(cmd_to_execute=cmd_to_execute)

    def get_network_data_passes(self):
        """
        This function collects information about nics

        :return: list of ip addresses, 1 per nic
        """
        # HARDCODED PARAMS:!
        self.logger.debug('Searching for network A and B data passes')
        cmd_to_execute = "ip addr show | grep -v '127.0.0.1' | grep -v '" + str(self.mgmt_ip) + "' | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"  # TODO: validate that all nics are present on all nodes
        nics = self.ssh_execute(cmd_to_execute=cmd_to_execute)  #TODO: add nic verification
        nic_list = (nics.get('result')).splitlines()
        if nic_list is None:
            self.logger.debug('No nics found, exiting')
            raise Exception('No nics found on node {mgmt_ip}'.format(mgmt_ip=self.mgmt_ip))
        else:
            return nic_list

    def get_block_devices(self, disktype: str = None):
        """
        This function collect information about the block devices

        :param disktype: Allows to switch the return to return only 1 type of disks.
                        Allowed options are:
                        hdd - returns only hdds (lsblk ROTA = 1)
                        ssd - returns only ssds (lsblk ROTA = 0)
                        pmem - returns only pmem devices
                        dax - returns only dax devices
                        None - returns hdd, ssd, pmem and dax devices
        :return: returns a list of devices selected by disktype.
        """
        sys_disk = set(
            self.ssh_execute("lsblk -p -io KNAME,TYPE | awk '/part/ {print $1}' | sed 's/.$//'")['result'].splitlines())
        hdd_cmd = "lsblk -p -io KNAME,TYPE,ROTA | grep 1 | grep -v 'pmem*' | awk '/disk/ {print $1}' "
        ssd_cmd = "lsblk -p -io KNAME,TYPE,ROTA | grep 0 | grep -v 'pmem*' | awk '/disk/ {print $1}' "
        pmem_cmd = "lsblk | awk '/pmem/ {print $1}'"
        dax_cmd = 'ls -ltr /dev/ | grep dax'
        for each_disk in sys_disk:
            hdd_cmd += "| grep -v '{disk}'".format(disk=str(each_disk))
            ssd_cmd += "| grep -v '{disk}'".format(disk=str(each_disk))
        hdds = self.ssh_execute(cmd_to_execute=hdd_cmd)['result'].splitlines()
        ssds = self.ssh_execute(cmd_to_execute=ssd_cmd)['result'].splitlines()
        pmems = self.ssh_execute(cmd_to_execute=pmem_cmd)['result'].splitlines()
        daxs = self.ssh_execute(cmd_to_execute=dax_cmd)['result'].splitlines()
        if disktype is 'hdd':
            return hdds
        elif disktype is 'ssd':
            return ssds
        elif disktype is 'pmem':
            return pmems
        elif disktype is 'dax':
            return daxs
        else:
            return hdds, ssds, pmems, daxs

    def get_dev(self, disktype: str = None) -> tuple:
        """
        This function collect information about the block devices

        :param disktype: Allows to switch the return to return only 1 type of disks.
                        Allowed options are:
                        hdd - returns only hdds (lsblk ROTA = 1)
                        ssd - returns only ssds (lsblk ROTA = 0)
                        pmem - returns only pmem devices
                        dax - returns only dax devices
                        None - returns hdd, ssd, pmem and dax devices
        :return: returns a list of devices selected by disktype.
        """
        lsbl = self.ssh_execute(cmd_to_execute='lsblk -p -io KNAME,TYPE,ROTA')
        lsblk = lsbl['result'].splitlines()
        lsblk.pop(0)
        ssd = []
        hdd = []
        pmem = []
        parted_disks = []
        dax = []
        for each_disk in lsblk:
            each_disk = each_disk.split()
            regex = r"(\/dev\/pmem\d)"
            matches = re.finditer(regex, each_disk[0])
            if matches:
                for match in matches:
                    parted_disks.append(match.group(1))
                    pmem.append(match.group(1))
            if each_disk[1] == 'disk' and each_disk[2] == '1':
                hdd.append(each_disk[0])
            elif each_disk[1] == 'disk' and each_disk[2] == '0':
                ssd.append(each_disk[0])
            elif each_disk[1] == 'part':
                regex = r"(\/dev\/\D*)\d"
                matches = re.finditer(regex, each_disk[0])
                if matches:
                    for match in matches:
                        parted_disks.append(match.group(1))
        parted_disks = set(parted_disks)
        # TODO: rewrite below check
        for parted in parted_disks:
            try:
                hdd.remove(parted)
            except ValueError:
                pass
            try:
                ssd.remove(parted)
            except ValueError:
                pass
        daxs = self.ssh_execute(cmd_to_execute="ls -ltr /dev/ | grep dax | awk '{print $10}'")['result'].splitlines()
        for each_dax in daxs:
            dax.append('/dev/{dev}'.format(dev=each_dax))
        if disktype is 'hdd':
            return hdd
        elif disktype is 'ssd':
            return ssd
        elif disktype is 'pmem':
            return pmem
        elif disktype is 'dax':
            return dax
        else:
            return hdd, ssd, pmem, dax

