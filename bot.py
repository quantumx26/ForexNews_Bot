import os
import discord
import aiohttp
from bs4 import BeautifulSoup
import asyncio

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Discord Bot Token
TELEGRAM_URL = "https://t.me/s/fxassistcalendar"  # Öffentliche Telegram-Webseite

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def fetch_telegram_news():
    async with aiohttp.ClientSession() as session:
        async with session.get(TELEGRAM_URL) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            messages = soup.find_all('div', class_='tgme_widget_message_text')  # Holt alle Nachrichten
            
            news = []
            for message in messages[-5:]:  # Nur die letzten 5 Nachrichten holen
                news.append(message.text.strip())
            
            return news

async def post_news():
    await client.wait_until_ready()
    channel = client.get_channel(1335674970013040794)  # Ersetze mit deiner Discord-Channel-ID
    
    last_news = set()  # Um doppelte Nachrichten zu vermeiden
    
    while not client.is_closed():
        news = await fetch_telegram_news()
        for item in news:
            if item not in last_news:  # Nur neue Nachrichten posten
                await channel.send(item)
                last_news.add(item)
        await asyncio.sleep(900)  # Alle 30 Minuten neue Nachrichten abrufen

@client.event
async def on_ready():
    print(f'Eingeloggt als {client.user}')
    client.loop.create_task(post_news())

client.run(TOKEN)

