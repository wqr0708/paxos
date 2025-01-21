from flask import Flask, request, jsonify
import redis
import json
import threading
import time
from multi_paxos import RoundManager
import os

app = Flask(__name__)
redis_host = os.environ.get('REDIS_HOST', 'redis')
node_id = os.environ.get('NODE_ID', 'node1')
redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)

round_manager = RoundManager(node_id=node_id, redis_client=redis_client)

@app.route('/')
def index():
    return jsonify({'status': 'ok'})

@app.route('/client/read', methods=['GET'])
def handle_read():
    key = request.args.get('key')
    # 直接从数据库读取
    value = redis_client.get(key)
    return jsonify({'value': value})

@app.route('/client/write', methods=['POST'])
def handle_write():
    data = request.json
    # 将写指令放入指令队列
    redis_client.lpush('command_queue', json.dumps(data))
    return jsonify({'status': 'queued'})

@app.route('/message', methods=['POST'])
def handle_message():
    msg = request.json
    round_manager.handle_message(msg)
    return jsonify({'status': 'received'})

# 添加定期检查已完成轮次的任务
def check_rounds_periodically():
    while True:
        round_manager.check_finished_rounds()
        time.sleep(5)  # 每5秒检查一次

# 启动检查线程
threading.Thread(target=check_rounds_periodically, daemon=True).start() 