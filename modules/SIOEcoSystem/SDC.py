from modules.SIOEcoSystem.NodeGlobal import NodeGlobal
from modules.SIOEcoSystem.PhysNode import PhysNode


class SDC(NodeGlobal):
    def __init__(self, physnode: PhysNode):
        NodeGlobal.__init__(self, physnode)
        self.type = 'sdc'
        self.log_own_creation()
