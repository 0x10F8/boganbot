import dotenv
from music_bot import BoganBot
import os

dotenv.load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = BoganBot(command_prefix="!")
bot.run(DISCORD_TOKEN)
