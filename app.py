from flask import Flask, request
from openai import OpenAI
import os
import json
import requests

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AMO_DOMAIN = os.getenv("AMO_DOMAIN")
AMO_ACCESS_TOKEN = os.getenv("AMO_ACCESS_TOKEN")

@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.json

    message = data.get("message", {})

    text = message.get("text", "")
    user = message.get("from", {})

    username = user.get("username", "без username")
    first_name = user.get("first_name", "")

    reply_to_message = message.get("reply_to_message", {})
    post_text = reply_to_message.get("text", "") or reply_to_message.get("caption", "")

    if not text:
        return "ok"

    prompt = f"""
Ты анализируешь комментарии под Telegram-каналом учебного центра по БПЛА.

Определи:
1. Нужно ли отправить комментарий в amoCRM
2. Тему обучения
3. Тип вопроса
4. Что должен сделать менеджер

Темы:
- Оператор БПЛА
- Оператор FPV
- Анти-БПЛА
- Аналитик данных с БПЛА
- Техник БПЛА
- Инструктор БПЛА
- Инструктор FPV
- Бесплатный инструктор для СВО
- Документы
- Стоимость
- Расписание
- Формат обучения
- Обучение для организаций
- Трудоустройство
- Общая консультация

В amoCRM отправлять если:
- пользователь хочет связаться;
- спрашивает стоимость;
- спрашивает курс;
- просит консультацию;
- хочет записаться;
- спрашивает контакты;
- пишет негатив;
- спрашивает с кем поговорить.

Не отправлять:
- emoji
- спасибо
- класс
- реакции без вопроса

Верни строго JSON:

{{
  "send_to_crm": true или false,
  "course_topic": "тема",
  "question_type": "тип вопроса",
  "manager_task": "задача менеджеру"
}}

Текст поста:
{post_text}

Комментарий:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    result_text = response.choices[0].message.content

    print("AI RESULT:")
    print(result_text)

    try:
        analysis = json.loads(result_text)
    except Exception:
        print("AI returned invalid JSON")
        return "ok"

    if analysis.get("send_to_crm") == True:

        lead_name = f"Telegram | {analysis.get('course_topic')}"

        note_text = f"""
Комментарий: {text}

Username: @{username}

Имя: {first_name}

Тема: {analysis.get('course_topic')}

Тип вопроса: {analysis.get('question_type')}

Задача:
{analysis.get('manager_task')}
"""

        url = f"https://{AMO_DOMAIN}/api/v4/leads"

        headers = {
            "Authorization": f"Bearer {AMO_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = [
            {
                "name": lead_name
            }
        ]

        response = requests.post(
            url,
            headers=headers,
            json=payload
        )

        print("AMO RESPONSE:")
        print(response.status_code)
        print(response.text)

    else:
        print("SEND TO CRM: NO")

    return "ok"

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
