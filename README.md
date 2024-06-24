# Solana Transaction Sender

Этот проект предназначен для отправки транзакций на блокчейне Solana с использованием нескольких кошельков. Скрипт поддерживает случайные задержки между транзакциями и отправляет уведомления в Telegram по завершении каждой серии транзакций или при недостатке средств на кошельке.

## Установка

1. **Создайте виртуальное окружение:**

   ```bash
   python -m venv venv
Активируйте виртуальное окружение:

На Windows:
bash
Copy code
.\venv\Scripts\activate
На MacOS/Linux:
bash
Copy code
source venv/bin/activate
Установите необходимые пакеты:

bash
Copy code
pip install -r requirements.txt
Настройка
Создайте файл config.json в корневой директории проекта и заполните его следующими параметрами:

json
Copy code
{
    "rpc_url": "https://api.devnet.solana.com",
    "transaction_count": 100,
    "min_delay": 30,
    "max_delay": 180,
    "senders": [
        "СЕКРЕТНЫЙ КЛЮЧ 1 В BASE58",
        "СЕКРЕТНЫЙ КЛЮЧ 2 В BASE58"
    ],
    "transaction_amount": 0.01,
    "telegram_bot_token": "ВАШ ТЕЛЕГРАМ БОТ ТОКЕН",
    "telegram_chat_id": "ВАШ ТЕЛЕГРАМ ЧАТ ID"
}
rpc_url: URL RPC сервера Solana.
transaction_count: Количество транзакций для отправки каждым кошельком.
min_delay: Минимальная задержка между транзакциями в секундах.
max_delay: Максимальная задержка между транзакциями в секундах.
senders: Список секретных ключей отправителей в формате Base58.
transaction_amount: Сумма каждой транзакции в SOL.
telegram_bot_token: Токен вашего Telegram-бота.
telegram_chat_id: ID чата в Telegram, куда будут отправляться уведомления.
Создайте файл wallets.txt в корневой директории проекта и добавьте в него адреса получателей, по одному на строку:

python
Copy code
Адрес_получателя_1
Адрес_получателя_2
Адрес_получателя_3
...
Адрес_получателя_N
Запуск
Убедитесь, что виртуальное окружение активировано:

На Windows:
bash
Copy code
.\venv\Scripts\activate
На MacOS/Linux:
bash
Copy code
source venv/bin/activate
Запустите скрипт для отправки транзакций:

bash
Copy code
python send_transactions.py
Структура проекта
send_transactions.py: Основной скрипт для отправки транзакций.
telegram_notify.py: Скрипт для отправки уведомлений в Telegram.
config.json: Файл конфигурации проекта.
wallets.txt: Файл с адресами получателей.
requirements.txt: Файл с зависимостями проекта.
Пример уведомлений в Telegram
Успешное завершение серии транзакций:

css
Copy code
<b>Кошелек 1</b> успешно отправил 100 транзакций. ✅
Недостаточно средств:

css
Copy code
<b>Недостаточно средств</b> на кошельке 1 для отправки 100 транзакций. Баланс: 0.0 SOL.
Неудачные транзакции:

css
Copy code
<b>Кошелек 1</b> не смог отправить 10 транзакций. ❌
Логирование
Все события и ошибки записываются в файл send_transactions.log и выводятся в консоль.
