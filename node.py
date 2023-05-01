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
    

class ChainServicer(chain_pb2_grpc.ChainServicer):
    def __init__(self, name, address) -> None:
        self.name = name
        self.address = address

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

    print(f'Started node: {args.name} on {args.addr}')

    wait_for_nodes()

        
if __name__ == '__main__':
    serve()