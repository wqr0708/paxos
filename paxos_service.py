import redis
import os
from multi_paxos import RoundManager
import time
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_command_queue(redis_client, round_manager):
    """处理写入命令队列"""
    logger.info("Command queue processor started")
    while True:
        try:
            # 从命令队列获取消息
            message = redis_client.brpop('command_queue', timeout=1)
            if message:
                command = json.loads(message[1])
                logger.info(f"Processing command: {command}")
                # 启动新的 Paxos 轮次处理该命令
                round_manager.start_new_round()
                round_manager.handle_command(command)
        except Exception as e:
            logger.error(f"Error processing command: {e}")
        time.sleep(0.1)

def main():
    try:
        # 从环境变量获取配置
        redis_host = os.environ.get('REDIS_HOST', 'redis')
        node_id = os.environ.get('NODE_ID', 'node1')
        
        logger.info(f"Starting paxos service with node_id={node_id}, redis_host={redis_host}")
        
        # 连接Redis
        redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)
        redis_client.ping()  # 测试连接
        logger.info("Connected to Redis")
        
        # 创建RoundManager实例
        round_manager = RoundManager(node_id=node_id, redis_client=redis_client)
        
        # 启动第一轮
        round_manager.start_new_round()
        logger.info("First round started")
        
        # 启动命令处理线程
        import threading
        command_thread = threading.Thread(
            target=process_command_queue, 
            args=(redis_client, round_manager),
            daemon=True
        )
        command_thread.start()
        logger.info("Command processor thread started")
        
        # 持续运行并检查已完成的轮次
        while True:
            round_manager.check_finished_rounds()
            # 每隔一段时间尝试同步状态
            round_manager.sync_with_other_nodes()
            time.sleep(5)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main() 