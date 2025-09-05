# blockchain_logger.py
import hashlib
import json
import time

# Represents a single block in the blockchain
class Block:
    # Initialises a block with index, data, timestamp, and hash
    def __init__(self, index, timestamp, data, previous_hash): 
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()

    # Computes the SHA3-512 hash of the block contents
    def compute_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha3_512(block_string.encode()).hexdigest()

# Manages the chain of blocks and ensures integrity
class Blockchain:
    # Initializes the blockchain with a block
    def __init__(self):
        self.chain = [self.create_block()]

    # Creates the first block in the blockchain
    def create_block(self):
        return Block(0, time.time(), "Starter Block", "0")

    # Adds a new block with the given data to the chain
    def add_block(self, data):
        last_block = self.chain[-1]
        new_block = Block(len(self.chain), time.time(), data, last_block.hash)
        self.chain.append(new_block)

    # Validates the integrity of the blockchain
    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.hash != curr.compute_hash() or curr.previous_hash != prev.hash:
                return False
        return True
