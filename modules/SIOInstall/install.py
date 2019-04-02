"""
This module allow you to install SIO on provided server list. It allows to install normal and debug version. Allows yo use signed and unsigned packages.
Uasge:
    Manual install:
        Use install function and provide needed arguments to specify details for system installation.

    Auto install:
        Use auto_install with lists of ips, build and mode to install SIO system automatically on provided ip list.
"""

from modules.SIOInstall.NodeInInstall import NodeInInstall
from modules.SIOInstall.SIOSystem import SIOSystem
import warnings
import logging
from modules.Logger import logger_init
from modules import configuration
import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Suppressing DeprecationWarnings
warnings.filterwarnings("ignore")
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='INFO',
                                        log_to_file=False, executable_path=__file__)


def install_mdm(node: NodeInInstall, build: str, path: str):
    """
    Installs mdm components on a server

    :param node: information about the server stored in NodeInstall class
    :param build: a string value of a build number, should be passed as x.x-x.x
    :param path: a string value for the path where to download distributions
    :return:
    """
    command_list = []
    command_list.append("wget {path}EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm -nv".format(path=path, build=build))
    if node.is_manager:
        command_list.append("MDM_ROLE_IS_MANAGER=1 rpm -i EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm".format(build=build))
    else:
        command_list.append("MDM_ROLE_IS_MANAGER=0 rpm -i EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm".format(build=build))
    command_list.append("echo -e '\\user session hard timeout secs=2592000\\user session timeout secs=2592000' >> "
                        "/opt/emc/scaleio/mdm/cfg/conf.txt; pkill mdm")
    command_list.append("rm -rf EMC*")
    return command_list


def install_sds(build: str, path: str):
    """
    Installs sds components on a server

    :param build: a string value of a build number, should be passed as x.x-x.x
    :param path: a string value for the path where to download distributions
    :return:
    """
    command_list = []
    #node.logger.info('Starting SDS install task for {ip}'.format(str(node.mgmt_ip)))
    command_list.append("wget {path}EMC-ScaleIO-sds-{build}.el7.x86_64.rpm -nv".format(path=path, build=build))
    command_list.append("rpm -i EMC-ScaleIO-sds-{build}.el7.x86_64.rpm --force".format(build=build))
    command_list.append("rm -rf EMC*")
    return command_list


def install_sdc(build: str, mdm_ips: str, path: str):
    """
    Installs sdc components on a server

    :param build: a string value of a build number, should be passed as x.x-x.x
    :param mdm_ips: string of mdm ips for SDC to be added to
    :param path: a string value for the path where to download distributions
    :return:
    """
    command_list = []
    #node.logger.info('Starting SDC install task for {ip}'.format(str(node.mgmt_ip)))
    command_list.append("wget {path}EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm -nv".format(path=path, build=build))
    command_list.append("MDM_IP={mdm_ips} rpm -i EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm --force".format(mdm_ips=mdm_ips,
                                                                                                        build=build))
    command_list.append("rm -rf EMC*")
    return command_list


def add_slave_mdm(master: NodeInInstall, slave: SIOSystem):
    """
    Adds a slave mdmd to the SIO cluster

    :param master: NodeInInstall class object, contains server which is SIO cluster master for now
    :param slave: SIOSystem class object, contains information about server, which wil be added as slave mdm
    :return:
    """
    cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip} --mdm_role manager --new_mdm_' \
                     'management_ip {mgmt_ip} --new_mdm_name MDM_{mgmt_ip}'.format(data_ip=','.join(slave.data_nics),
                                                                                   mgmt_ip=str(slave.mgmt_ip))
    master.ssh_execute(cmd_to_execute=cmd_to_execute)


def add_tb(master: NodeInInstall, tb: SIOSystem):
    """
    Adds a Tie Braker to the SIO cluster

    :param master: NodeInInstall class object, contains server which is SIO cluster master for now
    :param tb: SIOSystem class object, contains information about server, which wil be added as TB
    :return:
    """
    cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip} --mdm_role tb --new_mdm_name TB_{mgmt_ip}'.format(
        data_ip=','.join(tb.data_nics), mgmt_ip=str(tb.mgmt_ip))
    master.ssh_execute(cmd_to_execute=cmd_to_execute)


def create_cluster(nodes: list):
    """
    Creates a cluster from a provided list of servers

    :param nodes: a list of NodeInIntall class objects
    :return:
    """
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


def run_ssh_command(node: NodeInInstall, command_list: list):
    for each_command in command_list:
        node.ssh_execute(cmd_to_execute=each_command)


def preinstall_cleanup():
    """
    wipes out SIO components and log directories

    :param node: NodeInInstall object
    :return:
    """
    cmd_to_execute = 'service scini stop; I_AM_SURE=1 rpm -e $(rpm -qa |grep EMC); rm -rf /opt/emc/'
    return cmd_to_execute


def install(nodes: list, build: str, debug: bool = True, signed: bool = False):
    """
     wipes out SIO components and log directories

    :param nodes: list of NodeInInstall class objects
    :param build: a string value of a build number, should be passed as x.x-x.x
    :param debug: True if you want to install debug version
    :param signed: True if you want to isntall signed package version
    :return:
    """
    MAX_WORKERS = 8
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    fs = []
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
    nodes_commands = {}
    for each_node in nodes:
        nodes_commands[each_node] = [preinstall_cleanup()]
        if each_node.is_mdm:
            nodes_commands[each_node] += install_mdm(each_node, build, path)
            mdm_ip_list.append(str(each_node.data_nic_a))
            cluster_mode += 1
    for each_node in nodes:
        if each_node.is_sds:
            nodes_commands[each_node] += install_sds(build, path)
        if each_node.is_sdc:
            mdm_ips = ','.join(mdm_ip_list)
            nodes_commands[each_node] += install_sdc(build, mdm_ips, path)
        if (each_node.is_sdc and each_node.is_mdm and each_node.is_sds) is False:
            each_node.logger.info('Why did you add node {mgmt_ip} then?!'.format(mgmt_ip=each_node.mgmt_ip))
        fs.append(executor.submit(run_ssh_command, each_node, nodes_commands[each_node]))
    concurrent.futures.wait(fs, timeout=None, return_when='ALL_COMPLETED')
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


def old_install(nodes: list, build: str, debug: bool = True, signed: bool = False):
    """
     wipes out SIO components and log directories

    :param nodes: list of NodeInInstall class objects
    :param build: a string value of a build number, should be passed as x.x-x.x
    :param debug: True if you want to install debug version
    :param signed: True if you want to isntall signed package version
    :return:
    """

    # TODO: Change up to cluster creation to use gevents
    MAX_WORKERS = 8
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    fs = []
    for each_node in nodes:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as execute:
            execute.submit(preinstall_cleanup, each_node)
    for each_node in nodes:
        if each_node.is_mdm:
            fs.append(executor.submit(install_mdm, each_node, build, path))
            mdm_ip_list.append(str(each_node.data_nic_a))
            cluster_mode += 1
            each_node.logger.info('Installing mdm on {ip}'.format(ip=each_node.mgmt_ip))
    for each_node in nodes:
        if each_node.is_sds:
            fs.append(executor.submit(install_sds, each_node, build, path))
            each_node.logger.info('sds installed on {ip}'.format(ip=each_node.mgmt_ip))
        if each_node.is_sdc:
            mdm_ips = ','.join(mdm_ip_list)
            fs.append(executor.submit(install_sdc, each_node, build, mdm_ips, path))
            each_node.logger.info(
                'added sdc on ip: {ip}, mdm_ips are: {mdm_ips}'.format(ip=each_node.mgmt_ip, mdm_ips=mdm_ips))
        if (each_node.is_sdc and each_node.is_mdm and each_node.is_sds) is False:
            each_node.logger.info('Why did you add node {mgmt_ip} then?!'.format(mgmt_ip=each_node.mgmt_ip))
    logger.info('WAITING FOR THREADS TO FINISH!')
    concurrent.futures.wait(fs, timeout=None, return_when='ALL_COMPLETED')
    end_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    logger.info('Start time: {start}, \n end time: {end}'.format(start=start_time, end=end_time))


def auto_install(ips: list, build: str, mode: int = 1):
    """
    This function automatically assigns roles compatible with SIO cluster creation.
    All servers will have SDS and SDC roles installed

    :param ips: list of ips where SIO components should be installed
    :param build: a string value of a build number, should be passed as x.x-x.x
    :param mode: select a cluster mode for SIO, correct values: 1, 3 or 5
    :return:
    """
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
         NodeInInstall('10.139.218.26', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.27', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.28', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.29', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.30', mdm=True, sds=True, sdc=True)]

ip_list = [
    '10.139.218.26',
    '10.139.218.27',
    '10.139.218.28',
    '10.139.218.29',
    '10.139.218.30']


siobuild = "3.0-0.769"
#auto_install(ip_list, siobuild, 5)
#install(list_of_nodes, siobuild)
install(nodelist, siobuild)
