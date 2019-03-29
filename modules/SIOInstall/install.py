"""This module allow you to install SIO on provided server list. It allows to install normal and debug version. Allows yo use signed and unsigned packages."""
from modules.SIOInstall.NodeInInstall import NodeInInstall
from modules.SIOInstall.SIOSystem import SIOSystem
import warnings
import logging
from modules.Logger import logger_init
from modules import configuration

# Suppressing DeprecationWarnings
warnings.filterwarnings("ignore")
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG',
                                        log_to_file=False, executable_path=__file__)


def install_mdm(node: NodeInInstall, build: str, path: str):
    cmd_to_execute = "wget {path}EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm -nv".format(path=path, build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    if node.is_manager:
        cmd_to_execute = "MDM_ROLE_IS_MANAGER=1 rpm -i EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm".format(build=build)
    else:
        cmd_to_execute = "MDM_ROLE_IS_MANAGER=0 rpm -i EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "echo -e '\\user session hard timeout secs=2592000\\user session timeout secs=2592000' >> " \
                     "/opt/emc/scaleio/mdm/cfg/conf.txt; pkill mdm"
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rm -rf EMC*".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install_sds(node: NodeInInstall, build: str, path: str):
    cmd_to_execute = "wget {path}EMC-ScaleIO-sds-{build}.el7.x86_64.rpm -nv".format(path=path, build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rpm -i EMC-ScaleIO-sds-{build}.el7.x86_64.rpm --force".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rm -rf EMC*".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install_sdc(node: NodeInInstall, build: str, mdm_ips: str, path: str):
    cmd_to_execute = "wget {path}EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm -nv".format(path=path, build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "MDM_IP={mdm_ips} rpm -i EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm --force".format(mdm_ips=mdm_ips,
                                                                                                     build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rm -rf EMC*".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def add_slave_mdm(master: NodeInInstall, slave: SIOSystem):
    cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip} --mdm_role manager --new_mdm_' \
                     'management_ip {mgmt_ip} --new_mdm_name MDM_{mgmt_ip}'.format(data_ip=','.join(slave.data_nics),
                                                                                   mgmt_ip=str(slave.mgmt_ip))
    master.ssh_execute(cmd_to_execute=cmd_to_execute)


def add_tb(master: NodeInInstall, tb: SIOSystem):
    cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip} --mdm_role tb --new_mdm_name TB_{mgmt_ip}'.format(
        data_ip=','.join(tb.data_nics), mgmt_ip=str(tb.mgmt_ip))
    master.ssh_execute(cmd_to_execute=cmd_to_execute)


def create_cluster(nodes: list):
    for each_node in nodes:
        if each_node.is_manager:
            master = each_node
            system = [SIOSystem(role='master', node_ip=each_node.mgmt_ip, data_nic=each_node.data_nics)]
            break
    for each_node in nodes:
        if each_node is not master:
            if each_node.is_mdm and each_node.is_manager:
                system.append(SIOSystem(role='manager', node_ip=each_node.mgmt_ip, data_nic=each_node.data_nics))
            elif each_node.is_mdm and each_node.is_manager is False:
                system.append(SIOSystem(role='tb', node_ip=each_node.mgmt_ip, data_nic=each_node.data_nics))
    managers = []
    tbs = []
    cmd_to_execute = 'scli --create_mdm_cluster --master_mdm_ip {data_ip} --master_mdm_management_ip {mgmt_ip} ' \
                     '--master_mdm_name MDM_{mgmt_ip} --accept_license --approve_certificate'.format(
        data_ip=','.join(master.data_nics), mgmt_ip=str(master.mgmt_ip))
    master.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = 'scli --login --username admin --password admin --approve_certificate; scli --set_password ' \
                     '--old_password admin --new_password Scaleio123; scli --login --username admin --password ' \
                     'Scaleio123 --approve_certificate'
    master.ssh_execute(cmd_to_execute=cmd_to_execute)
    mode = 1
    for each_node in system:
        if each_node.role == 'manager':
            managers.append(each_node)
            mode += 1
        elif each_node.role == 'tb':
            tbs.append(each_node)
            mode += 1
    if 3 <= mode < 5:
        slave = managers[0]
        add_slave_mdm(master, slave)
        tb = tbs[0]
        add_tb(master, tb)
        # TODO: change adding to use ID instead of names
        cmd_to_execute = 'scli --switch_cluster_mode --cluster_mode 3_node --add_slave_mdm_name MDM_{slave_name} ' \
                         '--add_tb_name TB_{tb_name}'.format(slave_name=str(slave.mgmt_ip),
                                                           tb_name=str(tb.mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
    # TODO: add check if there is enough managers
    elif mode >= 5:
        slaves = []
        tiebrakers = []
        for i in range(2):
            slaves.append(managers[i])
            add_slave_mdm(master, slaves[i])
            tiebrakers.append(tbs[i])
            add_tb(master, tbs[i])
        # TODO: change adding to use ID instead of names
        cmd_to_execute = 'scli --switch_cluster_mode --cluster_mode 5_node --add_slave_mdm_name MDM_{slave1},' \
                         'MDM_{slave2} --add_tb_name TB_{tb1},TB_{tb2}'.format(slave1=str(slaves[0].mgmt_ip),
                                                                               slave2=str(slaves[1].mgmt_ip),
                                                                               tb1=str(tiebrakers[0].mgmt_ip),
                                                                               tb2=str(tiebrakers[1].mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)


def preinstall_cleanup(node: NodeInInstall):
    cmd_to_execute = 'service scini stop; I_AM_SURE=1 rpm -e $(rpm -qa |grep EMC); rm -rf /opt/emc/'
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install(nodes: list, build: str, debug: bool = True, signed: bool = False):
    # TODO: Change up to cluster creation to use gevents
    cluster_mode = 0
    build_list = list(build)
    build_list = [char.replace('-', '.') for char in build_list]
    if debug:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/debug/'.format(
            build=(''.join(build_list)))
    else:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/release/'.format(
            build=(''.join(build_list)))
    if signed:
        path += 'SIGNED/'
    mdm_ip_list = []
    for each_node in nodes:
        preinstall_cleanup(each_node)
        if each_node.is_mdm:
            install_mdm(each_node, build, path)
            mdm_ip_list.append(','.join(map(str, each_node.data_nics)))
            cluster_mode += 1
    for each_node in nodes:
        if each_node.is_sds:
            install_sds(each_node, build, path)
            each_node.logger.info('sds installed on {ip}'.format(ip=each_node.mgmt_ip))
        if each_node.is_sdc:
            mdm_ips = ','.join(mdm_ip_list)
            install_sdc(each_node, build, mdm_ips, path)
        if (each_node.is_sdc and each_node.is_mdm and each_node.is_sds) is False:
            each_node.logger.info('Why did you add node {mgmt_ip} then?!'.format(mgmt_ip=each_node.mgmt_ip))
    if (cluster_mode != 1) and (cluster_mode != 3) and (cluster_mode != 5):
        if cluster_mode == 4:
            logger.info('Incorrect amount of mdms: {node_amount}, creating 3_node cluster'.format(
                node_amount=cluster_mode))
        elif cluster_mode > 5:
            logger.info('Incorrect amount of mdms: {node_amount}, creating 5_node cluster'.format(
                node_amount=cluster_mode))
        else:
            logger.info(
                'Incorrect amount of mdms: {node_amount}, creating 1_node cluster'.format(node_amount=cluster_mode))
    create_cluster(nodes)


def auto_install(ips: list, build: str, mode: int = 1):
    nodes = []
    for each_ip in ips:
        nodes.append(NodeInInstall(each_ip, sds=True, sdc=True))
    if 3 <= mode < 5:
        num_of_managers = 2
        num_of_mdms = 3
    elif mode >= 5:
        num_of_managers = 3
        num_of_mdms = 5
    else:
        num_of_managers = 1
        num_of_mdms = 1
    for i in range(num_of_managers):
        nodes[i].is_manager = True
    for i in range(num_of_mdms):
        nodes[i].is_mdm = True
    install(nodes, build)


logger = logging.getLogger()
nodelist = [
         NodeInInstall('10.234.210.125', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.126', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.127', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.128', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.103', mdm=True, sds=True, sdc=True)]

ip_list = [
    '10.234.210.125',
    '10.234.210.126',
    '10.234.210.127',
    '10.234.210.128',
    '10.234.210.103']


siobuild = "3.0-0.769"
auto_install(ip_list, siobuild, 5)
# install(list_of_nodes, siobuild)
