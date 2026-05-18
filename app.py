from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    print("NEW COMMENT:")
    print(data)

    return "ok"

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
