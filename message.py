# message.py - 消息定义
class NodeMessage:
    def __init__(self):
        self.type = None  # 消息类型：'prepareRequest', 'prepareRespond', 'acceptRequest', 'acceptRespond', 'BroadcastAccept'
        self.source = None  # 发送者地址
        self.target = None  # 接收者地址
        self.targetAgent = None  # 需要处理该消息的角色
        self.turn = None  # 当前处理的轮次
        self.number = None  # 提案编号
        self.value = None  # 提案内容 (Dict或JSON格式)
        self.promise = None  # acceptor做出的promise
        self.accept = None  # acceptor是否接受提案

    def to_dict(self):
        return {
            'type': self.type,
            'source': self.source,
            'target': self.target,
            'targetAgent': self.targetAgent,
            'turn': self.turn,
            'number': self.number,
            'value': self.value,
            'promise': self.promise,
            'accept': self.accept
        }
