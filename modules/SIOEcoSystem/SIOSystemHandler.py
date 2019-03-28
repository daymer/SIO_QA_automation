import ipaddress
from modules.SIOEcoSystem.NodeGlobal import NodeGlobal
from modules.SIOEcoSystem.MDM import MDM
from modules.SIOEcoSystem.PhysNode import PhysNode
import logging
from modules.configuration import SIOconfiguration


class SIOSystemHandler(object):  # TODO: add parallelism into initialization
    def __init__(self, sio_config: SIOconfiguration, mdms: list):
        self.logger = logging.getLogger('SIONodeHandler')
        self.sio_config = sio_config
        self.current_primary_mdm = None
        # initialization, stage 1: validate MDMs, add them into MDM_list and known_hosts
        self.known_hosts = {}
        # query SIO in oder to get list of all nodes
        self.MDM_list = self.make_MDM_list(unverified_mdms=mdms)
        for each_mdm_host in self.MDM_list:
            self.known_hosts[each_mdm_host.phys_node] = {each_mdm_host.type: each_mdm_host}
        self.system = self.MDM_list[0]
        self.system_mgmt_ips = self.make_system_mgmt_ips()

    def make_system_mgmt_ips(self):
        line = ''
        for each_mdm in self.MDM_list:
            line += str(each_mdm.mgmt_ip) + ','
        line = line[:-1]
        return line

    def make_MDM_list(self, unverified_mdms: list):
        verified_mdms = []
        for each_physnode in unverified_mdms:
            if type(each_physnode) is PhysNode:
                if next((x for x in verified_mdms if each_physnode.hostname == x.phys_node.hostname),
                        None) is None:
                    temp_mdm = MDM(each_physnode, self)
                else:
                    self.logger.error('A PhysNode with the same hostname was already added as MDM, skipping')
                    continue
                if temp_mdm.type is "mdm":
                        verified_mdms.append(temp_mdm)
                else:
                    self.logger.info('A non-verified MDM was dropped due to it\'s junk type, nothing to do')
                    pass
            else:
                self.logger.info('A non-verified MDM was dropped since a non-PhysNode object was submitted')
        if len(verified_mdms) > 0:
            return verified_mdms
        else:
            raise FailedToInitializeHardwareHandler('Not enough MDMs to initialize Hardware Handler instance', ['issue:', 'less than 1 valid MDM provided'])


class SIONodeHandlerException(Exception):
    def __init__(self, message, arguments):
        """Base class for HardwareHandler exceptions"""
        Exception.__init__(self, message + ": {0}".format(arguments))
        self.ErrorMessage = message
        self.ErrorArguments = arguments
        pass


class FailedToInitializeHardwareHandler(SIONodeHandlerException):
    """Raised when a submitted server has no role requested"""
    pass

