import threading
from multiprocessing import Pool, Process
import redis
from paxos import Proposer, Acceptor, Learner
import json
import time

class Round:
    """单轮Paxos实例"""
    def __init__(self, round_num, node_id, redis_client):
        self.round_num = round_num
        self.node_id = node_id
        self.redis_client = redis_client
        
        # 创建PAL角色
        self.proposer = Proposer(node_id, redis_client)
        self.acceptor = Acceptor(node_id, redis_client)
        self.learner = Learner(node_id, redis_client)
        
        # 创建三个线程
        self.proposer_thread = threading.Thread(target=self.run_proposer)
        self.acceptor_thread = threading.Thread(target=self.run_acceptor)
        self.learner_thread = threading.Thread(target=self.run_learner)
        
        self.is_finished = False
        
    def start(self):
        """启动所有线程"""
        self.proposer_thread.start()
        self.acceptor_thread.start()
        self.learner_thread.start()
        
    def run_proposer(self):
        """处理Proposer相关的消息"""
        while not self.is_finished:
            try:
                # 从proposer队列获取消息
                msg = self.redis_client.brpop(f'proposer_{self.round_num}_queue', timeout=1)
                if msg:
                    msg_dict = json.loads(msg[1])
                    if msg_dict['turn'] == self.round_num:
                        self.proposer.handle_message(msg_dict)
            except Exception as e:
                print(f"Error in proposer thread: {e}")
                time.sleep(1)
                    
    def run_acceptor(self):
        """处理Acceptor相关的消息"""
        while not self.is_finished:
            try:
                # 从acceptor队列获取消息
                msg = self.redis_client.brpop(f'acceptor_{self.round_num}_queue', timeout=1)
                if msg:
                    msg_dict = json.loads(msg[1])
                    if msg_dict['turn'] == self.round_num:
                        # 根据消息类型调用不同的处理方法
                        if msg_dict['type'] == 'prepareRequest':
                            self.acceptor.handle_prepare(msg_dict)
                        elif msg_dict['type'] == 'acceptRequest':
                            self.acceptor.handle_accept(msg_dict)
            except Exception as e:
                print(f"Error in acceptor thread: {e}")
                time.sleep(1)
                    
    def run_learner(self):
        """处理Learner相关的消息"""
        while not self.is_finished:
            try:
                # 从learner队列获取消息
                msg = self.redis_client.brpop(f'learner_{self.round_num}_queue', timeout=1)
                if msg:
                    msg_dict = json.loads(msg[1])
                    if msg_dict['turn'] == self.round_num:
                        self.learner.learn(msg_dict)
                        if msg_dict.get('final_value'):
                            self.is_finished = True
            except Exception as e:
                print(f"Error in learner thread: {e}")
                time.sleep(1)

    def broadcast_decision(self, value):
        """广播已达成的决议"""
        msg = NodeMessage()
        msg.type = 'decision'
        msg.source = self.node_id
        msg.turn = self.round_num
        msg.value = value
        msg.final_value = True
        
        # 将消息发送给所有节点的learner
        self.redis_client.lpush(f'learner_{self.round_num}_queue', json.dumps(msg))

class RoundManager:
    """管理多轮Paxos实例"""
    def __init__(self, node_id, redis_client):
        self.node_id = node_id
        self.redis_client = redis_client
        self.rounds = {}  # round_num -> Round
        self.current_round = 0
        self.max_rounds = 10  # 最大同时运行的轮次数
        
    def start_new_round(self):
        """启动新的一轮Paxos"""
        if len(self.rounds) < self.max_rounds:
            round_num = self.current_round
            new_round = Round(round_num, self.node_id, self.redis_client)
            self.rounds[round_num] = new_round
            new_round.start()
            self.current_round += 1
            
    def handle_message(self, msg):
        """处理接收到的消息"""
        round_num = msg['turn']
        if round_num not in self.rounds:
            # 如果是新的轮次，创建新的Round实例
            if round_num >= self.current_round:
                self.start_new_round()
                
        if round_num in self.rounds:
            # 根据消息类型将消息放入相应队列
            target_queue = f"{msg['targetAgent']}_{round_num}_queue"
            self.redis_client.lpush(target_queue, json.dumps(msg))
            
    def check_finished_rounds(self):
        """检查并清理已完成的轮次"""
        finished_rounds = []
        for round_num, round_instance in self.rounds.items():
            if round_instance.is_finished:
                finished_rounds.append(round_num)
                
        for round_num in finished_rounds:
            del self.rounds[round_num]
            
    def sync_with_other_nodes(self):
        """与其他节点同步状态"""
        # TODO: 实现节点间的状态同步
        pass 

    def handle_command(self, command):
        """处理写入命令"""
        try:
            if command['operation'] == 'write':
                print(f"Creating proposal for command: {command}")  # 添加日志
                # 创建提案
                proposal = {
                    'type': 'write',
                    'key': command['key'],
                    'value': command['value'],
                    'timestamp': time.time()
                }
                
                # 如果当前轮次还没开始，启动新的轮次
                if self.current_round not in self.rounds:
                    self.start_new_round()
                
                print(f"Current round: {self.current_round}")  # 添加日志
                # 将提案发送给当前轮次的 proposer
                current_round = self.rounds[self.current_round - 1]
                current_round.proposer.prepare(proposal)
                print(f"Proposal sent to proposer")  # 添加日志
        except Exception as e:
            print(f"Error handling command: {e}") 