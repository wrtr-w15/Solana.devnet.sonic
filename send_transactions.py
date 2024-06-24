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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("send_transactions.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
sender_secret_key = config.get('sender_secret_key')

if not rpc_url or not sender_secret_key:
    logging.error("Пожалуйста, проверьте наличие всех необходимых параметров в config.json")
    exit(1)

# Загружаем ключ отправителя
try:
    sender_keypair = Keypair.from_secret_key(base58.b58decode(sender_secret_key))
    logging.info("Ключ отправителя успешно загружен")
except Exception as e:
    logging.error(f"Ошибка при загрузке ключа отправителя: {e}")
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

async def send_sol(recipient_public_key):
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
                    lamports=1000,  # Укажите количество лампортов для перевода
                )
            )
        )
        transaction.recent_blockhash = recent_blockhash

        # Подпишем транзакцию
        transaction.sign(sender_keypair)

        # Отправим транзакцию
        response = await client.send_transaction(transaction, sender_keypair)
        logging.info(f'Транзакция отправлена на {recipient_public_key}: {response["result"]}')

    except Exception as e:
        logging.error(f'Ошибка отправки транзакции на {recipient_public_key}: {str(e)}')

async def main():
    tasks = []
    for _ in range(transaction_count):
        recipient = random.choice(recipient_wallets)
        tasks.append(send_sol(recipient))
        random_interval = random.randint(min_delay, max_delay)
        logging.info(f"Ожидание {random_interval} секунд перед следующей транзакцией")
        await asyncio.sleep(random_interval)

    await asyncio.gather(*tasks)

# Запуск отправки транзакций
try:
    asyncio.run(main())
    logging.info("Все транзакции успешно отправлены")
except Exception as e:
    logging.error(f"Ошибка выполнения основной функции: {e}")
