#!/usr/bin/python
"""
Jellyfish Topology.

@author Han Lin
@author Zeyang Zhang
"""
import random

from mininet.log import lg
from mininet.topo import Topo

PORT_BASE = 1  # starting index for OpenFlow switch ports

class JellyfishNodeID(object):
  '''Topo node identifier.'''

  def __init__(self, switch_id=None, host_id=None, dpid=None, name=None):
    '''Init.

    @param switch_id
    @param host_id
    @param dpid dpid
    '''
    if name is not None:
      if name[0] == 'h':
        self.switch_id = int(name[1:])
        self.host_id = int(name[1:])
      elif name[0] == 's':
        self.switch_id = int(name[1:])
        self.host_id = 255
      self.dpid = (self.switch_id << 8) + self.host_id
    elif dpid is not None:
      self.switch_id = (dpid & 0xff00) >> 8
      self.host_id = (dpid & 0xff)
      self.dpid = dpid
    else:
      self.host_id = host_id
      self.switch_id = switch_id
      self.dpid = ((self.switch_id) << 8) + (self.host_id)

  def __str__(self):
    '''String conversion.

    @return str dpid as string
    '''
    if self.host_id == 255:
      return "s%d" % self.switch_id
    else:
      return "h%d" % self.host_id

  def name_str(self):
    '''Name conversion.

    @return name name as string
    '''
    return str(self)

  def ip_str(self):
    '''Name conversion.

    @return ip ip as string
    '''
    mid = (self.dpid & 0xff00) >> 8
    lo = self.dpid & 0xff
    return "10.0.%i.%i" % (mid, lo)

  def mac_str(self):
    mid = (self.dpid & 0xff00) >> 8
    lo = self.dpid & 0xff
    return "00:00:00:00:%02x:%02x" % (mid, lo)


class StructuredNodeSpec(object):
    '''Layer-specific vertex metadata for a StructuredTopo graph.'''

    def __init__(self, up_total, down_total, up_speed, down_speed,
                 type_str = None):
        '''Init.

        @param up_total number of up links
        @param down_total number of down links
        @param up_speed speed in Gbps of up links
        @param down_speed speed in Gbps of down links
        @param type_str string; model of switch or server
        '''
        self.up_total = up_total
        self.down_total = down_total
        self.up_speed = up_speed
        self.down_speed = down_speed
        self.type_str = type_str


class StructuredEdgeSpec(object):
    '''Static edge metadata for a StructuredTopo graph.'''

    def __init__(self, speed = 1.0):
        '''Init.

        @param speed bandwidth in Gbps
        '''
        self.speed = speed


class StructuredTopo(Topo):
    '''Data center network representation for structured multi-trees.'''

    def __init__(self, node_specs, edge_specs):
        '''Create StructuredTopo object.

        @param node_specs list of StructuredNodeSpec objects, one per layer
        @param edge_specs list of StructuredEdgeSpec objects for down-links,
            one per layer
        '''
        super(StructuredTopo, self).__init__()
        self.node_specs = node_specs
        self.edge_specs = edge_specs

    def def_nopts(self, layer):
        '''Return default dict for a structured topo.

        @param layer layer of node
        @return d dict with layer key/val pair
        '''
        return {'layer': layer}

    def layer(self, name):
        '''Return layer of a node

        @param name name of switch
        @return layer layer of switch
        '''
        return self.node_info[name]['layer']

    def isPortUp(self, port):
        ''' Returns whether port is facing up or down

        @param port port number
        @return portUp boolean is port facing up?
        '''
        return port % 2 == PORT_BASE

    def layer_nodes(self, layer):
        '''Return nodes at a provided layer.

        @param layer layer
        @return names list of names
        '''
        def is_layer(n):
            '''Returns true if node is at layer.'''
            return self.layer(n) == layer

        nodes = [n for n in self.g.nodes() if is_layer(n)]
        return nodes

    def up_nodes(self, name):
        '''Return edges one layer higher (closer to core).

        @param name name

        @return names list of names
        '''
        layer = self.layer(name) - 1
        nodes = [n for n in self.g[name] if self.layer(n) == layer]
        return nodes

    def down_nodes(self, name):
        '''Return edges one layer higher (closer to hosts).

        @param name name
        @return names list of names
        '''
        layer = self.layer(name) + 1
        nodes = [n for n in self.g[name] if self.layer(n) == layer]
        return nodes

    def up_edges(self, name):
        '''Return edges one layer higher (closer to core).

        @param name name
        @return up_edges list of name pairs
        '''
        edges = [(name, n) for n in self.up_nodes(name)]
        return edges

    def down_edges(self, name):
        '''Return edges one layer lower (closer to hosts).

        @param name name
        @return down_edges list of name pairs
        '''
        edges = [(name, n) for n in self.down_nodes(name)]
        return edges


# Topology to be instantiated in Mininet
class JellyfishTopo(StructuredTopo):
  "Jellyfish Topology."

  LAYER_EDGE = 2
  LAYER_HOST = 3

  def def_nopts(self, layer, name=None):
    '''Return default dict for a Jellyfish topo.

    @param layer layer of node
    @param name name of node
    @return d dict with layer key/val pair, plus anything else (later)
    '''
    d = {'layer': layer}
    if name:
      id = self.id_gen(name=name)
      # For hosts only, set the IP
      if layer == self.LAYER_HOST:
        d.update({'ip': id.ip_str()})
        d.update({'mac': id.mac_str()})
      d.update({'dpid': "%016x" % id.dpid})
    return d

  def __init__(self, seed=0, switches=16, nodes=4, ports_per_switch=4,
               hosts_per_switch=1, bw=40):
    # Add default members to class.
    self.bw = bw
    self.id_gen = JellyfishNodeID
    random.seed(seed)

    edge_specs = [StructuredEdgeSpec(bw)] * 3
    node_specs = [StructuredNodeSpec(ports_per_switch - hosts_per_switch,
                                     hosts_per_switch, bw, bw, 'edge'),
                  StructuredNodeSpec(1, 0, bw, None, 'host'),
                 ]

    super(JellyfishTopo, self).__init__(node_specs, edge_specs)

    self.create_topology(switches, nodes, ports_per_switch, hosts_per_switch)

  def not_fully_connected(self, switch_list, link_list):
    for i in range(len(switch_list)):
      switch = switch_list[i]
      for j in range(i + 1, len(switch_list)):
        switch2 = switch_list[j]
        link = (switch, switch2)
        if link not in link_list and (switch2, switch) not in link_list:
          return True
    return False

  def addHosts(self, switches, nodes, ports_per_switch, hosts_per_switch):
    switch_num = 1
    host_list = []
    for num in range(0, nodes):
      host_id = self.id_gen(num+1, num+1).name_str()
      host_opts = self.def_nopts(self.LAYER_HOST, host_id)
      h = self.addHost(host_id, **host_opts)
      lg.debug("Adding host: %s\n" % (host_id))
      host_list.append(h)
      if num % hosts_per_switch == 0:
        switch_id = self.id_gen(switch_num, 255).name_str()
        switch_opts = self.def_nopts(self.LAYER_EDGE, switch_id)
        switch = self.addSwitch(switch_id, **switch_opts)
        lg.debug("Adding switch: %s\n" % (switch_id))
        for host in host_list:
          self.addLink(host, switch, bw=self.bw)
          lg.debug("Adding link: %s to %s\n" % (str(host), str(switch)))
        host_list = []
        switch_num += 1

    for num in range(nodes / hosts_per_switch, switches):
      switch_id = self.id_gen(num+1, 255).name_str()
      lg.debug("Adding switch: %s\n" % (switch_id))
      switch_opts = self.def_nopts(self.LAYER_EDGE, switch_id)
      switch = self.addSwitch(switch_id, **switch_opts)

  def count_links_with_switch(self, switch, link_list):
    count = 0
    for link in link_list:
      if switch in link:
        count += 1
    return count

  def up_nodes(self, name):
    '''Return edges one layer higher (closer to core).

    @param name name

    @return names list of names
    '''
    return [n for n in self.g[name] if self.isSwitch(n)]

  def down_nodes(self, name):
    '''Return edges one layer higher (closer to hosts).

    @param name name
    @return names list of names
    '''
    layer = self.layer(name) + 1
    nodes = [n for n in self.g[name] if self.layer(n) == layer]
    return nodes

  def switch_is_fully_connected(self, switch, links, switches):
    for s in switches:
      if s == switch:
        continue
      if (switch, s) not in links or (s, switch) not in links:
        return False
    return True

  def create_topology(self, switches, nodes, ports_per_switch, hosts_per_switch):

    self.addHosts(switches, nodes, ports_per_switch, hosts_per_switch)
    switch_list = list(self.switches())
    added_links = []
    while len(switch_list) > 1 and self.not_fully_connected(switch_list, added_links):
      switch = random.choice(switch_list)
      switch2 = random.choice(switch_list)
      if switch == switch2:
        continue
      link = (switch, switch2)
      if link in added_links or (switch2, switch) in added_links:
        continue
      added_links.append(link)
      if (self.count_links_with_switch(switch, added_links) == ports_per_switch or
         self.switch_is_fully_connected(switch, added_links, switch_list)):
        switch_list.remove(switch)
      if (self.count_links_with_switch(switch2, added_links) == ports_per_switch or
         self.switch_is_fully_connected(switch2, added_links, switch_list)):
        switch_list.remove(switch2)

    print (added_links)
    print (switch_list)
    while True:
      completed = True
      for switch in switch_list:
        if self.switch_is_fully_connected(switch, added_links, switch_list):
          continue
        if self.count_links_with_switch(switch, added_links) < (ports_per_switch-1):
          completed = False
          link = random.choice(added_links)
          if switch == link [0] or switch == link[1]:
            continue
          new_link1 = (switch, link[0])
          new_link2 = (switch, link[1])
          added_links.remove(link)
          added_links.append(new_link1)
          added_links.append(new_link2)
      if completed:
        break

    for link in added_links:
      self.addLink(link[0], link[1], bw=self.bw)

topos = {'jellyfish': JellyfishTopo}

if __name__ == '__main__':
  pass
