import asyncio
from playwright.async_api import async_playwright
import telegram
import os
import time

TELEGRAM_BOT_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHANNEL = os.getenv('CHANNEL_ID', '@Click2StealUS')
POST_EVERY_MINUTES = int(os.getenv('POST_EVERY_MINUTES', 180))  # default 3 ore
AFFILIATE_TAG = 'tgig01-20'

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

async def get_vipon_offers():
    offers = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://mymyvipon.com", timeout=60000)
        await page.wait_for_selector('.deal-item', timeout=15000)

        items = await page.query_selector_all('.deal-item')
        for item in items[:5]:
            title = await item.query_selector_eval('.title', 'el => el.textContent.trim()')
            link = await item.query_selector_eval('a', 'el => el.href')
            # Aggiunta tag affiliato Amazon se il link è Amazon
            if 'amazon.com' in link:
                if 'tag=' not in link:
                    if '?' in link:
                        link += f'&tag={AFFILIATE_TAG}'
                    else:
                        link += f'?tag={AFFILIATE_TAG}'
            # Immagine
            img = await item.query_selector_eval('img', 'el => el.src')

            offer_text = (
                f"{title}\n"
                f"Click to open on Amazon ➜ {link}\n"
            )
            offers.append((offer_text, img))

        await browser.close()
    return offers

async def post_offers():
    offers = await get_vipon_offers()
    for offer_text, img_url in offers:
        try:
            # Manda immagine con caption testo
            await bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=img_url, caption=offer_text)
            time.sleep(3)
        except Exception as e:
            print(f"Errore invio: {e}")

async def main_loop():
    while True:
        await post_offers()
        print(f"Posted offers, sleeping for {POST_EVERY_MINUTES} minutes...")
        await asyncio.sleep(POST_EVERY_MINUTES * 60)

if name == 'main':
    asyncio.run(main_loop())
