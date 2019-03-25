import ipaddress
from modules.SIOHardwareHandler.main_classes import MDM


class SIONodeHandler(object):  # TODO: add parallelism into initialization
    def __init__(self, mdms: list):
        self.current_primary_mdm = None
        self.MDM_list = []
        self.known_hosts = {}
        # initialization, stage 1: validate MDMs, add them into MDM_list and known_hosts
        unverified_mdms = []
        # query SIO in oder to get list of all nodes
        for each_mdm in mdms:
            try:
                each_ip = each_mdm['node_ip']
            except KeyError:
                raise Exception('Bad arguments submitted to SIONodeHandler init: ' + str(each_mdm))
                # TODO: SIONodeHandler misconfig exeptions
            if type(each_ip) is not ipaddress:
                try:
                    if 'username' and 'password' in each_mdm:
                        unverified_mdms.append(
                            {'node_ip': ipaddress.ip_address(each_ip),
                             'user': each_mdm['user'],
                             'password': each_mdm['password']}
                        )
                    else:
                        unverified_mdms.append(
                            {'node_ip': ipaddress.ip_address(each_ip)})
                except ValueError:
                    raise Exception('Bad arguments submitted to SIONodeHandler init: ' + str(each_ip))
                    # TODO: SIONodeHandler misconfig exeptions
        for each_mdm in unverified_mdms:
            temp_mdm = MDM(**each_mdm)
            self.MDM_list.append(temp_mdm)
        for each_mdm_host in self.MDM_list:
            self.known_hosts[each_mdm_host.hostname] = each_mdm_host
