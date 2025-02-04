import os
import discord
import aiohttp
import asyncio
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Discord Bot Token

SOURCES = [
    "https://t.me/s/ForexFactoryCalendar",  # Telegram-Kanal
]
RSS_FEEDS = [
    "https://cointelegraph.com/rss"  # RSS-Feed für Krypto-News
]

CHANNEL_FOREX_ID = 1335674970013040794  # Forex-News-Kanal
CHANNEL_TRADE_ID = 1335676311838134355  # Trading-Kanal
CHANNEL_RSS_ID = 1336353220460806174  # Neuer Kanal für RSS-Feeds

# Handelszeiten
SESSIONS = [
    {"name": "Trading Session 1", "time": "15:55", "timezone": "Europe/Berlin"},
    {"name": "Trading Session 2", "time": "19:35", "timezone": "Europe/Berlin"},
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

sent_news = set()  # Verhindert doppelte Nachrichten

# Telegram-Nachrichten abrufen
async def fetch_telegram_news(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            messages = soup.find_all('div', class_='tgme_widget_message_text')
            return [msg.text.strip() for msg in messages[-5:]]  # Letzte 5 Nachrichten

# RSS-Feed abrufen
async def fetch_rss_news():
    news_items = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:  # Nur die neuesten 5 Artikel holen
            if entry.link not in sent_news:
                sent_news.add(entry.link)
                news_items.append(f"📰 **{entry.title}**\n{entry.link}")
    return news_items

# News abrufen & in die entsprechenden Kanäle posten
async def post_news():
    await client.wait_until_ready()
    
    forex_channel = client.get_channel(CHANNEL_FOREX_ID)  # Kanal für Forex-Nachrichten
    rss_channel = client.get_channel(CHANNEL_RSS_ID)  # Kanal für RSS-News

    while not client.is_closed():
        all_news = []

        # Telegram & Webseiten abrufen
        for url in SOURCES:
            if "t.me/s/" in url:  # Telegram-URL erkennen
                news = await fetch_telegram_news(url)
            else:  # Normale Webseite
                news = await fetch_website_news(url)
            all_news.extend(news)

        # RSS-News abrufen
        rss_news = await fetch_rss_news()
        all_news.extend(rss_news)

        # Forex-News in Forex-Kanal senden
        for item in all_news:
            if item not in sent_news:
                await forex_channel.send(item)
                sent_news.add(item)
                if len(sent_news) > 50:
                    sent_news.pop()  # Älteste Nachricht entfernen

        # RSS-News in RSS-Kanal senden
        rss_news = await fetch_rss_news()
        for item in rss_news:
            if item not in sent_news:
                await rss_channel.send(item)
                sent_news.add(item)
                if len(sent_news) > 50:
                    sent_news.pop()  # Älteste Nachricht entfernen

        await asyncio.sleep(900)  # Alle 15 Minuten neue News abrufen

# Handels Session Erinnerungen
async def send_trade_reminders():
    await client.wait_until_ready()
    trade_channel = client.get_channel(CHANNEL_TRADE_ID)

    while not client.is_closed():
        now = datetime.now(pytz.utc)

        for session in SESSIONS:
            session_time = datetime.strptime(session["time"], "%H:%M").time()
            session_tz = pytz.timezone(session["timezone"])
            session_now = now.astimezone(session_tz).time()

            reminder_time = (datetime.combine(datetime.today(), session_time) - timedelta(minutes=10)).time()
            if session_now.hour == reminder_time.hour and session_now.minute == reminder_time.minute:
                await trade_channel.send(f"⏰ **In 10 Minuten beginnt die {session['name']}!** 📊🚀")
                await asyncio.sleep(60)

            if session_now.hour == session_time.hour and session_now.minute == session_time.minute:
                await trade_channel.send(f"⏰ **{session['name']} beginnt jetzt!** 📊💰")
                await asyncio.sleep(60)

        await asyncio.sleep(30)  # Alle 30 Sekunden prüfen

@client.event
async def on_ready():
    print(f"✅ Bot {client.user} ist gestartet!")
    client.loop.create_task(post_news())  
    client.loop.create_task(send_trade_reminders())  

client.run(TOKEN)




