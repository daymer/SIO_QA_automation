"""Installs SIO on the provided servers"""
from modules.SIOInstall.NodeInInstall import NodeInInstall
import warnings
import logging
from modules.Logger import logger_init
from modules import configuration

# Suppressing DeprecationWarnings
warnings.filterwarnings("ignore")
IntegrationConfigInstance = configuration.Integration()
MainLogger = logger_init.logging_config(integration_config=IntegrationConfigInstance, logging_mode='DEBUG', log_to_file=False, executable_path=__file__)

def install_mdm(node: NodeInInstall, build: str):  # TODO: add debug installation
    cmd_to_execute = "wget http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/3.0.0.769/release/EMC-ScaleIO-mdm-{build}.el7.x86_64.rpm -nv".format(
        build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    if node.is_manager:
        cmd_to_execute = "MDM_ROLE_IS_MANAGER=1 rpm -i EMC-ScaleIO-mdm-$build.el7.x86_64.rpm"
    else:
        cmd_to_execute = "MDM_ROLE_IS_MANAGER=0 rpm -i EMC-ScaleIO-mdm-$build.el7.x86_64.rpm"
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    #cmd_to_execute = "echo - e '\user_session_hard_timeout_secs=2592000\user_session_timeout_secs=2592000' >> / opt / emc / scaleio / mdm / cfg / conf.txt; pkill mdm"
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install_sds(node: NodeInInstall, build):
    cmd_to_execute = "wget http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/3.0.0.769/release/EMC-ScaleIO-sds-{build}.el7.x86_64.rpm -nv".format(
        build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "rpm -i EMC-ScaleIO-sds-$build.el7.x86_64.rpm --force".format(build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def install_sdc(node: NodeInInstall, build, mdm_ips: str):
    cmd_to_execute = "wget http://vm-jenkins.lss.emc.com/sw_dev/Artifacts/Build-All-OEL7/3.0.0.769/release/EMC-ScaleIO-sdc-{build}.el7.x86_64.rpm -nv".format(
        build=build)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)
    cmd_to_execute = "MDM_IP={mdm_ips} rpm -i EMC-ScaleIO-sdc-$build.el7.x86_64.rpm --force".format(mdm_ips=mdm_ips)
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


def preinstall_cleanup(node: NodeInInstall):
    cmd_to_execute = 'service scini stop; I_AM_SURE=1 rpm -e $(rpm -qa |grep EMC); rm -rf /opt/emc/'
    node.ssh_execute(cmd_to_execute=cmd_to_execute)


nodes = [NodeInInstall('10.234.210.126', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.127', manager=True, mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.128', mdm=True, sds=True, sdc=True),
         NodeInInstall('10.234.210.103')]
siobuild = "3.0-0.769"
mdm_ip_list = []
logger = logging.getLogger()

for each_node in nodes:
    #preinstall_cleanup(each_node)
    if each_node.is_mdm:
        install_mdm(each_node, siobuild)
        mdm_ip_list.append(','.join(map(str, each_node.data_nics)))
for each_node in nodes:
    if each_node.is_sds:
        install_sds(each_node, siobuild)
    if each_node.is_sdc:
        mdm_ips = ','.join(mdm_ip_list)
        install_sdc(each_node, siobuild, mdm_ips)
    if each_node.is_sdc and each_node.is_mdm and each_node.is_sds is False:
        each_node.logger.debug('Why did you add node {mgmt_ip} then?!'.format(mgmt_ip=each_node.mgmt_ip))
