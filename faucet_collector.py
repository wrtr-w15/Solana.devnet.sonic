import time
import json
import logging
import requests
import random
from solana.keypair import Keypair
from solana.publickey import PublicKey
from selenium import webdriver
import pandas as pd
import base58
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twocaptcha import TwoCaptcha
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.proxy import Proxy, ProxyType

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("faucet_collector.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def solve_captcha(api_key, site_key, url):
    solver = TwoCaptcha(api_key)
    try:
        result = solver.recaptcha(sitekey=site_key, url=url)
        return result['code']
    except Exception as e:
        logging.error(f"Ошибка при решении капчи: {e}")
        return None

def load_proxies(proxy_file):
    with open(proxy_file, 'r') as file:
        proxies = file.read().splitlines()
    return proxies

def collect_faucet(api_key, proxies, faucet_url, public_key):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    
    if proxies:
        proxy = random.choice(proxies)
        proxy_parts = proxy.split('@')
        auth = proxy_parts[0]
        proxy_url = proxy_parts[1]
        options.add_argument(f'--proxy-server={proxy_url}')
        webdriver.DesiredCapabilities.CHROME['proxy'] = {
            "httpProxy": proxy_url,
            "ftpProxy": proxy_url,
            "sslProxy": proxy_url,
            "proxyType": "MANUAL",
        }
        webdriver.DesiredCapabilities.CHROME['proxy']['socksUsername'] = auth.split(':')[0]
        webdriver.DesiredCapabilities.CHROME['proxy']['socksPassword'] = auth.split(':')[1]

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(faucet_url)

    try:
        # Ожидаем загрузки страницы
        wait = WebDriverWait(driver, 15)
        wallet_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Wallet Address']")))

        # Ввод публичного ключа
        wallet_input.send_keys(public_key)

        # Нажимаем кнопку для сбора монет
        collect_button = driver.find_element(By.CSS_SELECTOR, "button[type='button']")
        collect_button.click()

        # Ожидаем капчу
        time.sleep(5)
        site_key = driver.find_element(By.CLASS_NAME, "g-recaptcha").get_attribute("data-sitekey")
        captcha_code = solve_captcha(api_key, site_key, faucet_url)
        
        if captcha_code:
            # Вводим решение капчи
            captcha_input = driver.find_element(By.ID, "g-recaptcha-response")
            driver.execute_script("arguments[0].style.display = 'block';", captcha_input)
            captcha_input.send_keys(captcha_code)

            # Нажимаем кнопку для подтверждения капчи
            confirm_button = driver.find_element(By.ID, "confirmButton")
            confirm_button.click()

            # Ожидаем завершения процесса сбора монет
            time.sleep(10)

        logging.info(f"Монеты успешно собраны для публичного ключа: {public_key}")
    except Exception as e:
        logging.error(f"Ошибка при сборе монет с крана: {e}")
    finally:
        driver.quit()

def main():
    try:
        with open('config.json', 'r', encoding='utf-8') as config_file:
            config = json.load(config_file)
        logging.info("Конфигурационный файл успешно загружен")
    except Exception as e:
        logging.error(f"Ошибка при загрузке конфигурационного файла: {e}")
        return

    if config.get("use_faucet", False):
        proxies = load_proxies(config.get('proxy_file', 'proxies.txt'))
        try:
            df = pd.read_excel(config['senders_file'], engine='openpyxl')
            private_keys = df['PrivateKey'].dropna().tolist()
            for private_key in private_keys:
                keypair = Keypair.from_secret_key(base58.b58decode(private_key))
                public_key = str(keypair.public_key)
                collect_faucet(config['2captcha_api_key'], proxies, config['faucet_url'], public_key)
        except Exception as e:
            logging.error(f"Ошибка при загрузке ключей отправителей из Excel файла: {e}")

if __name__ == "__main__":
    main()
