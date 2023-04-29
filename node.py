import sys
import grpc
import chain_replication_pb2
import chain_replication_pb2_grpc
import time
import random
from concurrent import futures


def print_help():
    print("""
    This is a ChainReplication node.
    Use -p to assign a port to the node. Example -p 5051.
    Use -n to assign a name to the node. Example -n MyNode.
    Default port is 5051 and default name is node.

    Required (ip aadresses of other nodes):
        -node2 x.x.x.x:xxxx
        -node3 x.x.x.x:xxxx

    Example command: python node.py -p 8080 -n MyNode -node2 192.168.1.212:5051 -node3 192.168.1.217:5051""")


def array_index(array, element):
    try:
        return array.index(element)
    except:
        return -1


def element_or_default(array, index, default):
    try:
        return array[index]
    except:
        return default


def node_port(args):
    default_port = 5051

    port_index = array_index(args, '-p') + 1
    if port_index != 0:
        return element_or_default(args, port_index, default_port)
    return default_port


def node_name(args):
    default_name = 'node'

    name_index = array_index(args, '-n') + 1
    if name_index != 0:
        return element_or_default(args, name_index, default_name)
    return default_name


def node_id(args):
    default_id = random.randint(1, 4000)

    id_index = array_index(args, '-i') + 1
    if id_index != 0:
        return int(element_or_default(args, id_index, default_id))
    return default_id


def other_nodes(args):
    node2_index = array_index(args, '-node2')
    if node2_index == -1:
        raise ValueError('-node2 missing')

    node2_value = element_or_default(args, node2_index + 1, '')
    if not node2_value:
        raise ValueError('-node2 value is missing')

    node3_index = array_index(args, '-node3')
    if node3_index == -1:
        raise ValueError('-node3 missing')

    node3_value = element_or_default(args, node3_index + 1, '')
    if not node3_value:
        raise ValueError('-node3 value is missing')

    return node2_value, node3_value


class ChainReplicationServicer(chain_replication_pb2_grpc.ChainReplicationServicer):
    def __init__(self, id, name, node2, node3):
        self.id = id
        self.name = name
        self.coordinator = None

        self.node2 = node2
        self.node3 = node3

        self.node2name = None
        self.node3name = None

        self.node2id = None
        self.node3id = None

    def Ack(self, request, context):
        return chain_replication_pb2.AckResponse(name=self.name, id=self.id)

    def wait_for_others(self):
        while True:
            if not self.node2name:
                try:
                    with grpc.insecure_channel(self.node2) as channel:
                        stub = chain_replication_pb2_grpc.ChainReplicationStub(channel)
                        response = stub.Ack(chain_replication_pb2.AckRequest())

                        self.node2name = response.name
                        self.node2id = response.id

                        print('Node2 ({}) is ready'.format(self.node2name))
                except:
                    print('Waiting for Node2 to connect...')

            if not self.node3name:
                try:
                    with grpc.insecure_channel(self.node3) as channel:
                        stub = chain_replication_pb2_grpc.ChainReplicationStub(channel)
                        response = stub.Ack(chain_replication_pb2.AckRequest())

                        self.node3name = response.name
                        self.node3id = response.id

                        print('Node3 ({}) is ready'.format(self.node3name))
                except:
                    print('Waiting for Node3 to connect...')

            if self.node2name and self.node3name:
                print('Node2 ({}) and Node3 ({}) are ready'.format(self.node2name, self.node3name))
                return True

            time.sleep(0.5)

    def Start(self, request, context):
        return chain_replication_pb2.StartResponse(ready=self.waiting_start)

    def ask_status(self):
        node2_start = False
        node3_start = False
        while not (node2_start and node3_start):
            if not node2_start:
                try:
                    with grpc.insecure_channel(self.node2) as channel:
                        stub = chain_replication_pb2_grpc.ChainReplicationStub(channel)
                        response = stub.Start(chain_replication_pb2.StartMessage())
                        node2_start = response.ready
                except:
                    raise ConnectionError('{} missing'.format(self.node2name))

            if not node3_start:
                try:
                    with grpc.insecure_channel(self.node3) as channel:
                        stub = chain_replication_pb2_grpc.ChainReplicationStub(channel)
                        response = stub.Start(chain_replication_pb2.StartMessage())
                        node3_start = response.ready
                except:
                    raise ConnectionError('{} missing'.format(self.node3name))

            if not node2_start:
                print('Waiting for {} to join new game...'.format(self.node2name))

            if not node3_start:
                print('Waiting for {} to join new game...'.format(self.node3name))

            print()
            time.sleep(1)


    def process_command(self, command):
        print("Unknown command!")

def serve():
    if array_index(sys.argv, '--help') != -1:
        print_help()
        return

    # Server config
    id = node_id(sys.argv)
    name = node_name(sys.argv)
    port = node_port(sys.argv)
    node2, node3 = other_nodes(sys.argv)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))

    servicer = ChainReplicationServicer(id, name, node2, node3)
    chain_replication_pb2_grpc.add_ChainReplicationServicer_to_server(servicer, server)

    server.add_insecure_port('0.0.0.0:{}'.format(port))
    server.start()

    print('Started ChainReplication node#{} {} on port {}'.format(id, name, port))
    print('Node2: {}'.format(node2))
    print('Node3: {}\n'.format(node3))

    # Wait for other nodes to become available
    servicer.wait_for_others()

    try:
        while True:
            user_command = input('{}>'.format(name))
            servicer.process_command(user_command)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
