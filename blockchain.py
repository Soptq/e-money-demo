"""实现的一条区块链"""
import time
import utils
import elliptic_curve
import requests
import random
import math
import json


class Blockchain:
    def __init__(self, encry_params: tuple, G: tuple, ip, root: set):
        self.ROOT = set() # DNS 节点
        self.ROOT = root
        self.chain = [] # 主链
        self.DIFFICULTY = 0 # < 64
        self.curvefn = elliptic_curve.Curve_Encrypt(encry_params[0], encry_params[1], encry_params[2], encry_params[3])
        self.G = G

        self.private_key = random.randint(1, encry_params[3])
        self.public_key, self.address = self.curvefn.get_address(self.private_key, self.G)

        self.genesis_block()

        self.neighbor = set()  # 邻居节点
        self.children = set()   # 子代
        self.ip = ip
        self.coop_ip = ""
        self.coop_batch = 4096
        self.current_batch = 0
        self.coop_status = False
        self.coop_proof = 0

        self.amount = 0
        self.hypoamount = 0
        self.hyporeceive = []
        self.current_transactions = []  # 自己的交易池
        self.receive_transactions = []  # 别人的交易池

        # 初始化 coin_base 奖励
        self.mine_transaction = self.generate_transactions(50, str(self.public_key), "root")
        self.coin_base = [[self.mine_transaction, {'txhash': utils.hash256(self.mine_transaction)}]]
        # self.msg = []

        self.register() # 向 DNS 汇报自己存在
        self.update_neighbor() # 拉取当前在线节点
        self.receive_transaction() # 拉取交易

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
            'sender': sender,
            'time': time.time()
        }

    def genesis_block(self):
        """
        创世区块
        :return:
        """
        block = self.generate_block(0, '000000', '000000', 138, time.time(), [])
        self.chain.append(block)

    def proof_of_work(self, coop=False):
        """
        挖矿
        :return:
        """
        self.update_neighbor()
        self.resolve_conflicts()
        self.receive_transaction()
        print(self.receive_transactions)
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
        data = {'difficulty': self.DIFFICULTY, 'block': block}
        if coop :
                # 主机，分配任务
                for child in self.children:
                    requests.post(f'http://{child}/start_work', data=json.dumps(data))
                # 等待
                while self.coop_status is False:
                    for child in self.children:
                        resp = requests.get(f'http://{child}/coop_status').json()
                        if resp['status'] == '1':
                            block['proof'] = int(resp['proof'])
                            self.coop_status = True

                    time.sleep(1)

                for child in self.children:
                    requests.post(f'http://{child}/stop_work')
        else:   # 单机挖矿
            while self.valid_proof(block) is False:
                proof += 1
                block['proof'] = proof
        self.current_transactions = []
        self.receive_transactions = []
        self.chain.append(block)
        self.utxo_pool(block)
        self.diffuculty_resolve()
        self.hypoamount = 0
        self.current_batch = 0
        self.coop_status = False
        self.coop_proof = 0
        return block

    def valid_proof(self, block, difficulty=-1, update=True):
        if update:
            self.update_neighbor()
            self.receive_transaction()
        if difficulty == -1:
            difficulty = self.DIFFICULTY
        guess_hash = utils.hash256(block)
        print(guess_hash)
        print(guess_hash[:difficulty])
        print("0" * difficulty)
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
        if amount > self.amount + self.hypoamount:
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
            self.hypoamount = 0
            self.hyporeceive = []
            return True
        return False

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            last_block_hash = utils.hash256(last_block)
            if block['previous_hash'] != last_block_hash:
                # self.msg.append('hash wrong')
                return False
            if not self.valid_proof(block):
                # self.msg.append('proof wrong')
                return False
            if not self.valid_block_transaction(block):
                # self.msg.append('t wrong')
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

    def receive_transaction(self):
        if len(self.neighbor) != 0:
            for i in self.neighbor:
                if i in self.children:
                    continue
                resp = requests.get(f'http://{i}/transaction_pool')
                if resp.status_code == 200:
                    if len(resp.json()) > 0:
                        for tx in resp.json():
                            if tx not in self.receive_transactions:
                                self.receive_transactions.append(tx)
                            if self.curvefn.sign_verify(tx[0], eval(tx[0]['sender']), tx[1]['signature'], self.G):
                                if tx[0]['recipient'] == str(self.public_key) \
                                        and tx[2]['txhash'] not in self.hyporeceive:
                                    self.hypoamount += int(tx[0]['amount'])
                                    self.hyporeceive.append(tx[2]['txhash'])

    def register(self):
        if self.ip not in self.ROOT:
            for dns in self.ROOT:
                self.neighbor.add(dns)
                requests.post(f'http://{dns}/register_nodes', {'node': self.ip})

    def update_neighbor(self):
        temp_neighbor = set()
        if self.ip not in self.ROOT:
            dns = random.sample(self.ROOT, 1)[0]
            resp = requests.get(f'http://{dns}/net_work')
            r = set(resp.json()['node_list'])
            for ip in r:
                if ip == self.ip or ip in self.ROOT:
                    continue
                temp_neighbor.add(ip)
            temp_neighbor.add(dns)
        if len(temp_neighbor) != 0:
            self.neighbor = temp_neighbor

    def solve_mini_mission(self, data):
        # 子机任务
        # 构造 block
        data = json.loads(data)
        difficulty = data['difficulty']
        block = data['block']
        while self.coop_status is False:
            resp = requests.get(f'http://{self.coop_ip}/mission').json()
            start_batch = resp['start']
            end_batch = resp['end']
            print(f'Get Mission From {start_batch} To {end_batch}')
            for p in range(start_batch, end_batch):
                block['proof'] = p
                if self.valid_proof(block, difficulty=difficulty, update=False):
                    # 解开了
                    self.coop_status = True
                    self.coop_proof = p
                    break


