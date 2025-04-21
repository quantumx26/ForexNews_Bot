import os
import discord
import aiohttp
import asyncio
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt
import numpy as np
from pycoingecko import CoinGeckoAPI
from io import BytesIO

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Discord Bot Token

SOURCES = [
    "https://t.me/s/ForexFactoryCalendar",  # Telegram-Kanal
]
RSS_FEEDS = [
    "https://www.coincierge.de/feed/"     # RSS-Feed für Krypto-News
]

CHANNEL_FOREX_ID = 1336353220460806174  # Forex-News-Kanal
CHANNEL_TRADE_ID = 1335676311838134355  # Trading-Kanal
CHANNEL_RSS_ID = 1335674970013040794  # RSS-News-Kanal
CHANNEL_KRYPTO_HEATMAP_ID = 1336644704405553225  # Füge hier die Channel ID für die Krypto-Heatmap hinzu

# Handelszeiten
SESSIONS = [
    {"name": "Trading Session", "time": "09:00", "timezone": "Europe/Berlin"},
]

def get_trading_sessions():
    berlin_tz = pytz.timezone("Europe/Berlin")
    current_time = datetime.now(berlin_tz)
    current_weekday = current_time.weekday()
    
    if current_weekday >= 5:
        return []

    print(f"Aktueller Wochentag: {current_weekday}")  # Debugging-Ausgabe

    filtered_sessions = []
    for session in SESSIONS:
        session_time = datetime.strptime(session["time"], "%H:%M").time()
        session_datetime = berlin_tz.localize(datetime.combine(current_time.date(), session_time))

        if current_time <= session_datetime:
            filtered_sessions.append(session)

    return filtered_sessions


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

sent_news = set()  # Verhindert doppelte Nachrichten
sent_telegram_news = set()  # Verhindert doppelte Telegram-Nachrichten

# CoinGecko API Client
cg = CoinGeckoAPI()

# Telegram-Nachrichten abrufen
async def fetch_telegram_news(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            messages = soup.find_all('div', class_='tgme_widget_message_text')
            return [msg.text.strip() for msg in messages[-1:]]  # Letzte 5 Nachrichten

# RSS-Feed abrufen
async def fetch_rss_news():
    news_items = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:1]:  # Nur die neuesten 5 Artikel holen
            if entry.link not in sent_news:
                sent_news.add(entry.link)
                news_items.append(f"📰 **{entry.title}**\n{entry.link}")
    return news_items

# Krypto-Heatmap generieren und als Bild in den Discord-Kanal senden
async def post_crypto_update():
    await client.wait_until_ready()
    
# 1. Abruf der letzten 20 Krypto-Coins sofort beim Start
    channel = client.get_channel(CHANNEL_KRYPTO_HEATMAP_ID)
    if channel:
        try:
            print("Abrufe der letzten 20 Krypto-Coins beim Neustart...")
            data = cg.get_coins_markets(vs_currency='usd')
            top_coins = sorted(data, key=lambda x: x['market_cap'], reverse=True)[:20]  # Top 20 Coins

            message = "**📊 Krypto Markt-Update (Top 20)**\n\n"
            for coin in top_coins:
                name = coin['name']
                price = f"${coin['current_price']:,.2f}"
                change = coin['price_change_percentage_24h'] or 0
                symbol = "🚀" if change > 0 else "📉"
                
                message += f"**{name}**: {price} | {symbol} {change:.2f}%\n"

            await channel.send(message)
        except Exception as e:
            print(f"Fehler beim Abrufen der Krypto-Daten beim Neustart: {e}")

    while not client.is_closed():
        try:
            data = cg.get_coins_markets(vs_currency='usd')
            top_coins = sorted(data, key=lambda x: x['market_cap'], reverse=True)[:20]  # Top 10 Coins

            message = "**📊 Krypto Markt-Update (Top 20)**\n\n"
            for coin in top_coins:
                name = coin['name']
                price = f"${coin['current_price']:,.2f}"
                change = coin['price_change_percentage_24h'] or 0
                symbol = "🚀" if change > 0 else "📉"
                
                message += f"**{name}**: {price} | {symbol} {change:.2f}%\n"

            if channel:
                await channel.send(message)
        except Exception as e:
            print(f"Fehler beim Abrufen der Krypto-Daten: {e}")

        await asyncio.sleep(26000)  # Alle 5 Stunde aktualisieren

# News abrufen & in die entsprechenden Kanäle posten
async def post_news():
    await client.wait_until_ready()

    forex_channel = client.get_channel(CHANNEL_FOREX_ID)
    rss_channel = client.get_channel(CHANNEL_RSS_ID)

    while not client.is_closed():
        for url in SOURCES:
            if "t.me/s/" in url:
                news = await fetch_telegram_news(url)
                for item in news:
                    if item not in sent_telegram_news:
                        await forex_channel.send(item)
                        sent_telegram_news.add(item)

        rss_news = await fetch_rss_news()
        for item in rss_news:
            if item not in sent_news:
                await rss_channel.send(item)
                sent_news.add(item)
                if len(sent_news) > 20:
                    sent_news.pop()

        await asyncio.sleep(60)  # Alle 1 Minute neue News abrufen

# Handels Session Erinnerungen
async def send_trade_reminders():
    await client.wait_until_ready()
    trade_channel = client.get_channel(CHANNEL_TRADE_ID)

    while not client.is_closed():
        now = datetime.now(pytz.utc)

        sessions = get_trading_sessions()
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
    client.loop.create_task(post_news())  # News abrufen
    client.loop.create_task(send_trade_reminders())  
    client.loop.create_task(post_crypto_update())  # Krypto-Heatmap jede Stunde generieren

client.run(TOKEN)
