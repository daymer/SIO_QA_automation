from abc import ABCMeta
import paramiko
import logging
from modules.SIOEcoSystem.PhysNode import PhysNode


class NodeGlobal(object):  # TODO: add args validation
    __metaclass__ = ABCMeta

    def __init__(self, phys_node: PhysNode):
        self.logger = logging.getLogger("NodeGlobal")
        self.phys_node = phys_node
        self.mgmt_ip = self.phys_node.mgmt_ip
        self.logger.info('Creating a NodeGlobal object for PhysNode with IP: ' + str(self.mgmt_ip))
        self.ssh = self.phys_node.ssh
        self.pretty_name = self.phys_node.pretty_name
        self.type = None

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

    def log_own_creation(self):
        self.logger = logging.info("Created a new " + self.type.upper() + " object, ip: " + str(self.mgmt_ip))

