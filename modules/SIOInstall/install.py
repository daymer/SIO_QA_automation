"""
This module allows you to install SIO on provided server list. It allows to install normal and debug version. Allows yo use signed and unsigned packages.
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


def install_mdm(node: NodeInInstall, build: str, path: str) -> list:
    """
    Generates a list of commands to install mdm

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


def install_sds(build: str, path: str) -> list:
    """
    Generates a list of commands to install sds

    :param build: a string value of a build number, should be passed as x.x-x.x
    :param path: a string value for the path where to download distributions
    :return:
    """
    command_list = []
    command_list.append("wget {path}EMC-ScaleIO-sds-{build}.el7.x86_64.rpm -nv".format(path=path, build=build))
    command_list.append("rpm -i EMC-ScaleIO-sds-{build}.el7.x86_64.rpm --force".format(build=build))
    command_list.append("rm -rf EMC*")
    return command_list


def install_sdc(build: str, mdm_ips: str, path: str) -> list:
    """
    Generates a list of commands to install sdc

    :param build: a string value of a build number, should be passed as x.x-x.x
    :param mdm_ips: string of mdm ips for SDC to be added to
    :param path: a string value for the path where to download distributions
    :return:
    """
    command_list = []
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
            system = [SIOSystem(role='master', node_ip=each_node.mgmt_ip, data_nic=each_node.data_nics,
                                hdds=each_node.hdds, ssds=each_node.ssds, pmem=each_node.pmem, dax=each_node.dax)]
            break
    for each_node in nodes:
        if each_node is not master:
            if each_node.is_mdm and each_node.is_manager:
                system.append(SIOSystem(role='manager', node_ip=each_node.mgmt_ip, data_nic=each_node.data_nics,
                                        hdds=each_node.hdds, ssds=each_node.ssds, pmem=each_node.pmem,
                                        dax=each_node.dax))
            elif each_node.is_mdm and each_node.is_manager is False:
                system.append(SIOSystem(role='tb', node_ip=each_node.mgmt_ip, data_nic=each_node.data_nics,
                                        hdds=each_node.hdds, ssds=each_node.ssds, pmem=each_node.pmem,
                                        dax=each_node.dax))
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
        cmd_to_execute = 'scli --switch_cluster_mode --cluster_mode 3_node --add_slave_mdm_name MDM_{slave_name} ' \
                         '--add_tb_name TB_{tb_name}'.format(slave_name=str(slave.mgmt_ip),
                                                             tb_name=str(tb.mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
    elif mode >= 5:
        slaves = []
        tiebrakers = []
        for i in range(2):
            slaves.append(managers[i])
            add_slave_mdm(master, slaves[i])
            tiebrakers.append(tbs[i])
            add_tb(master, tbs[i])
        cmd_to_execute = 'scli --switch_cluster_mode --cluster_mode 5_node --add_slave_mdm_name MDM_{slave1},' \
                         'MDM_{slave2} --add_tb_name TB_{tb1},TB_{tb2}'.format(slave1=str(slaves[0].mgmt_ip),
                                                                               slave2=str(slaves[1].mgmt_ip),
                                                                               tb1=str(tiebrakers[0].mgmt_ip),
                                                                               tb2=str(tiebrakers[1].mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
    # Creation of PD, SP
    spef = True
    cmd_to_execute = 'scli --add_protection_domain --protection_domain_name pd1'
    master.ssh_execute(cmd_to_execute=cmd_to_execute)
    for each_node in nodes:
        if not len(each_node.dax) or not len(each_node.ssds):
            spef = False
    if spef:
        cmd_to_execute = 'scli --add_acceleration_pool --acceleration_pool_name accp --protection_domain_name pd1 ' \
                          '--media_type NVDIMM; '
        cmd_to_execute += 'scli --add_storage_pool --protection_domain_name pd1 --storage_pool_name SPEF ' \
                          '--media_type SSD --data_layout fine_granularity --compression_method normal '  \
                          '--fine_granularity_acceleration_pool_name accp; '
        cmd_to_execute += 'scli --add_storage_pool --protection_domain_name pd1 --storage_pool_name sp1 ' \
                          '--media_type HDD'
    else:
        cmd_to_execute = 'scli --add_storage_pool --protection_domain_name pd1 --storage_pool_name sp1 --media_type HDD; '
        cmd_to_execute += 'scli --add_storage_pool --protection_domain_name pd1 --storage_pool_name sp2 --media_type SSD'
    master.ssh_execute(cmd_to_execute=cmd_to_execute)
    # adding SDS
    cmd_to_execute = add_sds(nodes, spef)
    master.ssh_execute(cmd_to_execute=cmd_to_execute)


def add_sds(nodes: list, spef: bool = False) -> str:
    """
    This function allows to add SDS to the cluster, in case of SPEF, SPEF storage pool will be created
    and all SDS with SSDS added to it.

    :param nodes: a list of NodeInIntall class objects
    :param spef: If True means that cluster supports SPEF and SPEF SP shoudl be created
    :return: command line to execute which will add sds to the cluster
    """
    cmd = ''
    if len(nodes[0].hdds):
        sp = 'sp1'
    else:
        sp = 'sp2'
    for each_node in nodes:
        if each_node.is_sds:
            if spef:
                cmd += "scli --add_sds --sds_name {name} --sds_ip {ip} --device_path {devices} --force_device_takeover " \
                       "--protection_domain_name pd1 --storage_pool_name SPEF --media_type SSD " \
                       "--acceleration_device_path {dax} --acceleration_pool_name accp --force_clean --i_am_sure; ".format(
                        name=each_node.pretty_name, ip=','.join(each_node.data_nics), devices=','.join(each_node.ssds),
                        dax=','.join(each_node.dax))
                cmd += add_sds_device(nodes, 'hdd', 'sp1')
            else:
                if sp == 'sp1':
                    cmd += "scli --add_sds --sds_ip {ip} --device_path {hdds} --storage_pool_name {sp} " \
                       "--protection_domain_name pd1 --sds_name {name} --force_device_takeover; ".format(name=each_node.pretty_name,
                                                                                                         ip=','.join(each_node.data_nics),
                                                                                                         hdds=','.join(each_node.hdds),
                                                                                                         sp=sp)
                    cmd += add_sds_device(nodes, 'ssd', 'sp2')
                else:
                    cmd += "scli --add_sds --sds_ip {ip} --device_path {ssds} --storage_pool_name {sp} " \
                           "--protection_domain_name pd1 --sds_name {name} --force_device_takeover; ".format(
                        name=each_node.pretty_name,
                        ip=','.join(each_node.data_nics),
                        ssds=','.join(each_node.ssds), sp=sp)
                    cmd += add_sds_device(nodes, 'hdd', 'sp1')
    return cmd


def add_sds_device(nodes: list, dev: str, sp: str):
    """
    This function adds all devices of certain type to the SDS and provided storage pool

    :param nodes: a list of NodeInIntall class objects
    :param dev: type of device, allowed values: hdd, ssd
    :param sp: storage pool name
    :return:  command line to execute which will add devices to the sds
    """
    cmd = ''
    for each_node in nodes:
        if dev == 'hdd':
            for each_hdd in each_node.hdds:
                cmd += "scli --add_sds_device --storage_pool_name {sp} --sds_name {name} --device_path {devices} " \
                       "--force_device_takeover; ".format(sp=sp, name=each_node.pretty_name, devices=each_hdd)
        elif dev == 'ssd':
            for each_ssd in each_node.ssds:
                cmd += "scli --add_sds_device --storage_pool_name {sp} --sds_name {name} --device_path {devices} " \
                   "--force_device_takeover; ".format(sp=sp, name=each_node.pretty_name, devices=each_ssd)
    return cmd


def run_ssh_command(node: NodeInInstall, command_list: list):
    """
    Executes provided list of ssh commands

    :param node: NodeInInstall class object with the target server for ssh commands
    :param command_list: list of ssh commands
    :return:
    """
    for each_command in command_list:
        result = node.ssh_execute(cmd_to_execute=each_command)
        node.logger.info('Command to execute: {cmd}'.format(cmd=each_command))
        node.logger.info('status of the command: {res}'.format(res=result['status']))


def preinstall_cleanup():
    """
    Provides the command to wipe out SIO components and log directories

    :return:
    """
    cmd_to_execute = 'service scini stop; I_AM_SURE=1 rpm -e $(rpm -qa |grep EMC); rm -rf /opt/emc/'
    return cmd_to_execute


def install(nodes: list, build: str, debug: bool = True, signed: bool = False):
    """
     Wipes out SIO components and installs provided build with cluster creation

    :param nodes: list of NodeInInstall class objects
    :param build: a string value of a build number, should be passed as x.x-x.x
    :param debug: True if you want to install debug version
    :param signed: True if you want to isntall signed package version
    :return:
    """
    max_workers = 8
    executor = ThreadPoolExecutor(max_workers=max_workers)
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


def auto_install(ips: list, build: str, mode: int = 1, debug: bool = True, signed: bool = False):
    """
    This function automatically assigns roles compatible with SIO cluster creation.
    All servers will have SDS and SDC roles installed

    :param ips: list of ips where SIO components should be installed
    :param build: a string value of a build number, should be passed as x.x-x.x
    :param mode: select a cluster mode for SIO, correct values: 1, 3 or 5
    :param debug: True if you want to install debug version
    :param signed: True if you want to isntall signed package version
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
    install(nodes, build, debug, signed)


def validate(nodes: list):
    """
    Verifies that provided list has minimal required amount of mdms and managers

    :param nodes: a list of NodeInInstall objects
    :return: a list of verified NodeInInstall objects
    """
    mdm = 0
    manager = 0
    for each_node in nodes:
        if each_node.is_mdm:
            mdm += 1
        elif each_node.is_manager:
            manager += 1
    for each_node in nodes:
        if mdm == 0:
            if each_node.is_mdm is False:
                each_node.is_mdm = True
                mdm += 1
        if manager == 0:
            if each_node.is_manager is False:
                each_node.is_manager = True
                manager += 1
        if each_node.is_manager is True and each_node.is_mdm is False:
            each_node.is_mdm = True
            mdm += 1
        if manager > mdm:
            if each_node.is_mdm is False:
                each_node.is_mdm = True
                mdm += 1
    return nodes


logger = logging.getLogger()
nodelist = [
         NodeInInstall('10.139.218.26', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.27', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.28', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.29', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.30', mdm=True, sds=True, sdc=True)]

nods = [
         NodeInInstall('10.139.218.26', manager=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.27', manager=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.28', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.29', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.139.218.30', mdm=True, sds=True, sdc=True)]
"""
nods = [
         NodeInInstall('10.234.179.90', manager=True, sds=True, sdc=True),
         NodeInInstall('10.234.179.91', manager=True, sds=True, sdc=True),
         NodeInInstall('10.234.179.92', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.179.93', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.179.94', mdm=True, sds=True, sdc=True)]
"""
ip_list = [
    '10.139.218.26',
    '10.139.218.27',
    '10.139.218.28',
    '10.139.218.29',
    '10.139.218.30']

#ip_list = [
#'10.234.214.123',
#'10.234.214.124',
#'10.234.214.125']


siobuild = "3.0-100.124"
auto_install(ip_list, siobuild, 5, True, True)
#install(list_of_nodes, siobuild)
#nods = validate(nods)
#install(nods, siobuild)
