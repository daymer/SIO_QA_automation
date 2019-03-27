from modules.SIOHardwareHandler.NodeGlobal import NodeGlobal
from modules.SIOHardwareHandler.PhysNode import PhysNode
import modules.SIOHardwareHandler.exeptions as main_classes_exeptions
from modules.SIOSCLI import scli
from modules.configuration import SIOconfiguration


class MDM(NodeGlobal):
    def __init__(self, physnode: PhysNode):
        NodeGlobal.__init__(self, physnode)
        try:
            self.installation_package = self.get_mdm_version()
            self.type = 'mdm'
            # HARDCODED PARAMS:!
            sio_configuration = SIOconfiguration()
            self.scli = scli.SCLI(sio_config=sio_configuration, ssh_handler=self.ssh)
            self.log_own_creation()
            self.is_debug = False  # TODO: add check
            self.phys_node.installed_components['mdm'] = True
        except main_classes_exeptions.WrongRoleSelected as error:
            self.logger.critical('A wrong type of node was submitted as MDM due to: ' + str(error))
            self.logger.info('A node ' + str(self.mgmt_ip) + 'will be ignored while MDM object creation due to: ' + str(error))
            self.type = 'junk'

    def get_mdm_version(self):
        cmd_to_execute = "rpm -qa | grep -i EMC-ScaleIO-mdm"
        result = self.ssh_execute(cmd_to_execute=cmd_to_execute)
        if result['status'] is True:
            return result
        elif result['status'] is False:
            raise main_classes_exeptions.WrongRoleSelected('Unable to get mdm_version via ssh',
                                                           ['node ip', str(self.mgmt_ip)])
