"""Installs SIO on the provided servers"""
from modules.SIOInstall.NodeInInstall import NodeInInstall
import warnings
import logging
from modules.Logger import logger_init
from modules import configuration

# Suppressing DeprecationWarnings
warnings.filterwarnings("ignore")
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG',
                                        log_to_file=False, executable_path=__file__)


def install_mdm(node: NodeInInstall, build: str, debug: bool = False):  # TODO: add debug installation
    build_list = list(build)
    build_list = [char.replace('_', '.') for char in build_list]
    if debug:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/debug/'.format(
            build=(''.join(build_list)))
    else:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/release/'.format(
            build=(''.join(build_list)))
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


def install_sds(node: NodeInInstall, build: str, debug: bool = False):
    build_list = list(build)
    build_list = [char.replace('_', '.') for char in build_list]
    if debug:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/debug/'.format(
            build=(''.join(build_list)))
    else:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/release/'.format(
            build=(''.join(build_list)))
    cmd_to_execute = "wget {path}EMC-ScaleIO-sds-{build}.el7.x86_64.rpm -nv".format(path=path, build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rpm -i EMC-ScaleIO-sds-{build}.el7.x86_64.rpm --force".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rm -rf EMC*".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install_sdc(node: NodeInInstall, build: str, mdm_ips: str, debug: bool = False):
    build_list = list(build)
    build_list = [char.replace('_', '.') for char in build_list]
    if debug:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/debug/'.format(
            build=(''.join(build_list)))
    else:
        path = 'http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/{build}/release/'.format(
            build=(''.join(build_list)))
    cmd_to_execute = "wget {path}EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm -nv".format(path=path, build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "MDM_IP={mdm_ips} rpm -i EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm --force".format(mdm_ips=mdm_ips,
                                                                                                     build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rm -rf EMC*".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def create_cluster(nodes: list, mode: str):  #TODO: refactor
    for each_node in nodes:
        if each_node.is_manager:
            master = each_node
            break
    mdm_ips = ''
    tb_ips = ''
    if mode == 1:
        cmd_to_execute = 'scli --create_mdm_cluster --master_mdm_ip {data_ip} --master_mdm_management_ip {mgmt_ip} ' \
                         '--accept_license --approve_certificate'.format(data_ip=','.join(map(str, master.data_nics)),
                                                                         mgmt_ip=str(master.mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
        cmd_to_execute = 'scli --login --username admin --password admin --approve_certificate; scli --set_password ' \
                         '--old_password admin --new_password Scaleio123; scli --login --username admin --password ' \
                         'Scaleio123 --approve_certificate'

        master.ssh_execute(cmd_to_execute=cmd_to_execute)
    elif mode == 3:
        cmd_to_execute = 'scli --create_mdm_cluster --master_mdm_ip {data_ip} --master_mdm_management_ip {mgmt_ip} ' \
                         '--accept_license --approve_certificate'.format(data_ip=','.join(map(str, master.data_nics)),
                                                                         mgmt_ip=str(master.mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
        cmd_to_execute = 'scli --login --username admin --password admin --approve_certificate; scli --set_password ' \
                         '--old_password admin --new_password Scaleio123; scli --login --username admin --password ' \
                         'Scaleio123 --approve_certificate'
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
        for each_node in nodes:
            if each_node is not master and each_node.is_manager:
                cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip} --mdm_role manager --new_mdm_' \
                                 'management_ip {mgmt_ip}'.format(data_ip=','.join(map(str, each_node.data_nics)),
                                                                  mgmt_ip=str(each_node.mgmt_ip))
                master.ssh_execute(cmd_to_execute=cmd_to_execute)
                mdm_ips += ','.join(map(str, each_node.data_nics))
            elif each_node is not master and each_node.is_manager is False and each_node.is_mdm:
                cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip}  ' \
                                 '--mdm_role tb'.format(data_ip=','.join(map(str, each_node.data_nics)))
                master.ssh_execute(cmd_to_execute=cmd_to_execute)
                tb_ips += ','.join(map(str, each_node.data_nics))
        cmd_to_execute = 'scli --switch_cluster_mode --cluster_mode 3_node --add_slave_mdm_ip {mdms} --add_tb_ip {tbs}'.\
            format(mdms=mdm_ips, tbs=tb_ips)
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
    else:
        cmd_to_execute = 'scli --create_mdm_cluster --master_mdm_ip {data_ip} --master_mdm_management_ip {mgmt_ip} ' \
                         '--accept_license --approve_certificate'.format(data_ip=','.join(map(str, master.data_nics)),
                                                                         mgmt_ip=str(master.mgmt_ip))
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
        cmd_to_execute = 'scli --login --username admin --password admin --approve_certificate; scli --set_password ' \
                         '--old_password admin --new_password Scaleio123; scli --login --username admin --password ' \
                         'Scaleio123 --approve_certificate'
        master.ssh_execute(cmd_to_execute=cmd_to_execute)
        for each_node in nodes:
            if each_node is not master and each_node.is_manager  and each_node.is_mdm:
                cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip} --mdm_role manager --new_mdm_' \
                                 'management_ip {mgmt_ip}'.format(data_ip=','.join(map(str, each_node.data_nics)),
                                                                  mgmt_ip=str(each_node.mgmt_ip))
                master.ssh_execute(cmd_to_execute=cmd_to_execute)
                mdm_ips += ','.join(map(str, each_node.data_nics))
            elif each_node is not master and each_node.is_manager is False:
                cmd_to_execute = 'scli --add_standby_mdm --new_mdm_ip {data_ip}  ' \
                                 '--mdm_role tb'.format(data_ip=','.join(map(str, each_node.data_nics)))
                master.ssh_execute(cmd_to_execute=cmd_to_execute)
                tb_ips += ','.join(map(str, each_node.data_nics))
        cmd_to_execute = 'scli --switch_cluster_mode --cluster_mode 5_node --add_slave_mdm_ip {mdms} --add_tb_ip {tbs}'.\
            format(mdms=mdm_ips, tbs=tb_ips)
        master.ssh_execute(cmd_to_execute=cmd_to_execute)


def preinstall_cleanup(node: NodeInInstall):
    cmd_to_execute = 'service scini stop; I_AM_SURE=1 rpm -e $(rpm -qa |grep EMC); rm -rf /opt/emc/'
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install(nodes: list, build: str):
    cluster_mode = 0
    for each_node in nodes:
        preinstall_cleanup(each_node)
        if each_node.is_mdm:
            install_mdm(each_node, build)
            mdm_ip_list.append(','.join(map(str, each_node.data_nics)))
            cluster_mode += 1
    for each_node in nodes:
        if each_node.is_sds:
            install_sds(each_node, build)
            each_node.logger.info('sds installed on {ip}'.format(ip=each_node.mgmt_ip))
        if each_node.is_sdc:
            mdm_ips = ','.join(mdm_ip_list)
            install_sdc(each_node, build, mdm_ips)
        if (each_node.is_sdc and each_node.is_mdm and each_node.is_sds) is False:
            each_node.logger.info('Why did you add node {mgmt_ip} then?!'.format(mgmt_ip=each_node.mgmt_ip))
    if (cluster_mode != 1) and (cluster_mode != 3) and (cluster_mode != 5):
        logger.debug('Incorrect amount of mdms: {node_amount}'.format(node_amount=cluster_mode))
    else:
        create_cluster(nodes, cluster_mode)


nodelist = [
         NodeInInstall('10.234.210.126', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.127', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.128', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.125')]

siobuild = "3.0-0.769"
mdm_ip_list = []
logger = logging.getLogger()

install(nodelist, siobuild)
