import discord
import aiohttp
from bs4 import BeautifulSoup
import asyncio

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def fetch_forexfactory_news():
    url = "https://www.forexfactory.com/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            # Hier kannst du die spezifischen Nachrichten-Elemente auswählen
            news = soup.find_all('div', class_='flexbox-item-content')
            return [n.text.strip() for n in news]

async def post_news():
    await client.wait_until_ready()
    channel = client.get_channel(1335674970013040794)  # Ersetze YOUR_CHANNEL_ID durch die ID deines Kanals
    
    while not client.is_closed():
        news = await fetch_forexfactory_news()
        for item in news:
            await channel.send(item)
        await asyncio.sleep(3600)  # Warte 1 Stunde, bevor du die nächsten Nachrichten übermittelst

@client.event
async def on_ready():
    print(f'Eingeloggt als {client.user}')
    client.loop.create_task(post_news())

client.run('MTMzNTY5OTI1MzM1NTQ3OTEyMA.GGIbUZ.4zqMXPPmwQWaXf2_ZYTvnksDOu73P6PthcgGCw')  # Ersetze YOUR_BOT_TOKEN durch den Token deines Bots