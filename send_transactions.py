import asyncio
import random
import json
import logging
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solana.system_program import TransferParams, transfer
from solana.keypair import Keypair
from solana.publickey import PublicKey
import base58
from telegram_notify import send_telegram_message

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

# Загружаем конфигурацию
try:
    with open('config.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)
    logging.info("Конфигурационный файл успешно загружен")
except Exception as e:
    logging.error(f"Ошибка при загрузке конфигурационного файла: {e}")
    exit(1)

rpc_url = config.get('rpc_url')
transaction_count = config.get('transaction_count', 100)
min_delay = config.get('min_delay', 30)
max_delay = config.get('max_delay', 180)
senders = config.get('senders', [])
transaction_amount = config.get('transaction_amount', 0.01)  # Сумма каждой транзакции в SOL
telegram_bot_token = config.get('telegram_bot_token')
telegram_chat_id = config.get('telegram_chat_id')

if not rpc_url or not senders:
    logging.error("Пожалуйста, проверьте наличие всех необходимых параметров в config.json")
    exit(1)

# Загружаем ключи отправителей
try:
    sender_keypairs = [decode_secret_key(sender) for sender in senders]
    logging.info("Ключи отправителей успешно загружены")
except Exception as e:
    logging.error(f"Ошибка при загрузке ключей отправителей: {e}")
    exit(1)

# Загружаем адреса получателей
try:
    with open('wallets.txt', 'r', encoding='utf-8') as wallets_file:
        recipient_wallets = [PublicKey(line.strip()) for line in wallets_file.readlines()]
    logging.info(f"Успешно загружено {len(recipient_wallets)} адресов получателей")
except Exception as e:
    logging.error(f"Ошибка при загрузке адресов получателей: {e}")
    exit(1)

# Устанавливаем соединение с RPC
client = AsyncClient(rpc_url)

async def send_sol(sender_keypair, recipient_public_key):
    try:
        # Получаем текущую информацию о блоке для nonce
        response = await client.get_recent_blockhash()
        recent_blockhash = response['result']['value']['blockhash']

        # Создаем транзакцию
        transaction = Transaction().add(
            transfer(
                TransferParams(
                    from_pubkey=sender_keypair.public_key,
                    to_pubkey=recipient_public_key,
                    lamports=int(transaction_amount * 1_000_000_000),  # Преобразование SOL в лампорты
                )
            )
        )
        transaction.recent_blockhash = recent_blockhash

        # Подпишем транзакцию
        transaction.sign(sender_keypair)

        # Отправим транзакцию
        response = await client.send_transaction(transaction, sender_keypair)
        logging.info(f'Транзакция отправлена на {recipient_public_key}: {response["result"]}')
        return True

    except Exception as e:
        logging.error(f'Ошибка отправки транзакции на {recipient_public_key}: {str(e)}')
        return False

async def process_sender(sender_keypair, sender_index):
    balance = await check_balance(client, sender_keypair.public_key)
    logging.info(f'Баланс кошелька {sender_keypair.public_key}: {balance} SOL')
    if balance < transaction_amount * transaction_count:
        error_message = f"<b>Недостаточно средств</b> на кошельке {sender_index} для отправки {transaction_count} транзакций. Баланс: {balance} SOL."
        logging.error(error_message)
        send_telegram_message(telegram_bot_token, telegram_chat_id, error_message)
        return

    success_count = 0
    fail_count = 0

    for _ in range(transaction_count):
        recipient = random.choice(recipient_wallets)
        success = await send_sol(sender_keypair, recipient)
        if success:
            success_count += 1
        else:
            fail_count += 1
        
        random_interval = random.randint(min_delay, max_delay)
        logging.info(f"Ожидание {random_interval} секунд перед следующей транзакцией")
        await asyncio.sleep(random_interval)
    
    success_message = f"<b>Кошелек {sender_index}</b> успешно отправил {success_count} транзакций. ✅\n"
    fail_message = f"<b>Кошелек {sender_index}</b> не смог отправить {fail_count} транзакций. ❌"
    send_telegram_message(telegram_bot_token, telegram_chat_id, success_message + fail_message)

async def main():
    for index, sender_keypair in enumerate(sender_keypairs, start=1):
        await process_sender(sender_keypair, index)

# Запуск отправки транзакций
try:
    asyncio.run(main())
    logging.info("Все транзакции успешно отправлены")
except Exception as e:
    logging.error(f"Ошибка выполнения основной функции: {e}")
