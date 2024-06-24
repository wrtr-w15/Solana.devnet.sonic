# Solana Transaction Sender

Этот проект предназначен для отправки транзакций на блокчейне Solana с использованием нескольких кошельков. Скрипт поддерживает случайные задержки между транзакциями и отправляет уведомления в Telegram по завершении каждой серии транзакций или при недостатке средств на кошельке.

## Установка

1. **Создайте виртуальное окружение:**

   ```bash
   python -m venv venv
2. **Активируйте виртуальное окружение:**

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
