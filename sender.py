import redis
import json
import requests
from multiprocessing import Pool
import os

class Sender:
    def __init__(self, redis_client, num_workers=4):
        self.redis_client = redis_client
        self.pool = Pool(num_workers)
        
    def start(self):
        while True:
            try:
                # 从队列中获取消息
                message = self.redis_client.brpop('sender_queue', timeout=1)
                if message:
                    msg_dict = json.loads(message[1])
                    # 使用进程池并行发送消息
                    self.pool.apply_async(self.send_message, (msg_dict,))
            except Exception as e:
                print(f"Error in sender: {e}")
                
    def send_message(self, msg_dict):
        try:
            url = f"http://{msg_dict['target']}/message"
            response = requests.post(url, json=msg_dict)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

def main():
    # 从环境变量获取配置
    redis_host = os.environ.get('REDIS_HOST', 'redis')
    
    # 连接Redis
    redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)
    
    # 创建并启动sender
    sender = Sender(redis_client)
    sender.start()

if __name__ == "__main__":
    main() 