import requests
from flask import Flask, jsonify, request, render_template
from blockchain import Blockchain
import utils


ip = input("输入这个节点的 IP: ")
# ip = '127.0.0.1:5000'
ROOT = set()
ROOT.add('127.0.0.1:5000')
blockchain = Blockchain(utils.get_magic_param()[0], utils.get_magic_param()[1], ip, ROOT)  # 实例化类

app = Flask(__name__)



def get_render_assets():
    public_key = utils.tuple2string(blockchain.public_key)
    secret_key = str(blockchain.private_key)
    amount = blockchain.amount
    hypoamount = blockchain.hypoamount
    networks = list(blockchain.neighbor)
    chains = []
    for obj in blockchain.chain:
        temp = {}
        temp['index'] = str(obj['index'])
        if temp['index'] == '0':
            temp['owner'] = "世界"
            temp['number'] = "世界"
            temp['time'] = str(obj['timestamp'])
        else:
            if obj['transactions'][0][0]['recipient'] == str(blockchain.public_key):
                temp['owner'] = "我"
            else:
                temp['owner'] = "别人"
            temp['number'] = str(len(obj['transactions']))
            temp['time'] = str(obj['timestamp'])
        chains.append(temp)
    children = list(blockchain.children)
    return public_key, secret_key, amount, hypoamount, networks, chains, children


@app.route('/', methods=['GET'])
def web_index():
    public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

    return render_template('index.html',
                           public_key=public_key,
                           secret_key=secret_key,
                           amount=amount,
                           hypoamount=hypoamount,
                           node_length=str(len(networks) + 1),
                           localip=blockchain.ip,
                           networks=networks,
                           block_length=str(len(blockchain.chain)),
                           chain=chains,
                           children=children)


# 更新网络
@app.route('/get_map', methods=['GET'])
def get_map():
    blockchain.update_neighbor()
    public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

    return render_template('index.html',
                           public_key=public_key,
                           secret_key=secret_key,
                           amount=amount,
                           hypoamount=hypoamount,
                           node_length=str(len(networks) + 1),
                           localip=blockchain.ip,
                           networks=networks,
                           block_length=str(len(blockchain.chain)),
                           chain=chains,
                           children=children)


@app.route('/receive_transaction', methods=['GET'])
def receive_transaction():
    blockchain.receive_transaction()
    public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

    return render_template('index.html',
                           public_key=public_key,
                           secret_key=secret_key,
                           amount=amount,
                           hypoamount=hypoamount,
                           node_length=str(len(networks) + 1),
                           localip=blockchain.ip,
                           networks=networks,
                           block_length=str(len(blockchain.chain)),
                           chain=chains,
                           children=children)


@app.route('/consensus', methods=['GET'])
def consensus():
    blockchain.resolve_conflicts()
    public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

    return render_template('index.html',
                           public_key=public_key,
                           secret_key=secret_key,
                           amount=amount,
                           hypoamount=hypoamount,
                           node_length=str(len(networks) + 1),
                           localip=blockchain.ip,
                           networks=networks,
                           block_length=str(len(blockchain.chain)),
                           chain=chains,
                           children=children)


# 操作返回界面类
@app.route('/mine', methods=['POST'])
def mine():
    values = request.form
    values.to_dict()
    if 'coop' in values and values['coop'] == 'on':
        blockchain.coop_batch = int(values['coop_batch'])
        blockchain.proof_of_work(coop=True)
    else:
        blockchain.proof_of_work()
    public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

    return render_template('index.html',
                           public_key=public_key,
                           secret_key=secret_key,
                           amount=amount,
                           hypoamount=hypoamount,
                           node_length=str(len(networks) + 1),
                           localip=blockchain.ip,
                           networks=networks,
                           block_length=str(len(blockchain.chain)),
                           chain=chains,
                           children=children)


@app.route('/transaction', methods=['POST'])  # 自身交易池
def transaction():
    values = request.form
    values.to_dict()
    if values['recipient'] == '' or values['amount'] == '':
        public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

        return render_template('index.html',
                               public_key=public_key,
                               secret_key=secret_key,
                               amount=amount,
                               hypoamount=hypoamount,
                               node_length=str(len(networks) + 1),
                               localip=blockchain.ip,
                               networks=networks,
                               block_length=str(len(blockchain.chain)),
                               chain=chains,
                               children=children,
                               message='缺少参数')
    else:
        if blockchain.sub_transactions(str(utils.string2tuple(values['recipient'])), int(values['amount'])):
            blockchain.hypoamount -= int(values['amount'])
            public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

            return render_template('index.html',
                                   public_key=public_key,
                                   secret_key=secret_key,
                                   amount=amount,
                                   hypoamount=hypoamount,
                                   node_length=str(len(networks) + 1),
                                   localip=blockchain.ip,
                                   networks=networks,
                                   block_length=str(len(blockchain.chain)),
                                   chain=chains,
                                   children=children,
                                   message='成功')
        else:
            public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

            return render_template('index.html',
                                   public_key=public_key,
                                   secret_key=secret_key,
                                   amount=amount,
                                   hypoamount=hypoamount,
                                   node_length=str(len(networks) + 1),
                                   localip=blockchain.ip,
                                   networks=networks,
                                   block_length=str(len(blockchain.chain)),
                                   chain=chains,
                                   children=children,
                                   message='余额不足')


@app.route('/register_nodes', methods=['POST'])
def register_nodes():
    values = request.form
    values.to_dict()
    n = values['node']
    if n is None:
        return render_template('index.html', log='请提供一个正确的ip', chain=blockchain.chain)
    else:
        if n not in blockchain.neighbor:
            blockchain.neighbor.add(n)
            log = {
                '新节点注册成功'
                '邻居节点': list(blockchain.neighbor),
            }
            return render_template('index.html', log=log, chain=blockchain.chain)



# # 展示界面类
# @app.route('/show_network', methods=['GET'])
# def show_network():
#     a = list(blockchain.neighbor)
#     a.append(blockchain.ip)
#     log = {
#         '节点列表': a,
#         '节点数量': len(a),
#     }
#     return render_template('index.html', log=log, chain=blockchain.chain)


# @app.route('/show_transaction', methods=['GET'])
# def show_transaction():
#     return render_template('index.html', log=blockchain.current_transactions, chain=blockchain.chain)


# 接口类
@app.route('/net_work', methods=['GET'])
def net_work():
    a = list(blockchain.neighbor)
    a.append(blockchain.ip)
    response = {
        'node_list': a,
        'node_number': len(a), }
    return jsonify(response), 200


@app.route('/transaction_pool', methods=['GET'])
def transaction_pool():
    return jsonify(blockchain.current_transactions)


@app.route('/chain', methods=['GET'])
def chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/register_childs', methods=['POST'])
def register_childs():
    values = request.form
    values.to_dict()
    n = values['node']
    if n is not None:
        if n not in blockchain.children:
            blockchain.children.add(n)
    return "200"


@app.route('/connect_parent', methods=['POST'])
def connect_parent():
    values = request.form
    values.to_dict()
    if 'coop_parent' in values:
        if values['coop_parent'] is not None:
            blockchain.coop_ip = values['coop_parent']
            requests.post(f'http://{blockchain.coop_ip}/register_childs', {'node': blockchain.ip})

    public_key, secret_key, amount, hypoamount, networks, chains, children = get_render_assets()

    return render_template('index.html',
                           public_key=public_key,
                           secret_key=secret_key,
                           amount=amount,
                           hypoamount=hypoamount,
                           node_length=str(len(networks) + 1),
                           localip=blockchain.ip,
                           networks=networks,
                           block_length=str(len(blockchain.chain)),
                           chain=chains,
                           children=children)


@app.route('/mission', methods=['GET'])
def mission():
    values = request.form
    values.to_dict()
    # 分配新任务
    batch_start = blockchain.current_batch
    blockchain.current_batch += blockchain.coop_batch
    batch_end = blockchain.current_batch
    return jsonify({'start': batch_start, 'end': batch_end})

@app.route('/start_work', methods=['POST'])
def start_work():
    values = request.data
    blockchain.coop_status = False
    blockchain.solve_mini_mission(values)
    return "200"


@app.route('/stop_work', methods=['POST'])
def stop_work():
    blockchain.coop_status = True
    return "200"


@app.route('/coop_status', methods=['GET'])
def coop_status():
    if blockchain.coop_status:
        return jsonify({'status': '1', 'proof': str(blockchain.coop_proof)})
    else:
        return jsonify({'status': '0'})


host = blockchain.ip.split(':')[0]
port = blockchain.ip.split(':')[1]
app.run(host=host, port=int(port))
