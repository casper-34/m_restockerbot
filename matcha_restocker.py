import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import asyncio
import json

# === Config ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  
CHAT_ID = os.getenv("CHAT_ID")  
bot = Bot(token=TELEGRAM_TOKEN)         

# === Product List ===
PRODUCTS = [
    {
        "name": "Marukyu's Yugen",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1171020c1",
        "mode": "keyword",
        "keyword": "currently out of stock"
    },
    {
        "name": "Marukyu's Unkaku",
        "url": "https://www.marukyu-koyamaen.co.jp/english/shop/products/1141020c1",
        "mode": "keyword",
        "keyword": "currently out of stock"
    },
    {
    "name": "Ippodo's Ikuyo-no-mukashi 30g",
    "url": "https://global.ippodo-tea.co.jp/collections/all/products/matcha105033",
    "mode": "json_availability",
    },
    {
        "name": "Ippodo's Ummon-no-mukashi 20g",
        "url": "https://global.ippodo-tea.co.jp/collections/matcha/products/matcha101024",
        "mode": "json_availability"
    }
]

# === State Tracking ===
alerted_products = set()

# === Stock Checker ===
def is_in_stock(mode, url, selector=None, keyword=None):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        text = resp.text.lower()

        if mode == "keyword":
            return keyword.lower() not in text
            
        elif mode == "json_availability":
            try:
                soup = BeautifulSoup(resp.text, 'html.parser')
                json_tag = soup.find("script", type="application/ld+json")
                if json_tag:
                    data = json.loads(json_tag.string)
                    availability = data.get("offers", {}).get("availability", "")
                    return "InStock" in availability
                else:
                    print(f"[Warning] JSON tag not found for {url}")
                    return False
            except Exception as e:
                print(f"[Error parsing JSON for {url}]: {e}")
                return False
                
        elif selector:
            elem = BeautifulSoup(text, 'html.parser').select_one(selector)
            return elem and "in stock" in elem.get_text().lower()
        else:
            print(f"[Warning] No valid mode or selector for {url}")
            return False

    except Exception as e:
        print(f"[Error] Failed to check {url}: {e}")
        return False

# === Telegram Notifier ===
async def send_telegram_message(message):
    print(f"[Alert] {message}")
    await bot.send_message(chat_id=CHAT_ID, text=message)

# === Safe Asyncio Wrapper ===
def run_async_safely(coroutine):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(coroutine)


# === Scheduled Job ===
def job():
    print("[Checking products]")

    for product in PRODUCTS:
        name = product["name"]
        url = product["url"]
        mode = product.get("mode", "selector")
        selector = product.get("selector")
        keyword = product.get("keyword")
        identifier = f"{name}|{url}"

        in_stock = is_in_stock(mode, url, selector, keyword)

        if in_stock:
            if identifier not in alerted_products:
                message = f"🔔 {name} is back in stock!\n{url}"
                run_async_safely(send_telegram_message(message))
                alerted_products.add(identifier)
        else:
            if identifier in alerted_products:
                print(f"[Info] {name} went out of stock again.")
                alerted_products.remove(identifier)

job()  # Run once immediately
