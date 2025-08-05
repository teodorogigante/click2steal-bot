import subprocess

def install_playwright_browsers():
    print("Installazione browser Playwright in corso...")
    result = subprocess.run(["playwright", "install", "chromium"], capture_output=True, text=True)
    print("Output install:", result.stdout)
    print("Errori install:", result.stderr)

install_playwright_browsers()


import re
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

# === SETUP LOG ===
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

# === FETCH OFFERS (French Offer) ===
async def fetch_offers(page):
    await page.goto("https://www.myvipon.com", timeout=60000)
    await page.wait_for_selector("div.layer", timeout=60000)

    offer_elements = await page.query_selector_all("div.layer")
    urls = []
    for el in offer_elements:
        onclick_attr = await el.get_attribute("onclick")
        if onclick_attr:
            # L'attributo onclick contiene la chiamata getDetail_new('url_path')
            match = re.search(r"getDetail_new\('([^']+)'", onclick_attr)
            if match:
                url_path = match.group(1)
                full_url = "https://www.myvipon.com" + url_path
                urls.append(full_url)
    return urls

async def fetch_offer_detail(page, url):
    await page.goto(url, timeout=60000)
    await page.wait_for_selector("div.product-info", timeout=60000)
    
    title = await page.text_content("p.product-title span")
    price_discounted = await page.text_content("p.product-price > span:nth-child(1)")
    price_original = await page.text_content("p.product-price > s")
    discount_percent = await page.text_content("span.product-percent-discount")
    image_url = await page.get_attribute("div.left-show-img img", "src")
    amazon_link = await page.get_attribute("p.go-to-amazon a", "href")
    
    # Promo code (potrebbe non esserci sempre)
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

# === POST TO TELEGRAM ===
async def post_to_telegram(session, offer):
    if is_already_posted(offer["amazon_link"]):
        logging.info(f"Offerta già pubblicata: {offer['title']}")
        return

    promo_text = f"\nCodice promo: <b>{offer['promo_code']}</b>" if offer['promo_code'] else ""
    message = f"""🛒 <b>{offer['title']}</b>

💲 Prezzo: <s>{offer['price_original']}</s> ➡️ <b>{offer['price_discounted']}</b>{promo_text}
    👉 <a href="{offer['amazon_link']}?tag={AFFILIATE_TAG}">Apri l'offerta su Amazon</a>
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
            save_as_posted(offer["amazon_link"])
            logging.info(f"Inviata: {offer['title']}")
        else:
            error_text = await resp.text()
            logging.error(f"Errore invio Telegram: {error_text}")

# === MAIN LOOP ===
async def main_loop():
    init_db()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    logging.info("Cerco nuove offerte...")
                    offer_urls = await fetch_offers(page)
                    if offer_urls:
                        for url in offer_urls:
                            details = await fetch_offer_detail(page, url)
                            await post_to_telegram(session, details)
                            await asyncio.sleep(2)  # pausa tra i post
                    else:
                        logging.info("Nessuna nuova offerta trovata.")
                except Exception as e:
                    logging.error(f"Errore nel ciclo: {e}")

                logging.info(f"Attendo {POST_INTERVAL} secondi...")
                await asyncio.sleep(POST_INTERVAL)

if name == "main":
    asyncio.run(main_loop())
