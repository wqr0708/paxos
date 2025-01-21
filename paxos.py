import redis
from message import NodeMessage
import requests
import json

class Proposer:
    def __init__(self, node_id, redis_client):
        self.node_id = node_id
        self.redis_client = redis_client
        self.current_turn = 0
        self.proposal_number = 0
        self.value = None
        
    def prepare(self, value):
        self.value = value
        msg = NodeMessage()
        msg.type = 'prepareRequest'
        msg.source = self.node_id
        msg.turn = self.current_turn
        msg.number = self.generate_proposal_number()
        msg.value = value
        
        # 将消息放入sender队列
        self.redis_client.lpush('sender_queue', json.dumps(msg.to_dict()))
        
    def generate_proposal_number(self):
        self.proposal_number += 1
        return f"{self.proposal_number}_{self.node_id}"

    def handle_message(self, msg):
        """处理接收到的消息"""
        if msg['type'] == 'prepareRespond':
            if msg['promise']:
                # 如果收到足够的promise，发送accept请求
                self.handle_promise(msg)
            else:
                # 如果被拒绝，增加提案编号重试
                self.retry_with_higher_number(msg)

    def handle_promise(self, msg):
        """处理promise响应"""
        if msg['promise']:
            # 发送accept请求
            accept_msg = NodeMessage()
            accept_msg.type = 'acceptRequest'
            accept_msg.source = self.node_id
            accept_msg.turn = msg['turn']
            accept_msg.number = msg['number']
            accept_msg.value = msg['value'] if msg['value'] else self.value
            
            self.redis_client.lpush('sender_queue', json.dumps(accept_msg.to_dict()))

class Acceptor:
    def __init__(self, node_id, redis_client):
        self.node_id = node_id
        self.redis_client = redis_client
        self.promised_number = None
        self.accepted_number = None
        self.accepted_value = None
        
    def handle_prepare(self, msg):
        response = NodeMessage()
        response.type = 'prepareRespond'
        response.source = self.node_id
        response.target = msg['source']
        response.turn = msg['turn']
        
        if self.promised_number and msg['number'] < self.promised_number:
            response.promise = False
        else:
            response.promise = True
            response.number = self.accepted_number
            response.value = self.accepted_value
            self.promised_number = msg['number']
            
        self.redis_client.lpush('sender_queue', json.dumps(response.to_dict()))

    def handle_accept(self, msg):
        """处理accept请求"""
        response = NodeMessage()
        response.type = 'acceptRespond'
        response.source = self.node_id
        response.target = msg['source']
        response.turn = msg['turn']
        
        if msg['number'] >= self.promised_number:
            response.accept = True
            self.accepted_number = msg['number']
            self.accepted_value = msg['value']
            # 广播接受的值
            self.broadcast_accept(msg['value'], msg['turn'])
        else:
            response.accept = False
            
        self.redis_client.lpush('sender_queue', json.dumps(response.to_dict()))
        
    def broadcast_accept(self, value, turn):
        """广播接受的值"""
        msg = NodeMessage()
        msg.type = 'decision'
        msg.source = self.node_id
        msg.turn = turn
        msg.value = value
        msg.final_value = True
        
        # 广播给所有learner
        self.redis_client.lpush(f'learner_{turn}_queue', json.dumps(msg.to_dict()))

class Learner:
    def __init__(self, node_id, redis_client):
        self.node_id = node_id
        self.redis_client = redis_client
        self.learned_values = {}
        
    def learn(self, msg):
        if msg['turn'] not in self.learned_values:
            self.learned_values[msg['turn']] = msg['value']
            # 执行value中的指令
            self.execute_command(msg['value'])
            
    def execute_command(self, value):
        """执行命令"""
        try:
            if value['type'] == 'write':
                # 写入Redis
                self.redis_client.set(value['key'], value['value'])
                print(f"Successfully wrote {value['key']}={value['value']}")
        except Exception as e:
            print(f"Error executing command: {e}") 