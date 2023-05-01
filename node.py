import argparse
import grpc
import chain_pb2
import chain_pb2_grpc
import time
from concurrent import futures

parser = argparse.ArgumentParser(description='Node setup arguments')
required = parser.add_argument_group('required arguments')
required.add_argument('-name', type=str, help='Name of the created node', required=True)
required.add_argument('-addr', type=str, help='IP address of the created node in format x.x.x.x:port', required=True)
parser.add_argument('-file', type=str, default='node_list.txt', help='Path to the node list file')
args = parser.parse_args()

class Node:
    def __init__(self, address) -> None:
        self.name = None
        self.address = address
        self.online = False

    def set_name(self, name):
        self.name = name

    def set_online(self, online):
        self.online = online

    def probe_node(self):
        '''
        Check if node is alive. If alive, the method returns node name, otherwise None.
        '''
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.Probe(chain_pb2.ProbeRequest())
                print(f'Node at {self.address} is online')
                return response.name
        except:
            print(f'Node at {self.address} is not online yet')
            return None

    def __repr__(self) -> str:
        return f'Node: {self.name}, address: {self.address}, online: {self.online}'
    

class Process:
    def __init__(self, name) -> None:
        self.name = name
        self.predecessor = None
        self.successor = None
        self.store = {}
        self.head = False
        self.tail = False

    def set_predecessor(self, process):
        self.predecessor = process

    def set_successor(self, process):
        self.successor = process

    def set_head(self, head):
        self.head = head

    def set_tail(self, tail):
        self.tail = tail    


class ChainServicer(chain_pb2_grpc.ChainServicer):
    def __init__(self, name, address) -> None:
        self.name = name
        self.address = address
        self.server = None
        self.processes = {}

    def set_server(self, server):
        self.server = server

    def create_process(self):
        name = f'{self.name}-PS{len(self.processes.keys()) + 1}'
        process = Process(name)
        self.processes[name] = process
        print(f'Created process {name}')

    def process_command(self, command: str):
        if command.startswith('Local-store-ps'):
            k = int(command.split(' ')[1])
            self.local_store_ps(k)
        elif command == 'exit':
            print('Should exit the server here m8')
            #stop_server()
        else:
            print('Unsupported command')

    def local_store_ps(self, k: int):
        '''
        k: the number of storages to create
        '''
        for i in range(k):
            self.create_process()

    def stop_server(self):
        self.server.stop(0)

    def Probe(self, request, context):
        return chain_pb2.ProbeResponse(name=self.name)


# Reads the node file and returns an array of Node objects
def read_node_file(path):
    nodes = []
    with open(path, 'r') as file:
        for line in file:
            address = line.strip()
            nodes.append(Node(address))

    return nodes


def check_node_statuses(nodes):
    all_nodes_online = True
    for node in nodes:
        if node.address == args.addr:
            continue

        if node.online == True:
            print(f'Node at {node.address} is online')
            continue

        name = node.probe_node()
        if name is None:
            all_nodes_online = False
            continue

        node.set_name(name)
        node.set_online(True)

    return all_nodes_online


def wait_for_nodes():
    nodes = read_node_file(args.file)

    print('Waiting for all nodes to become available')
    all_nodes_ready = False
    while all_nodes_ready is False:
        all_nodes_ready = check_node_statuses(nodes)
        time.sleep(1)

    print('All nodes are online. It is possible to proceed.')


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    servicer = ChainServicer(args.name, args.addr)
    chain_pb2_grpc.add_ChainServicer_to_server(servicer, server)
    server.add_insecure_port(args.addr)
    server.start()
    servicer.set_server(server)

    print(f'Started node: {args.name} on {args.addr}')
    wait_for_nodes()

    try:
        while True:
            user_command = input(f'{args.name}>')
            servicer.process_command(user_command)
    except KeyboardInterrupt:
        server.stop(0)

        
if __name__ == '__main__':
    serve()