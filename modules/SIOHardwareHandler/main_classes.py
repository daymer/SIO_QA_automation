from abc import ABCMeta
import ipaddress


class NodeGlobal(object):
    __metaclass__ = ABCMeta

    def __init__(self, node_ip: ipaddress):
        self.node_ip = node_ip
        pass


class MDM(NodeGlobal):
    def __init__(self, **kwargs):
        NodeGlobal.__init__(self, kwargs['node_ip'])
        pass


class SDS(NodeGlobal):
    def __init__(self, **kwargs):
        NodeGlobal.__init__(self, kwargs['node_ip'])
        pass


class SDC(NodeGlobal):
    def __init__(self, **kwargs):
        NodeGlobal.__init__(self, kwargs['node_ip'])
        pass
