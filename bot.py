import os
import discord
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta
import pytz

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Discord Bot Token
TELEGRAM_URL = [
    "https://t.me/s/ForexFactoryCalendar",  # Erster Kanal
    "https://t.me/s/CRYPTO_insider_deutcher",      # Zweiter Kanal  
]
CHANNEL_FOREX_ID = 1335674970013040794  # Ersetze mit deinem Forex-Channel
CHANNEL_TRADE_ID = 1335676311838134355 # Ersetze mit deinem Trading-Channel

# Sessions mit Handelszeiten
SESSIONS = [
    {"name": "Trading Session 1", "time": "15:55", "timezone": "Europe/Berlin"},
    {"name": "Trading Session 2", "time": "19:35", "timezone": "Europe/Berlin"},
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Liste zur Speicherung der letzten gesendeten Nachrichten-IDs (vermeidet doppelte Posts)
sent_news = []

# Forex News Abfrage
async def fetch_telegram_news():
    news = []
    for url in TELEGRAM_URL:  # Durchläuft jede URL in der Liste
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                messages = soup.find_all('div', class_='tgme_widget_message_text')  # Holt alle Nachrichten
                
                for message in messages[-5:]:  # Nur die letzten 5 Nachrichten holen
                    news.append(message.text.strip())
            
    return news

# Forex News Posten
async def post_news():
    await client.wait_until_ready()
    forex_channel = client.get_channel(CHANNEL_FOREX_ID)

    while not client.is_closed():
        news = await fetch_telegram_news()
        for item in news:
            if item not in sent_news:  # Nur neue Nachrichten posten
                await forex_channel.send(item)
                sent_news.append(item)
                if len(sent_news) > 50:  # Begrenze die Anzahl gespeicherter Nachrichten
                    sent_news.pop(0)  # Entferne die älteste Nachricht, wenn die Liste zu lang wird
        await asyncio.sleep(900)  # Alle 15 Minuten neue Nachrichten abrufen

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

            # Wenn es 10 Minuten vor der Handelszeit ist
            reminder_time = (datetime.combine(datetime.today(), session_time) - timedelta(minutes=10)).time()
            if session_now.hour == reminder_time.hour and session_now.minute == reminder_time.minute:
                await trade_channel.send(f"⏰ **In 10 Minuten beginnt die {session['name']}!** Bereitet euch vor! 📊🚀")
                await asyncio.sleep(60)  # 1 Minute warten, um Dopplungen zu vermeiden

            # Wenn es genau die Handelszeit ist
            if session_now.hour == session_time.hour and session_now.minute == session_time.minute:
                await trade_channel.send(f"⏰ **{session['name']} beginnt jetzt!** Viel Erfolg beim Trading! 📊💰")
                await asyncio.sleep(60)  # 1 Minute warten, um Dopplungen zu vermeiden

        await asyncio.sleep(30)  # Alle 30 Sekunden prüfen

@client.event
async def on_ready():
    print(f"✅ Bot {client.user} ist gestartet!")
    # Starte beide Aufgaben im Hintergrund
    client.loop.create_task(post_news())  # Forex-Nachrichten senden
    client.loop.create_task(send_trade_reminders())  # Handels-Erinnerungen senden

client.run(TOKEN)




