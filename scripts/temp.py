import ipaddress
from modules.SIOHardwareHandler.main_classes import MDM, SDS, SDC
from modules.SIOHardwareHandler.hardware_handler import SIONodeHandler


# Initializing hardware environment
SIONodeHandler = SIONodeHandler(mdms=[
    {'node_ip': '10.139.218.26',
     'user': 'root',
     'password': 'password'},
    {'node_ip': '10.139.218.27'}])


for hostname, components in SIONodeHandler.known_hosts.items():
        for each_component in components:
            print(each_component.installation_package)







