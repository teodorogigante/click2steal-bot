import time
import requests
import telegram
from bs4 import BeautifulSoup

TELEGRAM_BOT_TOKEN = '8040395517:AAGSPs8wndz_Cs5El_fxriX5Du02X5trpEs'
TELEGRAM_CHANNEL = '@Click2StealUS'
POST_EVERY_MINUTES = 30
OFFERS_PER_POST = 5

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def get_vipon_offers():
    url = "https://www.mymyvipon.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    offers = []
    for item in soup.select(".deal-item")[:OFFERS_PER_POST]:
        title = item.select_one(".title").text.strip()
        link = item.select_one("a")["href"]
        offer_text = f"{title}\n🔗 {link}"
        offers.append(offer_text)

    return offers

def post_to_telegram():
    offers = get_vipon_offers()
    for offer in offers:
        try:
            bot.send_message(chat_id=TELEGRAM_CHANNEL, text=offer)
            time.sleep(3)
        except Exception as e:
            print(f"Errore invio: {e}")

while True:
    post_to_telegram()
    time.sleep(POST_EVERY_MINUTES * 60)
