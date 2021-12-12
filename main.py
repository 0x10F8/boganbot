import dotenv
from music_bot import BoganBot
import os

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv("discord_token")

bot = BoganBot(command_prefix="!")
bot.run(DISCORD_TOKEN)
