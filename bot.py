import os
import discord
import asyncio
from datetime import datetime, timedelta
import pytz
import aiohttp
from bs4 import BeautifulSoup

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Discord Bot Token
CHANNEL_FOREX_ID = 1335676311838134355  # Ersetze mit deinem Forex-Kanal
CHANNEL_TRADE_ID = 123456789012345678  # Ersetze mit deinem Trading-Kanal

# Sessions mit Handelszeiten
SESSIONS = [
    {"name": "Trading Session 1", "time": "15:55", "timezone": "Europe/Berlin"},
    {"name": "Trading Session 2", "time": "19:35", "timezone": "Europe/Berlin"},
]

# Forex Factory Nachrichten URL
FOREX_URL = "https://www.forexfactory.com/"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

# Forex News Abfrage
async def fetch_forexfactory_news():
    async with aiohttp.ClientSession() as session:
        async with session.get(FOREX_URL) as response:
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            # Hier kannst du die spezifischen Nachrichten-Elemente auswählen
            news = soup.find_all('div', class_='flexbox-item-content')
            return [n.text.strip() for n in news]

async def send_forex_news():
    await client.wait_until_ready()
    forex_channel = client.get_channel(CHANNEL_FOREX_ID)

    while not client.is_closed():
        news = await fetch_forexfactory_news()
        for item in news:
            await forex_channel.send(item)
        await asyncio.sleep(3600)  # Warte 1 Stunde, bevor du die nächsten Nachrichten übermittelst

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
    client.loop.create_task(send_forex_news())  # Forex-Nachrichten senden
    client.loop.create_task(send_trade_reminders())  # Handels-Erinnerungen senden

client.run(TOKEN)

