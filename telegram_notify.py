import logging
import requests

def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"Ошибка отправки уведомления в Telegram: {response.text}")
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления в Telegram: {e}")
