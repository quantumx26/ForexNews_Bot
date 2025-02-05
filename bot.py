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
    "https://www.btc-echo.de/feed/",
    "https://www.coincierge.de/feed/"     # RSS-Feed für Krypto-News
]

CHANNEL_FOREX_ID = 1336353220460806174  # Forex-News-Kanal
CHANNEL_TRADE_ID = 1335676311838134355  # Trading-Kanal
CHANNEL_RSS_ID = 1335674970013040794  # RSS-News-Kanal
CHANNEL_KRYPTO_HEATMAP_ID = 1336644704405553225  # Füge hier die Channel ID für die Krypto-Heatmap hinzu

# Handelszeiten
SESSIONS = [
    {"name": "Trading Session 1", "time": "15:55", "timezone": "Europe/Berlin"},
    {"name": "Trading Session 2", "time": "19:35", "timezone": "Europe/Berlin"},
]

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
        for entry in feed.entries[:5]:  # Nur die neuesten 5 Artikel holen
            if entry.link not in sent_news:
                sent_news.add(entry.link)
                news_items.append(f"📰 **{entry.title}**\n{entry.link}")
    return news_items

# Krypto-Heatmap generieren und als Bild in den Discord-Kanal senden
async def generate_crypto_heatmap():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_KRYPTO_HEATMAP_ID)
    
    while not client.is_closed():
        try:
            data = cg.get_coins_markets(vs_currency='usd')
            coins = sorted(data, key=lambda x: x['market_cap'], reverse=True)[:20]  # Top 20 Coins nach Marktkapitalisierung

            names = [coin['name'] for coin in coins]
            prices = [coin['current_price'] for coin in coins]
            percentages = [coin['price_change_percentage_24h'] for coin in coins]

            fig, ax = plt.subplots(figsize=(10, 6))
            scatter = ax.scatter(names, prices, c=percentages, cmap='coolwarm', s=100)
            ax.set_xlabel('Kryptowährungen')
            ax.set_ylabel('Preis in USD')
            ax.set_title('Krypto-Heatmap: Top 20 Coins')
            plt.xticks(rotation=45, ha='right')

            cbar = plt.colorbar(scatter)
            cbar.set_label('24h Preisänderung (%)')

            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)

            if channel:
                await channel.send(file=discord.File(buf, filename='crypto_heatmap.png'))
            buf.close()

        except Exception as e:
            print(f"Fehler beim Generieren der Heatmap: {e}")
        
        await asyncio.sleep(3600)  # Alle 1 Stunde aktualisieren

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
                if len(sent_news) > 50:
                    sent_news.pop()

        await asyncio.sleep(60)  # Alle 1 Minute neue News abrufen

@client.event
async def on_ready():
    print(f"✅ Bot {client.user} ist gestartet!")
    client.loop.create_task(post_news())  # News abrufen
    client.loop.create_task(generate_crypto_heatmap())  # Krypto-Heatmap jede Stunde generieren

client.run(TOKEN)
