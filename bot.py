import subprocess

def install_playwright_browsers():
    print("Installazione browser Playwright in corso...")
    result = subprocess.run(["playwright", "install", "chromium"], capture_output=True, text=True)
    print("Output install:", result.stdout)
    print("Errori install:", result.stderr)

install_playwright_browsers()
import asyncio
import logging
import sqlite3
from playwright.async_api import async_playwright
import aiohttp

# === CONFIG ===
TELEGRAM_BOT_TOKEN = "8040395517:AAGSPs8wndz_Cs5El_fxriX5Du02X5trpEs"
TELEGRAM_CHANNEL = "@Click2StealUS"
AFFILIATE_TAG = "tgig01-20"
POST_INTERVAL = 300  # 5 minuti
OFFERS_PER_POST = 4

# === SETUP ===
logging.basicConfig(level=logging.INFO)

# === DATABASE ===
DB_FILE = "published.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS published (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            affiliate_link TEXT UNIQUE,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_already_posted(affiliate_link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM published WHERE affiliate_link = ?", (affiliate_link,))
    result = c.fetchone()
    conn.close()
    return result is not None

def save_as_posted(affiliate_link):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO published (affiliate_link) VALUES (?)", (affiliate_link,))
        conn.commit()
    except Exception as e:
        logging.warning(f"Errore salvataggio DB: {e}")
    conn.close()

async def fetch_offer_detail(page, url):
    await page.goto(url, timeout=60000)
    await page.wait_for_selector("div.product-info", timeout=60000)
    
    title = await page.text_content("p.product-title span")
    price_discounted = await page.text_content("p.product-price > span:nth-child(1)")
    price_original = await page.text_content("p.product-price > s")
    discount_percent = await page.text_content("span.product-percent-discount")
    image_url = await page.get_attribute("div.left-show-img img", "src")
    amazon_link = await page.get_attribute("p.go-to-amazon a", "href")
    
    # Promo code potrebbe non esserci sempre
    promo_code = None
    try:
        promo_code = await page.text_content("#coupon-container .coupon-code span")
    except Exception:
        promo_code = None
    
    return {
        "title": title.strip() if title else "",
        "price_discounted": price_discounted.strip() if price_discounted else "",
        "price_original": price_original.strip() if price_original else "",
        "discount_percent": discount_percent.strip() if discount_percent else "",
        "image_url": image_url,
        "amazon_link": amazon_link,
        "promo_code": promo_code.strip() if promo_code else None
    }

async def post_to_telegram(session, offer):
    message = f"""🛒 <b>{offer['title']}</b>

💲 Prezzo: <s>{offer['full_price']}</s> ➡️ <b>{offer['discounted_price']}</b>{offer['promo_code_text']}

👉 <a href="{offer['affiliate_link']}">Apri l'offerta su Amazon</a>
"""

    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHANNEL,
        "photo": offer["image_url"],
        "caption": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }


async def post_to_telegram(session, offer):
    message = f"""🛒 <b>{offer['title']}</b>

💲 Prezzo: <s>{offer['full_price']}</s> ➡️ <b>{offer['discounted_price']}</b>{offer['promo_code_text']}

👉 <a href="{offer['affiliate_link']}">Apri l'offerta su Amazon</a>
"""

    telegram_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHANNEL,
        "photo": offer["image_url"],
        "caption": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    async with session.post(telegram_api, data=payload) as resp:
        if resp.status == 200:
            save_as_posted(offer["affiliate_link"])
            logging.info(f"Inviata: {offer['title']}")
        else:
            error_text = await resp.text()
            logging.error(f"Errore invio: {error_text}")

async def main_loop():
    init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    logging.info("Cerco nuove offerte...")
                    offers = await fetch_offers(page)
                    if offers:
                        for offer in offers:
                            await post_to_telegram(session, offer)
                            await asyncio.sleep(2)
                    else:
                        logging.info("Nessuna nuova offerta trovata.")
                except Exception as e:
                    logging.error(f"Errore nel ciclo: {e}")

                logging.info(f"Attendo {POST_INTERVAL} secondi...")
                await asyncio.sleep(POST_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main_loop())
