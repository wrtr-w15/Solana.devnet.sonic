# Solana Transaction Sender

Этот проект предназначен для отправки транзакций на блокчейне Solana с использованием нескольких кошельков. Скрипт поддерживает случайные задержки между транзакциями и отправляет уведомления в Telegram по завершении каждой серии транзакций или при недостатке средств на кошельке.

## Установка

1. **Создайте виртуальное окружение:**

   ```bash
   python -m venv venv
2. **Активируйте виртуальное окружение:**

   ```bash
   .\venv\Scripts\activate

3. **Установите необходимые пакеты:**

   ```bash
   pip install -r requirements.txt

## Настройка

**rpc_url**: URL RPC сервера Solana.

**transaction_count**: Количество транзакций для отправки каждым кошельком.

**min_delay**: Минимальная задержка между транзакциями в секундах.

**max_delay**: Максимальная задержка между транзакциями в секундах.

**senders**: Список секретных ключей отправителей в формате Base58.

**transaction_amount**: Сумма каждой транзакции в SOL.

**telegram_bot_token**: Токен вашего Telegram-бота.

**telegram_chat_id**: ID чата в Telegram, куда будут отправляться уведомления
