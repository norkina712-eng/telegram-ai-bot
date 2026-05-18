from flask import Flask, request
from groq import Groq
import os
import json
import requests
import time

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

AMO_DOMAIN = os.getenv("AMO_DOMAIN")
AMO_ACCESS_TOKEN = os.getenv("AMO_ACCESS_TOKEN")


def amo_headers():
    return {
        "Authorization": f"Bearer {AMO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


def create_contact(first_name, username, telegram_id):
    contact_name = first_name or username or f"Telegram ID {telegram_id}"

    telegram_link = ""
    if username and username != "без username":
        telegram_link = f"https://t.me/{username}"

    url = f"https://{AMO_DOMAIN}/api/v4/contacts"

    payload = [
        {
            "name": contact_name,
            "custom_fields_values": []
        }
    ]

    response = requests.post(url, headers=amo_headers(), json=payload)

    print("CREATE CONTACT RESPONSE:")
    print(response.status_code)
    print(response.text)

    if response.status_code not in [200, 201]:
        return None

    return response.json()["_embedded"]["contacts"][0]["id"]


def create_lead(course_topic, contact_id):
    lead_name = f"Telegram | {course_topic}"

    url = f"https://{AMO_DOMAIN}/api/v4/leads"

    payload = [
        {
            "name": lead_name,
            "_embedded": {
                "contacts": [
                    {
                        "id": contact_id
                    }
                ]
            }
        }
    ]

    response = requests.post(url, headers=amo_headers(), json=payload)

    print("CREATE LEAD RESPONSE:")
    print(response.status_code)
    print(response.text)

    if response.status_code not in [200, 201]:
        return None

    return response.json()["_embedded"]["leads"][0]["id"]


def add_note_to_lead(lead_id, note_text):
    url = f"https://{AMO_DOMAIN}/api/v4/leads/{lead_id}/notes"

    payload = [
        {
            "note_type": "common",
            "params": {
                "text": note_text
            }
        }
    ]

    response = requests.post(url, headers=amo_headers(), json=payload)

    print("ADD NOTE RESPONSE:")
    print(response.status_code)
    print(response.text)


def create_task(lead_id, task_text):
    url = f"https://{AMO_DOMAIN}/api/v4/tasks"

    payload = [
        {
            "entity_id": lead_id,
            "entity_type": "leads",
            "task_type_id": 1,
            "text": task_text,
            "complete_till": int(time.time()) + 3600
        }
    ]

    response = requests.post(url, headers=amo_headers(), json=payload)

    print("CREATE TASK RESPONSE:")
    print(response.status_code)
    print(response.text)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    message = data.get("message", {})

    text = message.get("text", "")
    user = message.get("from", {})

    telegram_id = user.get("id", "")
    username = user.get("username", "")
    first_name = user.get("first_name", "")

    reply_to_message = message.get("reply_to_message", {})
    post_text = reply_to_message.get("text", "") or reply_to_message.get("caption", "")

    if not text:
        return "ok"

    prompt = f"""
Ты анализируешь комментарии под Telegram-каналом учебного центра по БПЛА.

Определи:
1. Нужно ли отправить комментарий в amoCRM.
2. Тему обучения.
3. Тип вопроса.
4. Что должен сделать менеджер.

Темы:
- Оператор БПЛА
- Оператор FPV
- Анти-БПЛА
- Аналитик данных с БПЛА
- Техник БПЛА
- Инструктор БПЛА
- Инструктор FPV
- Бесплатный инструктор для SVO
- Документы
- Стоимость
- Расписание
- Формат обучения
- Обучение для организаций
- Трудоустройство
- Общая консультация

В amoCRM отправлять, если:
- пользователь хочет связаться;
- спрашивает стоимость;
- спрашивает про курс;
- просит консультацию;
- хочет записаться;
- спрашивает контакты;
- пишет негатив;
- спрашивает, с кем поговорить;
- пишет: куда написать, кто проконсультирует, можно обсудить, как связаться.

Не отправлять:
- emoji;
- спасибо;
- класс;
- огонь;
- обычные реакции без вопроса.

Верни только чистый JSON без markdown и без ```json.

Формат ответа:
{{
  "send_to_crm": true,
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
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    result_text = response.choices[0].message.content

    print("AI RESULT:")
    print(result_text)

    clean_result = result_text.strip()
    clean_result = clean_result.replace("```json", "")
    clean_result = clean_result.replace("```", "")
    clean_result = clean_result.strip()

    try:
        analysis = json.loads(clean_result)
    except Exception as e:
        print("AI returned invalid JSON")
        print(e)
        return "ok"

    if analysis.get("send_to_crm") is not True:
        print("SEND TO CRM: NO")
        return "ok"

    telegram_link = "Username не указан"
    if username:
        telegram_link = f"https://t.me/{username}"

    contact_id = create_contact(first_name, username, telegram_id)

    if not contact_id:
        print("CONTACT WAS NOT CREATED")
        return "ok"

    lead_id = create_lead(analysis.get("course_topic"), contact_id)

    if not lead_id:
        print("LEAD WAS NOT CREATED")
        return "ok"

    note_text = f"""
Новая заявка из Telegram-комментария.

Комментарий пользователя:
{text}

Текст поста:
{post_text}

Тема обучения:
{analysis.get("course_topic")}

Тип вопроса:
{analysis.get("question_type")}

Задача менеджеру:
{analysis.get("manager_task")}

Telegram:
@{username if username else "username не указан"}

Ссылка для связи:
{telegram_link}

Имя:
{first_name}

Telegram ID:
{telegram_id}
"""

    add_note_to_lead(lead_id, note_text)

    task_text = f"Ответить пользователю в Telegram: {telegram_link}"
    create_task(lead_id, task_text)

    return "ok"


@app.route('/')
def home():
    return "Bot is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
