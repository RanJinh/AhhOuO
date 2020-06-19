from hashlib import sha256
import json
import time
from flask import Flask, request
import requests


class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, merkle_root, nonce=0):
        """
        Constructor for the `Block` class.
        :param index: Unique ID of the block.
        :param transactions: List of transactions.
        :param timestamp: Time of generation of the block.
        :param previous_hash: Hash of the previous block in the chain which this block is part of.
        :param nonce: Nonce starts from 0.
        """
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.merkle_root = merkle_root
        self.nonce = nonce

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        First converting it into JSON string.
        """
        # WRITE YOUR CODE HERE !
        block_string = json.dumps(self.__dict__, sort_keys=True)
        hash = sha256(block_string.encode()).hexdigest()
        return hash


class Blockchain:
    # difficulty of PoW algorithm
    difficulty = 2

    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        # WRITE YOUR CODE HERE !
        genesis_block = Block(index=0,
                              transactions=[],
                              timestamp=0,
                              previous_hash="0",
                              merkle_root="0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @staticmethod
    def proof_of_work(block):
        """
        Function that tries different values of nonce to get a hash that satisfies difficulty criteria.
        """
        # WRITE YOUR CODE HERE !
        block.nonce = 0
        hash = block.compute_hash()
        while not hash.startswith(Blockchain.difficulty * '0'):
            block.nonce += 1
            hash = block.compute_hash()
        return hash

    def merkle_root(self):
        length = len(self.unconfirmed_transactions)
        hashdata = []
        for i in range(length):
            transactions_string = json.dumps(self.unconfirmed_transactions[i], sort_keys=True)
            hashdata.append(sha256(transactions_string.encode()).hexdigest())
        while length > 1:
            temp = int(length / 2)
            for i in range(temp):
                hashdata[i] = sha256((str(hashdata[i * 2]) + str(hashdata[i * 2 + 1])).encode()).hexdigest()
            if length % 2 != 0:
                hashdata[temp] = hashdata[temp * 2]
                length = (length + 1) / 2
            else:
                length = length / 2
        return hashdata[0]

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        # WRITE YOUR CODE HERE !

        return (block_hash == block.compute_hash()) and block_hash.startswith('0' * Blockchain.difficulty)

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        # WRITE YOUR CODE HERE !
        # Checking if the proof is valid.
        if not Blockchain.is_valid_proof(block, proof):
            return False
        # The previous_hash referred in the block and the hash of latest block
        #           in the chain match.
        previous_hash = self.last_block.hash
        if previous_hash != block.previous_hash:
            return False
        block.hash = proof
        self.chain.append(block)
        return True

    @property
    def last_block(self):
        return self.chain[-1]

    def mine(self):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        # WRITE YOUR CODE HERE !
        if not self.unconfirmed_transactions:
            return False
        last_block = self.last_block
        merkle_root = self.merkle_root()
        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash,
                          merkle_root=merkle_root)
        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        self.unconfirmed_transactions = []
        return True

    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    @classmethod
    def check_chain_validity(cls, chain):
        """
        to check if the entire blockchain is valid.
        """
        # WRITE YOUR CODE HERE !
        previous_hash = "0"
        for block in chain:
            block_hash = block.hash
            if not cls.is_valid_proof(block, block_hash) or previous_hash != block.previous_hash:
                return False
            previous_hash = block_hash
        return True


def consensus():
    """
    A simple consnsus algorithm: If a longer valid chain is found, chain is replaced with it.
    """
    global blockchain
    # WRITE YOUR CODE HERE !
    longest_chain = None
    current_len = len(blockchain.chain)
    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain
    if longest_chain:
        blockchain = longest_chain


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["merkle_root"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain


# Initialize flask application
app = Flask(__name__)
# Initialize a blockchain object.
blockchain = Blockchain()
blockchain.create_genesis_block()

# the address to other participating members of the network
peers = set()


# endpoint to submit a new transaction.
# This will be used by the application to add new data (posts) to the blockchain
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "content"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    tx_data["timestamp"] = time.time()

    blockchain.add_new_transaction(tx_data)

    return "Success", 201


# endpoint to return the node's copy of the chain.
# The application will be using this endpoint to query all the posts to display.
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})


# endpoint to add new peers to the network.
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    peers.add(node_address)

    # Return the consensus blockchain to the newly registered node so that he can sync
    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to register current node with the node specified in the request,
    and sync the blockchain as well as peer data.
    """
    node_address = request.get_json(force=True)["node_address"]
    print(node_address)
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


# endpoint to request the node to mine the unconfirmed transactions (if any).
# The application will be using it to initiate a command to mine from the application itself.
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        # Making sure we have the longest chain before announcing to the network
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


# endpoint to add a block mined by someone else to the node's chain. The block is first verified by the node and then added to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["merkle_root"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


