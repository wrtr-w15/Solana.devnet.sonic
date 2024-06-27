import asyncio
import random
import json
import logging
import pandas as pd
import base58
import requests
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.keypair import Keypair
from solana.publickey import PublicKey
from telegram_notify import send_telegram_message
from faucet_collector import main as collect_faucet
import inquirer
from twocaptcha import TwoCaptcha

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("send_transactions.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def decode_secret_key(secret_key):
    try:
        return Keypair.from_secret_key(base58.b58decode(secret_key))
    except Exception as e:
        logging.error(f"Ошибка декодирования секретного ключа: {e}")
        raise

async def check_balance(client, public_key):
    try:
        response = await client.get_balance(public_key)
        logging.info(f"Ответ от Solana API для баланса: {response}")
        balance_lamports = response['result']['value']
        balance_sol = balance_lamports / 1_000_000_000  # Преобразование лампортов в SOL
        logging.info(f"Баланс для {public_key}: {balance_sol} SOL ({balance_lamports} лампортов)")
        return balance_sol
    except Exception as e:
        logging.error(f"Ошибка при проверке баланса: {e}")
        return 0

def validate_public_key(pub_key_str):
    try:
        return PublicKey(pub_key_str)
    except Exception as e:
        logging.error(f"Неверный публичный ключ: {pub_key_str} - {e}")
        return None

def load_proxies(proxy_file):
    with open(proxy_file, 'r') as file:
        proxies = file.read().splitlines()
    return proxies

def check_proxies(proxies):
    for proxy in proxies:
        try:
            proxy_parts = proxy.split('@')
            if len(proxy_parts) == 2:
                auth = proxy_parts[0]
                proxy_url = proxy_parts[1]
                proxy_formatted = {
                    "http": f"http://{auth}@{proxy_url}",
                    "https": f"http://{auth}@{proxy_url}"
                }
            else:
                proxy_formatted = {
                    "http": f"http://{proxy}",
                    "https": f"http://{proxy}"
                }
            response = requests.get("http://www.google.com", proxies=proxy_formatted, timeout=5)
            if response.status_code == 200:
                logging.info(f"Прокси {proxy} работает")
            else:
                logging.error(f"Прокси {proxy} не работает")
        except Exception as e:
            logging.error(f"Ошибка при проверке прокси {proxy}: {e}")

def check_2captcha(api_key):
    solver = TwoCaptcha(api_key)

    try:
        result = solver.balance()
        logging.info(f"2Captcha API ключ работает: баланс {result} USD")
    except Exception as e:
        logging.error(f"Ошибка при проверке 2Captcha API ключа: {e}")

def check_private_keys(senders_file):
    try:
        df = pd.read_excel(senders_file, engine='openpyxl')
        private_keys = df['PrivateKey'].dropna().tolist()
        for key in private_keys:
            try:
                keypair = Keypair.from_secret_key(base58.b58decode(key))
                logging.info(f"Приватный ключ валиден: {keypair.public_key}")
            except Exception as e:
                logging.error(f"Ошибка при проверке приватного ключа: {e}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке приватных ключей из Excel файла: {e}")

def check_recipient_wallets(wallet_file):
    try:
        with open(wallet_file, 'r', encoding='utf-8') as wallets_file:
            recipient_wallets = [validate_public_key(line.strip()) for line in wallets_file.readlines()]
        recipient_wallets = [pk for pk in recipient_wallets if pk is not None]
        for wallet in recipient_wallets:
            logging.info(f"Валидный адрес получателя: {wallet}")
    except Exception as e:
        logging.error(f"Ошибка при загрузке адресов получателей: {e}")

async def send_sol(sender_keypair, recipient_public_key, amount):
    try:
        response = await client.get_recent_blockhash()
        recent_blockhash = response['result']['value']['blockhash']
        transaction = Transaction().add(
            transfer(
                TransferParams(
                    from_pubkey=sender_keypair.public_key,
                    to_pubkey=recipient_public_key,
                    lamports=int(amount * 1_000_000_000),  # Преобразование SOL в лампорты
                )
            )
        )
        transaction.recent_blockhash = recent_blockhash
        transaction.sign(sender_keypair)
        response = await client.send_transaction(transaction, sender_keypair)
        logging.info(f'Транзакция отправлена с {sender_keypair.public_key} на {recipient_public_key}: {response["result"]}')
        return True
    except Exception as e:
        logging.error(f'Ошибка отправки транзакции на {recipient_public_key}: {str(e)}')
        return False

async def process_transactions(sender_keypairs, recipient_wallets, transaction_count, min_amount, max_amount):
    send_counts = {str(kp.public_key): 0 for kp in sender_keypairs}
    while any(count < transaction_count for count in send_counts.values()):
        sender_keypair = random.choice(sender_keypairs)
        if send_counts[str(sender_keypair.public_key)] >= transaction_count:
            continue
        balance = await check_balance(client, sender_keypair.public_key)
        if balance < min_amount:
            error_message = f"<b>Недостаточно средств</b> на кошельке {sender_keypair.public_key}. Баланс: {balance} SOL."
            logging.error(error_message)
            send_telegram_message(telegram_bot_token, telegram_chat_id, error_message)
            sender_keypairs.remove(sender_keypair)
            if not sender_keypairs:
                logging.error("Нет доступных кошельков для отправки транзакций")
                return
            continue
        recipient = random.choice(recipient_wallets)
        amount = random.uniform(min_amount, max_amount)
        success = await send_sol(sender_keypair, recipient, amount)
        if success:
            send_counts[str(sender_keypair.public_key)] += 1
            # Отправка уведомления в Telegram и запись в лог
            transaction_message = (f"Кошелек {sender_keypair.public_key} отправил {send_counts[str(sender_keypair.public_key)]} транзакций.")
            send_telegram_message(telegram_bot_token, telegram_chat_id, transaction_message)
            logging.info(transaction_message)
        random_interval = random.randint(min_delay, max_delay)
        logging.info(f"Ожидание {random_interval} секунд перед следующей транзакцией")
        await asyncio.sleep(random_interval)
    for sender_keypair in sender_keypairs:
        public_key = str(sender_keypair.public_key)
        success_message = (f"<b>Кошелек ({public_key})</b> "
                           f"успешно отправил {send_counts[public_key]} транзакций. ✅")
        send_telegram_message(telegram_bot_token, telegram_chat_id, success_message)

async def main_process():
    await process_transactions(sender_keypairs, recipient_wallets, transaction_count, min_transaction_amount, max_transaction_amount)

def main():
    while True:
        questions = [
            inquirer.List('action',
                message="Выберите действие",
                choices=['Сбор крана', 'Проверка 2Captcha API', 'Проверка прокси', 'Проверка приватников', 'Проверка кошельков получателя', 'Запуск основного скрипта', 'Выход'],
            ),
        ]
        answers = inquirer.prompt(questions)
        action = answers['action']

        try:
            with open('config.json', 'r', encoding='utf-8') as config_file:
                config = json.load(config_file)
            logging.info("Конфигурационный файл успешно загружен")
        except Exception as e:
            logging.error(f"Ошибка при загрузке конфигурационного файла: {e}")
            return

        global client, telegram_bot_token, telegram_chat_id, sender_keypairs, recipient_wallets, transaction_count, min_delay, max_delay, min_transaction_amount, max_transaction_amount

        client = AsyncClient(config.get('rpc_url'))
        telegram_bot_token = config.get('telegram_bot_token')
        telegram_chat_id = config.get('telegram_chat_id')
        transaction_count = config.get('transaction_count', 100)
        min_delay = config.get('min_delay', 30)
        max_delay = config.get('max_delay', 180)
        min_transaction_amount = config.get('min_transaction_amount', 0.001)
        max_transaction_amount = config.get('max_transaction_amount', 0.01)
        senders_file = config.get('senders_file', 'senders.xlsx')
        proxy_file = config.get('proxy_file', 'proxies.txt')
        wallet_file = 'wallets.txt'
        captcha_api_key = config.get('2captcha_api_key')

        if action == 'Сбор крана':
            collect_faucet()
        elif action == 'Проверка 2Captcha API':
            check_2captcha(captcha_api_key)
        elif action == 'Проверка прокси':
            proxies = load_proxies(proxy_file)
            check_proxies(proxies)
        elif action == 'Проверка приватников':
            check_private_keys(senders_file)
        elif action == 'Проверка кошельков получателя':
            check_recipient_wallets(wallet_file)
        elif action == 'Запуск основного скрипта':
            # Загружаем ключи отправителей из Excel файла
            try:
                df = pd.read_excel(senders_file, engine='openpyxl')
                private_keys = df['PrivateKey'].dropna().tolist()
                sender_keypairs = [decode_secret_key(key) for key in private_keys]
                logging.info("Ключи отправителей успешно загружены из Excel файла")
            except Exception as e:
                logging.error(f"Ошибка при загрузке ключей отправителей из Excel файла: {e}")
                return

            # Загружаем и проверяем адреса получателей
            try:
                with open(wallet_file, 'r', encoding='utf-8') as wallets_file:
                    recipient_wallets = [validate_public_key(line.strip()) for line in wallets_file.readlines()]
                recipient_wallets = [pk for pk in recipient_wallets if pk is not None]
                if not recipient_wallets:
                    raise ValueError("Список кошельков получателей пуст или содержит только неверные ключи.")
                logging.info(f"Успешно загружено {len(recipient_wallets)} валидных адресов получателей")
            except Exception as e:
                logging.error(f"Ошибка при загрузке адресов получателей: {e}")
                return

            # Запуск отправки транзакций
            try:
                asyncio.run(main_process())
                logging.info("Все транзакции успешно отправлены")
            except Exception as e:
                logging.error(f"Ошибка выполнения основной функции: {e}")
        elif action == 'Выход':
            logging.info("Завершение программы")
            break

if __name__ == "__main__":
    main()
