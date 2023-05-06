import argparse
import grpc
import chain_pb2
import chain_pb2_grpc
import time
import random
import math
import re
from concurrent import futures
from threading import Thread

parser = argparse.ArgumentParser(description='Node setup arguments')
required = parser.add_argument_group('required arguments')
required.add_argument('-name', type=str, help='Name of the created node', required=True)
required.add_argument('-addr', type=str, help='IP address of the created node in format x.x.x.x:port', required=True)
parser.add_argument('-file', type=str, default='node_list.txt', help='Path to the node list file')
args = parser.parse_args()

pattern_local_store_ps = re.compile("Local-store-ps (\d+)")
pattern_write_operation = re.compile('Write-operation <"(.*?)", (\d+(\.\d*)?)>')
pattern_read_operation = re.compile('Read-operation "(.*?)"')
pattern_time_out = re.compile("Time-out (\d+(\.\d*)?)")


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

    def get_processes(self):
        '''
        Get the list of node processes
        '''
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.Processes(chain_pb2.ProcessRequest())
                return response.processes
        except:
            print(f'Failed to get processes of node {self.name}({self.address})')
            return None

    def send_chain(self, chain):
        '''
        Set the chain order (list of processes in the correct order) for other node
        '''
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.SetChain(chain_pb2.ChainRequest(processes=chain))
                return True
        except:
            print(f'Failed to send chain to node {self.name}({self.address})')
            return None

    def send_book_data(self, target_process, book, price, timeout=None):
        if timeout:
            time.sleep(math.ceil(timeout * 60))  # Convert minutes to seconds

        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.SendBook(chain_pb2.SendBookRequest(process=target_process, book=book, price=price))
                return True
        except:
            print(f'Failed to send book data to node {self.name}({self.address})')
            return None

    def clean_book(self, target_process, book):
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.CleanBook(chain_pb2.CleanBookRequest(process=target_process, book=book))
                return True
        except:
            print(f'Failed to clean book in node {self.name}({self.address})')
            return None

    def get_book_list(self, target_process):
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.ListBooks(chain_pb2.ListBooksRequest(process=target_process))
                return response.books
        except:
            print(f'Failed to get book list from node {self.name}({self.address})')
            return None

    def get_book_statuses(self, target_process):
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.StatusBooks(chain_pb2.StatusBooksRequest(process=target_process))
                return response.books
        except:
            print(f'Failed to get book statuses from node {self.name}({self.address})')
            return None

    def get_book_price(self, process, book):
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.GetBookPrice(chain_pb2.BookRequest(process=process, book=book))
                return response.price, response.old_price
        except:
            print(f'Failed to get book price from node {self.name}({self.address})')
            return None

    def set_timeout(self, timeout):
        try:
            with grpc.insecure_channel(self.address) as channel:
                stub = chain_pb2_grpc.ChainStub(channel)
                response = stub.Timeout(chain_pb2.TimeoutRequest(timeout=timeout))
                return True
        except:
            print(f'Failed to set timeout for node {self.name}({self.address})')
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

    def store_book(self, book, price):
        book_data = {}
        book_data['price'] = price
        book_data['dirty'] = True
        self.store[book] = book_data

    def clean_book(self, book):
        self.store[book]['dirty'] = False

    def get_books(self):
        listing = []
        for key in list(self.store.keys()):
            listing.append(f'{key} = {self.store[key]["price"]}')

        return listing

    def get_books_status(self):
        statuses = []
        for key in list(self.store.keys()):
            dirty = self.store[key]['dirty']
            if dirty:
                status = 'dirty'
            else:
                status = 'clean'

            statuses.append(f'{key} - {status}')

        return statuses

    def get_book_price(self, book):
        try:
            book = self.store[book]
            return book['price']
        except:
            return None

    def reset(self):
        self.predecessor = None
        self.successor = None
        self.store = {}
        self.head = False
        self.tail = False


class ChainServicer(chain_pb2_grpc.ChainServicer):
    def __init__(self, name, address) -> None:
        self.name = name
        self.address = address
        self.server = None
        self.nodes = []
        self.chain_order = []
        self.processes = {}
        self.timeout = None

    def set_server(self, server):
        self.server = server

    def set_nodes(self, nodes):
        self.nodes = nodes

    def set_timeout(self, timeout):
        self.timeout = timeout

    def get_process_node(self, process_name):
        target_node_name = process_name.split('-PS')[0]
        target_node = None
        for node in self.nodes:
            if node.name == target_node_name:
                target_node = node
                break

        return target_node

    def process_order(self):
        '''
        RPC list does not have index method, which means that we have to 'recreate' the list
        '''
        order = []
        for item in self.chain_order:
            order.append(item)
        self.chain_order = order

    def create_process(self):
        name = f'{self.name}-PS{len(self.processes.keys()) + 1}'
        process = Process(name)
        self.processes[name] = process
        print(f'Created process {name}')

    def update_processes(self):
        '''
        Updates the processes belonging to this node according to the latest chain order.
        Also sets the head and tail processes.
        '''
        for key in list(self.processes.keys()):
            process = self.processes[key]
            index = self.chain_order.index(process.name)
            # Head
            if index == 0:
                process.set_head(True)
                process.set_successor(self.chain_order[index + 1])

            # Tail
            elif index == len(self.chain_order) - 1:
                process.set_tail(True)
                process.set_predecessor(self.chain_order[index - 1])

            # Normal
            else:
                process.set_predecessor(self.chain_order[index - 1])
                process.set_successor(self.chain_order[index + 1])

    def create_chain(self):
        # If chain already exists, ask for confirmation
        if len(self.chain_order):
            confirmation = input('Do you want to create a new chain (yes/no): ')
            if confirmation == 'yes':
                for key in (list(self.processes.keys())):
                    self.processes[key].reset()
            else:
                print('Chain creation cancelled')
                return
        # Creating the chain ordering
        processes = list(self.processes.keys())
        for node in self.nodes:
            if node.name == self.name:
                continue

            node_processes = node.get_processes()
            if node_processes is not None:
                processes.extend(node_processes)

        chain_order = []
        if len(processes) < 2:
            print("Chain creation canceled. There must be at least 2 local store processes!")
            return
        while len(processes) > 0:
            chain_order.append(processes.pop(random.randint(0, len(processes) - 1)))

        print('Chain has been created')

        # Sending the created chain order to other nodes
        self.chain_order = chain_order
        self.update_processes()
        for node in self.nodes:
            if node.name == self.name:
                continue

            node.send_chain(chain_order)

    def list_chain(self):
        if len(self.chain_order) == 0:
            print('Chain has not been created yet')
            return

        for i, process in enumerate(self.chain_order):
            if i == 0:
                print(f'{process} (Head)', end=' -> ')
            elif i == len(self.chain_order) - 1:
                print(f'{process} (Tail)')
            else:
                print(f'{process}', end=' -> ')

    def write_operation(self, book, price):
        '''
        Parses the input and sends it to the head process
        '''
        # operation = operation[1:len(operation) - 1]
        # book, price = operation.split(',')
        # book = book[1:len(book) - 1]
        # price = price.strip()'
        
        if len(self.chain_order) == 0:
            print('Chain has not been created yet')
            return
        
        print("Correct input. Writing process started!")

        target_node = self.get_process_node(self.chain_order[0])

        thread = Thread(target=target_node.send_book_data, args=(self.chain_order[0], book, price))
        thread.start()

    def list_books(self):
        '''
        Asks the list of books from the Tail process
        '''
        if len(self.chain_order) == 0:
            print('Chain has not been created yet')
            return
        
        tail_process = self.chain_order[len(self.chain_order) - 1]
        tail_node = self.get_process_node(tail_process)

        books = tail_node.get_book_list(tail_process)
        if books is None:
            books = []

        for i, book in enumerate(books):
            print(f'{i}) {book}')

    def read_operation(self, book):
        '''
        Tries to read a book from a random process
        '''
        
        if len(self.chain_order) == 0:
            print('Chain has not been created yet')
            return
        process = self.chain_order[random.randint(0, len(self.chain_order) - 1)]
        node = self.get_process_node(process)
        if node:
            price, old_price = node.get_book_price(process, book)
        else:
            price = old_price = 'None'

        if price == 'None':
            print('Not yet in the stock')
        elif price != old_price and old_price != 'None':
            print(f'{price} EUR (old price {old_price} EUR)')
        else:
            print(f'{price} EUR')

    def process_timeout(self, timeout):
        '''
        Sets the timeout for all nodes before propagating the update to next nodes.
        Time is expected as minutes.
        '''
        timeout_fl = float(timeout)
        if timeout_fl == 0:
            self.set_timeout(None)
        else:
            self.set_timeout(timeout_fl)

        for node in self.nodes:
            if node.name == self.name:
                continue

            node.set_timeout(timeout)

    def data_status(self):
        '''
        Asks the head what is the status of the books in it.
        '''
        if len(self.chain_order) == 0:
            print('Chain has not been created yet')
            return
        head_process = self.chain_order[0]
        head_node = self.get_process_node(head_process)

        statuses = head_node.get_book_statuses(head_process)
        if statuses is None:
            statuses = []

        for i, status in enumerate(statuses):
            print(f'{i}) {status}')

    def remove_head(self):
        if len(self.chain_order) < 3:
            print("Can't remove head. There are less than 3 processes in the chain")
            return
        
        self.chain_order.pop(0)
        self.update_processes()
        for node in self.nodes:
            if node.name == self.name:
                continue

            node.send_chain(self.chain_order)
        print("command reached: Remove head")

    def restore_head(self):
        if len(self.chain_order) == 0:
            print('Chain has not been created yet')
            return
        print("command reached: Restore head")

    def process_command(self, command: str):
        is_unknown_command = False
        if command == 'Create-chain':
            self.create_chain()
        elif command == 'List-chain':
            self.list_chain()
        # elif command.startswith('Write-operation'):
        #    command = command.replace('Write-operation', '').strip()
        #    self.write_operation(command)
        elif command == 'List-books':
            self.list_books()
        # elif command.startswith('Read-operation'):
        #    book = command.replace('Read-operation', '').strip()
        #    book = book[1:len(book) - 1]  # Also removing quotes
        #    self.read_operation(book)
        # elif command.startswith('Set-timeout'):
        #    timeout = command.split(' ')[1].strip()
        #    self.process_timeout(timeout)
        elif command == 'Data-status':
            self.data_status()
        elif command == "Remove-head":
            self.remove_head()
        elif command == "Restore-head":
            self.restore_head()
        elif command == 'exit':
            self.stop_server()
        else:
            is_unknown_command = True

        if not is_unknown_command:
            return

        m = pattern_local_store_ps.match(command)
        if m:
            self.local_store_ps(int(m.group(1)))
            return
        m = pattern_write_operation.match(command)
        if m:
            self.write_operation(m.group(1), m.group(2))
            return
        m = pattern_read_operation.match(command)
        if m:
            self.read_operation(m.group(1))
            return
        m = pattern_time_out.match(command)
        if m:
            self.process_timeout(m.group(1))
            return
        print('Unsupported command')

    def local_store_ps(self, k: int):
        '''
        k: the number of storages to create
        '''
        for i in range(k):
            self.create_process()

    def stop_server(self):
        self.server.stop(0)

    # grpc implementations
    def Probe(self, request, context):
        return chain_pb2.ProbeResponse(name=self.name)

    def Processes(self, request, context):
        processes = list(self.processes.keys())
        return chain_pb2.ProcessResponse(processes=processes)

    def SetChain(self, request, context):
        print('Received chain ordering')
        chain_order = request.processes
        self.chain_order = chain_order
        self.process_order()
        for key in list(self.processes.keys()):
            self.processes[key].reset()
        self.update_processes()
        return chain_pb2.ChainResponse()

    def get_target_process(self, target_name):
        target_process = None
        for key in list(self.processes.keys()):
            process = self.processes[key]
            if process.name == target_name:
                target_process = process
                break

        return target_process

    def SendBook(self, request, context):
        target_process = self.get_target_process(request.process)

        book = request.book
        price = request.price
        target_process.store_book(book, price)
        # If the chain continues, send the book to the next member
        # Also includes timeout if this is necessary
        if target_process.successor is not None:
            target_node = self.get_process_node(target_process.successor)
            thread = Thread(target=target_node.send_book_data,
                            args=(target_process.successor, book, price, self.timeout))
            thread.start()
        else:
            target_process.clean_book(book)
            pred_node = self.get_process_node(target_process.predecessor)
            thread = Thread(target=pred_node.clean_book, args=(target_process.predecessor, book))
            thread.start()

        return chain_pb2.SendBookResponse()

    def CleanBook(self, request, context):
        target_process = self.get_target_process(request.process)
        target_process.clean_book(request.book)
        predecessor = target_process.predecessor
        if predecessor is None:
            return chain_pb2.CleanBookResponse()

        pred_node = self.get_process_node(predecessor)
        thread = Thread(target=pred_node.clean_book, args=(predecessor, request.book))
        thread.start()

        return chain_pb2.CleanBookResponse()

    def ListBooks(self, request, context):
        target_process = self.get_target_process(request.process)
        books = target_process.get_books()
        return chain_pb2.ListBooksResponse(books=books)

    def GetBookPrice(self, request, context):
        # Get the book from the required process
        target_process = self.get_target_process(request.process)
        if target_process:
            price = target_process.get_book_price(request.book)
        else:
            price = None
        if price is None:
            price = 'None'
        # Consult with the head node
        if request.process != self.chain_order[0]:
            head_node = self.get_process_node(self.chain_order[0])
            head_price, _ = head_node.get_book_price(self.chain_order[0], request.book)
        else:
            head_price = price
        return chain_pb2.BookResponse(price=head_price, old_price=price)

    def Timeout(self, request, context):
        timeout = float(request.timeout)
        if timeout == 0:
            self.set_timeout(None)
        else:
            self.set_timeout(timeout)
        return chain_pb2.TimeoutResponse()

    def StatusBooks(self, request, context):
        target_process = self.get_target_process(request.process)
        books = target_process.get_books_status()
        return chain_pb2.StatusBooksResponse(books=books)


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
            node.set_name(args.name)
            node.set_online(True)
            node.online = True
            continue

        if node.online:
            print(f'Node at {node.address} is online')
            continue

        name = node.probe_node()
        if name is None:
            all_nodes_online = False
            continue

        node.set_name(name)
        node.set_online(True)

    return all_nodes_online


def wait_for_nodes(nodes):
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
    nodes = read_node_file(args.file)
    wait_for_nodes(nodes)
    servicer.set_nodes(nodes)

    try:
        while True:
            user_command = input(f'{args.name}>')
            servicer.process_command(user_command)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    serve()
