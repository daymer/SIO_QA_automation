import ipaddress
import logging


class SIOSystem(object):  # TODO: add args validation
    def __init__(self, node_ip: ipaddress, role: str, data_nic: list, hdds: tuple, ssds: tuple, pmem: tuple, dax: tuple):
        self.logger = logging.getLogger("PhysNode")
        self.mgmt_ip = ipaddress.ip_address(node_ip)
        self.data_nics = data_nic
        self.role = role
        self.hdds = hdds
        self.ssds = ssds
        self.pmem = pmem
        self.dax = dax


