# server.py - HTTP服务器
app = Flask(__name__)

@app.route('/propose', methods=['POST'])
def propose():
    # 处理提案请求
    pass