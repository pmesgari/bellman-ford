from typing import Dict, List, Tuple
import argparse
from prettytable import PrettyTable
from helpers import get_files


ROUND_SEP = "-----\n"


class Node:
    def __init__(self,
                 name: str,
                 topology: 'Topology') -> None:
        self.name = name
        self.topology = topology
        self.incoming_links: Dict[str, int] = {}
        self.outgoing_links: Dict[str, int] = {}
        self.dv: Dict[str, int] = {self.name: 0}
        self.messages: List[Tuple[str, Dict[str, int]]] = []

    def __str__(self) -> str:
        outgoing_links_str = ""
        for name, weight in self.outgoing_links.items():
            outgoing_links_str += f"({name}, {weight}) "
        incoming_links_str = ""
        for name, weight in self.incoming_links.items():
            incoming_links_str += f"({name}, {weight}) "
        return (
            f"Node {self.name}: "
            f"outgoing links {outgoing_links_str if outgoing_links_str else '()'} "
            f"incoming links {incoming_links_str if incoming_links_str else '()'}")
    
    def reset_dv(self):
        self.dv = {self.name: 0}

    def set_neighbor(self, node: 'Node', weight: int):
        self.link_to(node.name, weight)
        node.link_from(self.name, weight)
    
    def link_to(self, node: str, weight: int):
        self.outgoing_links[node] = weight

    def link_from(self, node: str, weight: int):
        self.incoming_links[node] = weight

    def unlink(self, node: str):
        """Unlink the current node from the given node.
        This means if there is an outgoing link from the current node
        to the given node, it will be removed from the outgoing links.
        """
        self.outgoing_links = {key: val for key, val in self.outgoing_links.items() if key != node}


    def send_initial_messages(self):
        for neighbor in self.incoming_links.keys():
            self.send_message((self.name, self.dv), neighbor)

    def send_message(self, message, dest):
        self.topology.nodes[dest].queue_message(message)

    def queue_message(self, message):
        self.messages.append(message)

    def run_bellman_ford(self):
        vector = {}
        for key, value in self.dv.items():
            vector[key] = value

        for message in self.messages:
            sender, dv = message
            for node, weight in dv.items():
                if node == self.name:
                    continue
                elif node in self.dv and weight == -99:
                    self.dv[node] = -99
                else:
                    min_weight = min(
                        int(self.outgoing_links[sender]) + weight,
                        self.dv.get(node, float('inf'))
                    )
                    self.dv[node] = -99 if min_weight <= -99 else min_weight
        
        self.messages = []

        if vector != self.dv:
            for name, weight in self.incoming_links.items():
                self.send_message((self.name, self.dv), name)

    def log_distances(self):
        distances = ','.join([f"{key}{value}" for key, value in self.dv.items()])
        self.topology.add_log_entry(self.name, distances)
        # print(f"{self.name}: {distances}")

class Topology:
    def __init__(self, debug=False, logfile='out.txt') -> None:
        self.nodes: Dict[str, Node] = {}
        self.logs: Dict[str, str] = {}
        self.debug = debug
        self.logfile = logfile
        # we just open the file once to clear its content
        with open(logfile, 'w') as _:
            self.logfile = logfile

    def __str__(self) -> str:
        sep = '\n'
        return f"Topology: \n{sep.join([str(node) for _, node in self.nodes.items()])}"
    
    def clear(self):
        """Clears the topology of all nodes and truncates the log file"""
        self.nodes = {}
        self.logs = {}
        # we just open the file once to clear its content
        with open(self.logfile, 'w') as _:
            pass

    def get_node(self, name) -> Node:
        return self.nodes[name]
    
    def add_edge(self, start, end, weight=0):
        """
        Add an edge and register the incoming and outgoing links for both sides.
        A --> B with weight 2 means:
            * A has an outgoing link to B with weight 2
            * B has an incoming link from A with weight 2
        A < -- > B with weight 2 means:
            * A has an outgoing to B with weight 2
            * A has an incoming link from B with weight 2
            * B has an outgoing link to A with weight 2
            * B has an incoming link from A with weight 2
        """
        if start not in self.nodes:
            self.nodes[start] = Node(start, self)
        if end not in self.nodes:
            self.nodes[end] = Node(end, self)
        self.nodes[start].set_neighbor(self.nodes[end], weight)

    def update_edge(self, start, end, weight):
        """Update the weight for the edge"""
        self.nodes[start].set_neighbor(self.nodes[end], weight)
        self.reset_nodes()

    def reset_nodes(self):
        for _, node in self.nodes.items():
            node.reset_dv()

    def from_config_file(self, config_file):
        """Create a topology by reading the given config file."""
        with open(config_file, 'r') as f:
            lines = f.read().splitlines()
            # ignore comment lines
            lines = [line for line in lines if not line.startswith('#')]
        def chunks(l, n):
            for i in range(0, len(l), n):
                yield l[i: i+n]
        lines = [line.split(',') for line in lines]
        for line in lines:
            head, *tail = line
            for ch in chunks(tail, 2):
                end, weight = ch
                self.add_edge(head, end, weight)
        
    def run(self):
        """Run the topology"""
        for _, node in self.nodes.items():
            node.send_initial_messages()

        done = False
        while not done:
            for _, node in self.nodes.items():
                node.run_bellman_ford()
                node.log_distances()
            
            self.print_logs()

            done = True
            for _, value in self.nodes.items():
                if len(value.messages) != 0:
                    done = False
                    break

    def add_log_entry(self, node, logstring):
        self.logs[node] = logstring
        if self.debug:
            print(f'{node}: {logstring}')

    def print_logs(self):
        nodes = sorted(list(self.logs.keys()))
        with open(self.logfile, 'a') as f:
            for node in nodes:
                f.write(f'{node}: {self.logs[node]} \n')
            f.write(ROUND_SEP)

class CLI:
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('--mode', help='Select a mode to run, possible options are interactive, from_file')
        self.parser.add_argument('--filename', help='Specify the topology filename')
        self.parser.add_argument('--debug', help='Run topology in debug mode', action='store_true', default=False)

    @staticmethod
    def print_help_menu():
        BOLD = '\033[1m'
        END = '\033[0m'
        help_menu = {
            'add edge <start:str> <end:str> <weight:int>': 'Adds an edge to the topology.',
            'update edge <start:str> <end:str> <weight:int>': 'Updates the weight for the edge between start and end nodes.',
            'node down <nodename:str>': 'Brings down the node by assigning an infinit weight to all incoming links.',
            'list': 'Displays a list of available topologies',
            'load topology <filename:str>': 'Loads a topology from the given filename.',
            'run': 'Run the distributed Bellman Ford algorithm on the topology.',
            'display dv, dv': 'Prints the current distance vector.',
            'display topology, topology': 'Prints the topology.',
            'quit': 'Exits the application.'
        }
        print(
            f"Distributed Bellman Ford Interactive mode available commands.\n\n"
            f"{BOLD}COMMANDS{END}\n")
        for key, value in help_menu.items():
            print(
                f"\t{key}\n"
                f"\t\t{value}\n"
                )

    def run_in_file_mode(self, filename, debug=False):
        topology = Topology(debug=debug)
        topology.from_config_file(f'topologies/{filename}')
        topology.run()

    def run_in_interactive_mode(self, debug=False) -> None:
        topology = Topology()
        header = (
            f"**Welcome to distributed Bellman Ford simulation.**\n\n"
            f"To see available commands type help.\n"
            f"To quit press ctl+c or type quit.\n"
        )

        print(header)
        try:
            while True:
                command = input('[INPUT]: ')
                if command in ['quit', 'q']:
                    print('\nExiting. Goodbye!')
                    break
                elif command in ['help', 'h']:
                    self.print_help_menu()
                elif command.startswith('add edge'):
                    command = command.replace('add edge', '').strip()
                    parts = command.split(' ')
                    if len(parts) != 3:
                        print(
                            f"Invalid number of arguments, provided {len(parts)}, add edge requires 3 arguments."
                        )
                    else:
                        start, end, weight = parts
                        topology.add_edge(start=start, end=end, weight=int(weight))
                elif command.startswith('update edge'):
                    command = command.replace('update edge', '').strip()
                    parts = command.split(' ')
                    if len(parts) != 3:
                        print(
                            f"Invalid number of arguments, provided {len(parts)}, update edge requires 3 arguments."
                        )
                    else:
                        start, end, weight = parts
                        topology.update_edge(start=start, end=end, weight=int(weight))
                elif command.startswith('node down'):
                    command = command.replace('node down', '').strip()
                    parts = command.split(' ')
                    if len(parts) != 1:
                        print(
                            f"Invalid number of arguments, provided {len(parts)}, node down requires 1 argument."
                        )
                    else:
                        down_node = topology.get_node(parts[0])
                        # find all the incoming links to this node
                        upstream_neighbors = [n for n in down_node.incoming_links]
                        # remove all incoming links to this node
                        down_node.incoming_links = {}
                        # inform all upstream nodes to remove this node from their outgoing links
                        for n in upstream_neighbors:
                            upstream_node = topology.nodes[n]
                            upstream_node.unlink(down_node.name)
                        topology.reset_nodes()
                        topology.run()

                elif command == 'list':
                    names = [name.split('.')[0] for name in get_files('topologies')]
                    print('\n'.join(names))
                elif command.startswith('load topology'):
                    command = command.replace('load topology', '').strip()
                    parts = command.split(' ')
                    if len(parts) != 1:
                        print(
                            f"Invalid number of arguments, provided {len(parts)}, load topology requires 1 argument."
                        )
                    else:
                        topology.clear()
                        filename = parts[0]
                        topology.from_config_file(f'topologies/{filename}.txt')
                elif command == 'run':
                    topology.run()
                elif command in ['display topology', 'topology']:
                    print(topology)
                elif command in ['display dv', 'dv']:
                    table = PrettyTable()
                    sorted_node_names = sorted(topology.nodes.keys())
                    table.field_names = [" "] + sorted_node_names
                    rows = []
                    
                    for node in sorted_node_names:
                        row = []
                        node_dv = topology.nodes[node].dv
                        for n in sorted_node_names:
                            row.append(node_dv.get(n, 'inf'))
                        r = [node] + row
                        rows.append(r)
                    table.add_rows(rows)
                    print(table)
                else:
                    print("Invalid command. See the help menu using help or h commands.")

        except KeyboardInterrupt:
            print('\nExiting. Goodbye!')

    def run(self):
        try:
            args = self.parser.parse_args()
            debug = args.debug
            if args.mode == 'interactive':
                self.run_in_interactive_mode(debug=debug)
            elif args.mode == 'from_file':
                if not args.filename:
                    raise Exception('When using from_file mode, it is required to specify a filename using --filename')
                self.run_in_file_mode(args.filename, debug)
        except Exception as exc:
            print(exc)

if __name__ == '__main__':
    cli = CLI()
    cli.run()

    # topology = Topology()
    # topology.from_config_file('topologies/SimpleTopo.txt')
    # topology.add_edge('A', 'B', 1)
    # topology.add_edge('B', 'A', 1)
    # topology.add_edge('B', 'C', 2)
    # topology.add_edge('C', 'B', 2)
    # topology.add_edge('C', 'D', 0)
    # topology.add_edge('D', 'C', 0)
    # topology.add_edge('E', 'D', -1)
    # print(topology)
    # topology.run()
