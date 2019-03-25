import ipaddress
from modules.SIOHardwareHandler.main_classes import MDM


class SIONodeHandler(object):  # TODO: add parallelism into initialization
    def __init__(self, mdms: list):
        self.current_primary_mdm = None
        # initialization, stage 1: validate MDMs, add them into MDM_list and known_hosts
        self.MDM_list = []
        self.known_hosts = {}
        # query SIO in oder to get list of all nodes
        self.MDM_list = self.make_MDM_list(mdms=mdms)
        for each_mdm_host in self.MDM_list:
            self.known_hosts[each_mdm_host.node_name] = {each_mdm_host.type: each_mdm_host}

    def make_MDM_list(self, mdms):
        unverified_mdms = []
        verified_mdms = []
        for each_mdm in mdms:
            try:
                each_ip = each_mdm['node_ip']
            except KeyError:
                raise Exception('Bad arguments submitted to SIONodeHandler init: ' + str(each_mdm))
                # TODO: SIONodeHandler misconfig exeptions
            if type(each_ip) is not ipaddress:
                try:
                    if 'name' in each_mdm:
                        name = each_mdm['name']
                    else:
                        name = None
                    if 'username' and 'password' in each_mdm:
                        unverified_mdms.append(
                            {'node_ip': ipaddress.ip_address(each_ip),
                             'user': each_mdm['user'],
                             'password': each_mdm['password'],
                             'name': name
                             }
                        )
                    else:
                        unverified_mdms.append(
                            {'node_ip': ipaddress.ip_address(each_ip)})
                except ValueError:
                    raise Exception('Bad arguments submitted to SIONodeHandler init: ' + str(each_ip))
                    # TODO: SIONodeHandler misconfig exeptions
        for each_mdm in unverified_mdms:
            temp_mdm = MDM(**each_mdm)
            verified_mdms.append(temp_mdm)
        return verified_mdms

