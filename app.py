from flask import Flask, request
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.json

    text = data.get("message", {}).get("text", "")

    print("NEW COMMENT:")
    print(text)

    if text:

        prompt = f"""
        Проанализируй комментарий пользователя.

        Определи:
        1. Тему обучения
        2. Тип вопроса
        3. Нужен ли менеджер
        4. Температуру лида

        Комментарий:
        {text}
        """

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response.choices[0].message.content

        print("AI ANALYSIS:")
        print(result)

    return "ok"

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
