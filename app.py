from flask import Flask, request
from openai import OpenAI
import os
import json

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    message = data.get("message", {})

    text = message.get("text", "")
    user = message.get("from", {})
    username = user.get("username", "без username")
    first_name = user.get("first_name", "")

    # Пытаемся достать текст поста, под которым оставлен комментарий
    reply_to_message = message.get("reply_to_message", {})
    post_text = reply_to_message.get("text", "") or reply_to_message.get("caption", "")

    if not text:
        return "ok"

    prompt = f"""
Ты анализируешь комментарии под Telegram-каналом учебного центра по БПЛА.

Твоя задача:
1. Понять, нужно ли передать комментарий менеджеру в amoCRM.
2. Определить тему обучения.
3. Учитывать не только комментарий, но и пост, под которым он написан.

Темы обучения:
- Оператор БПЛА
- Оператор FPV
- Анти-БПЛА / защита объектов
- Аналитик данных с БПЛА
- Техник БПЛА
- Инструктор БПЛА
- Инструктор FPV
- Бесплатный инструктор для СВО
- Документы / удостоверение / летная книжка
- Стоимость обучения
- Расписание / сроки
- Формат обучения
- Обучение для организаций
- Трудоустройство
- Общая консультация

Важно:
Если комментарий короткий и непонятный, но под постом явно указана тема обучения, определи тему по посту.

Например:
Пост про FPV, комментарий: «С кем можно поговорить?»
→ тема: Оператор FPV
→ отправить в CRM: да

Пост про бесплатного инструктора для SVO, комментарий: «Как связаться?»
→ тема: Бесплатный инструктор для SVO
→ отправить в CRM: да

В amoCRM отправлять, если:
- человек спрашивает стоимость;
- хочет записаться;
- спрашивает про курс;
- спрашивает про документы;
- спрашивает сроки или расписание;
- интересуется обучением для компании;
- спрашивает «с кем можно поговорить»;
- спрашивает «куда написать»;
- спрашивает «кто проконсультирует»;
- просит контакт;
- хочет обсудить вопрос;
- задает вопрос, на который должен ответить менеджер;
- пишет негатив, жалобу или возражение.

Не отправлять в amoCRM:
- спасибо;
- класс;
- огонь;
- emoji;
- обычные реакции;
- комментарии без вопроса и без интереса к обучению.

Верни строго JSON без пояснений:

{{
  "send_to_crm": true или false,
  "course_topic": "тема обучения",
  "question_type": "тип вопроса",
  "manager_task": "что должен сделать менеджер",
  "reason": "почему так решил"
}}

Текст поста:
{post_text}

Комментарий пользователя:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    result_text = response.choices[0].message.content

    print("NEW COMMENT:")
    print(text)

    print("POST TEXT:")
    print(post_text)

    print("USERNAME:")
    print(username)

    print("FIRST NAME:")
    print(first_name)

    print("AI RESULT:")
    print(result_text)

    try:
        analysis = json.loads(result_text)
    except Exception:
        print("AI returned not JSON")
        return "ok"

    if analysis.get("send_to_crm") == True:
        print("SEND TO CRM: YES")
        print("Тут дальше будет создание сделки в amoCRM")
    else:
        print("SEND TO CRM: NO")

    return "ok"

@app.route('/')
def home():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
