import modules.SIOEcoSystem.exeptions as main_classes_exeptions
from modules.SIOEcoSystem.NodeGlobal import NodeGlobal
from modules.SIOEcoSystem.PhysNode import PhysNode
#from modules.SIOEcoSystem.SIOSystemHandler import SIOSystemHandler
from modules.SIOSCLI import scli


class MDM(NodeGlobal):
    def __init__(self, physnode: PhysNode, sio_system_handler):
        NodeGlobal.__init__(self, physnode)
        try:
            self.installation_package = self.get_mdm_version()
            self.type = 'mdm'
            self.sio_system_handler = sio_system_handler
            self.scli = scli.SCLI(sio_config=self.sio_system_handler.sio_config,
                                  ssh_handler=self.ssh,
                                  sio_system_handler=sio_system_handler)
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
