from mininet.topo import Topo
from mininet.node import OVSSwitch


class OVSBridgeSTP(OVSSwitch):

    prio = 1000

    def start(self, *args, **kwargs):
        OVSSwitch.start(self, *args, **kwargs)
        OVSBridgeSTP.prio += 1
        self.cmd('ovs-vsctl set-fail-mode', self, 'standalone')
        self.cmd('ovs-vsctl set-controller', self)
        self.cmd('ovs-vsctl set Bridge', self,
                 'stp_enable=true',
                 'other_config:stp-priority=%d' % OVSBridgeSTP.prio)


switches = {'ovs-stp': OVSBridgeSTP}


class FatTree(Topo):

    def __init__(self):


        K = 4
        podNum = K
        coreSwitchNum = pow((K / 2), 2)
        aggrSwitchNum = ((K / 2) * K)
        edgeSwitchNum = ((K / 2) * K)
        hostNum = (K * pow((K / 2), 2))

        Topo.__init__(self)

        coreSwitches = []
        aggrSwitches = []
        edgeSwitches = []

        for core in range(0, coreSwitchNum):
            coreSwitches.append(self.addSwitch("cs_" + str(core)))

        for pod in range(0, podNum):

            for aggr in range(0, aggrSwitchNum / podNum):
                aggrThis = self.addSwitch("as_" + str(pod) + "_" + str(aggr))
                aggrSwitches.append(aggrThis)
                for x in range((K / 2) * aggr, (K / 2) * (aggr + 1)):

                    self.addLink(aggrThis, coreSwitches[x])

            for edge in range(0, edgeSwitchNum / podNum):
                edgeThis = self.addSwitch("es_" + str(pod) + "_" + str(edge))
                edgeSwitches.append(edgeThis)
                for x in range((edgeSwitchNum / podNum) * pod, ((edgeSwitchNum / podNum) * (pod + 1))):
                    self.addLink(edgeThis, aggrSwitches[x])

                for x in range(0, (hostNum / podNum / (edgeSwitchNum / podNum))):
                    self.addLink(edgeThis, self.addHost("h_" + str(pod) + "_" + str(edge) + "_" + str(x)))


topos = {'fattree': (lambda: FatTree())}