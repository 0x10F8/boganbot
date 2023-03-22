import dotenv
import discord
from music_bot import BoganBot
import os

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = BoganBot(command_prefix="!", intents=intents)
bot.run(DISCORD_TOKEN)
