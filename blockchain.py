"""实现的一条区块链"""
import time
import utils
import elliptic_curve
import requests
import random
import math

_a = 0x0000000000000000000000000000000000000000000000000000000000000000         # 椭圆曲线 a
_b = 0x0000000000000000000000000000000000000000000000000000000000000007         # 椭圆曲线 b
_p = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f         # 取模运算的模数
_r = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141         # 私钥不能大于 _r

_Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798        # 椭圆曲线上固定一点 G 的 x
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8        # 椭圆曲线上固定一点 G 的 y


class Blockchain:
    def __init__(self, encry_params: tuple, G: tuple, ip):
        self.chain = [] # 主链
        self.DIFFICULTY = 0 # < 64
        self.curvefn = elliptic_curve.Curve_Encrypt(encry_params[0], encry_params[1], encry_params[2], encry_params[3])
        self.G = G

        self.private_key = random.randint(1, encry_params[3])
        self.public_key, self.address = self.curvefn.get_address(self.private_key, self.G)

        self.genesis_block()

        self.neighbor = set()  # 邻居节点
        self.ip = ip

        self.amount = 0
        self.current_transactions = []  # 自己的交易池
        self.receive_transactions = []  # 别人的交易池

        # 初始化 coin_base 奖励
        self.mine_transaction = self.generate_transactions(50, str(self.public_key), "root")
        self.coin_base = [[self.mine_transaction, {'txhash': utils.hash256(self.mine_transaction)}]]
        self.msg = []

    def diffuculty_resolve(self):
        print(math.floor(utils.c_logistic(len(self.chain))))
        self.DIFFICULTY = math.floor(utils.c_logistic(len(self.chain)))

    def generate_block(self, index, merkle_tree, previous_hash, proof, timestamp, transactions):
        return {
            'index': index,
            'merkle_tree': merkle_tree,
            'previous_hash': previous_hash,
            'proof': proof,
            'timestamp': timestamp,
            'transactions': transactions
        }

    def generate_transactions(self, amount, recipient, sender):
        return {
            'amount': amount,
            'recipient': recipient,
            'sender': sender
        }

    def genesis_block(self):
        """
        创世区块
        :return:
        """
        block = self.generate_block(0, '000000', '000000', 138, time.time(), [])
        self.chain.append(block)

    def proof_of_work(self):
        """
        挖矿
        :return:
        """
        proof = 0
        t = time.time()
        mk = [self.coin_base[0][1]['txhash']]
        for tx in self.current_transactions:
            mk.append(tx[2]['txhash'])
        block = self.generate_block(len(self.chain),
                                    utils.generate_merkle(mk),
                                    utils.hash256(self.chain[-1]),
                                    proof,
                                    t,
                                    self.coin_base + self.current_transactions + self.receive_transactions)

        while self.valid_proof(block) is False:
            proof += 1
            block['proof'] = proof

        self.current_transactions = []
        self.receive_transactions = []
        self.chain.append(block)
        self.utxo_pool(block)
        self.diffuculty_resolve()
        return block


    def valid_proof(self, block, difficulty = -1):
        if difficulty == -1:
            difficulty = self.DIFFICULTY
        guess_hash = utils.hash256(block)
        return guess_hash[:difficulty] == "0" * difficulty


    def utxo_pool(self, block):
        if block['transactions'][0][0]['recipient'] == str(self.public_key):
            self.amount = self.amount + 50

        for tx in block['transactions'][1:]:
            if tx[0]['sender'] == str(self.public_key):
                self.amount = self.amount - tx[0]['amount']

            if tx[0]['recipient'] == str(self.public_key):
                self.amount = self.amount + tx[0]['amount']

    def sub_transactions(self, recipient, amount):
        if amount > self.amount:
            return False
        else:
            t1 = self.generate_transactions(amount, recipient, str(self.public_key))
            signature = self.curvefn.sign(t1, self.private_key, self.G)
            t2 = {'signature': signature}
            t3 = {'txhash': utils.hash256(t1)}
            tx = [t1, t2, t3]
            self.current_transactions.append(tx)
            return True

    def resolve_conflicts(self):
        new_chain = None
        max_length = len(self.chain)
        if len(self.neighbor) == 0:
            pass
        else:
            for node in self.neighbor:
                response = requests.get(f'http://{node}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']
                    if length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
        if new_chain:
            self.chain = new_chain
            self.amount = 0
            for block in self.chain[1:]:
                self.utxo_pool(block)
            self.current_transactions = []
            self.receive_transactions = []
            self.diffuculty_resolve()
            return True
        return False

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            last_block_hash = utils.hash256(last_block)
            if block['previous_hash'] != last_block_hash:
                self.msg.append('hash wrong')
                return False
            if not self.valid_proof(block):
                self.msg.append('proof wrong')
                return False
            if not self.valid_block_transaction(block):
                self.msg.append('t wrong')
                return False
            last_block = block
            current_index += 1
        return True

    def valid_block_transaction(self, block):
        transactions = block['transactions'][1:]
        if len(transactions) == 0:
            return True
        else:
            for tx in transactions:
                if not (self.curvefn.sign_verify(tx[0], eval(tx[0]['sender']), tx[1]['signature'], self.G)):
                    return False
            return True



if __name__ == '__main__':
    b = Blockchain((_a, _b, _p, _r), (_Gx, _Gy))
    b.sub_transactions('123', 29)
    b.proof_of_work()
    print(b.amount)
    b.sub_transactions('123', 22)
    b.proof_of_work()
    print(b.amount)
    b.sub_transactions('123', 13)
    b.proof_of_work()
    print(b.amount)
    c = b.chain
    d = b.valid_chain(c)
    print(d)
