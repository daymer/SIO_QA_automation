import paramiko
import ipaddress
import logging


class FIO:
    def __init__(self, ssh_handle: paramiko):
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.logger = logging.getLogger()
        self.ssh = ssh_handle

    def launch_fio_custom_args(self, **kwargs):
        # Supported args:
        supported_args = ['filename',
                          'offset',
                          'rwmixread',
                          'thread',
                          'ioengine',
                          'rw',
                          'bs',
                          'direct',
                          'size',
                          'numjobs',
                          'filename',
                          'name']
        cmd_to_execute = 'fio --thread'

        if kwargs is not None:
            for key, value in kwargs.items():
                if key in supported_args:
                    cmd_to_execute += ' --'+str(key) + '=' + str(value)
                else:
                    raise Exception
        self.logger.debug(cmd_to_execute)
        ssh_stdin, ssh_stdout, ssh_stderr = self.ssh.exec_command(cmd_to_execute)
        result = ssh_stdout.read().decode('ascii').rstrip()
        if len(result) > 0:
            self.logger.debug(result)
            return True
        else:
            error = ssh_stderr.read().decode('ascii').rstrip()
            self.logger.error(error)
            raise Exception
