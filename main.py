import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from database import Database

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TournamentBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.db = Database()

    async def setup_hook(self):
        await self.db.init_db()
        logging.info("SQLite Veritabanı ilklendirildi.")

        initial_extensions = [
            'cogs.temp_voice',
            'cogs.ticket',
            'cogs.guard',
            'cogs.autorole',
            'cogs.tournament'
        ]
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                logging.info(f"Yüklendi: {ext}")
            except Exception as e:
                logging.error(f"Modül yükleme hatası [{ext}]: {e}")

        try:
            synced = await self.tree.sync()
            logging.info(f"Slash komutları senkronize edildi: {len(synced)} komut aktif.")
        except Exception as e:
            logging.error(f"Slash komut senkronizasyon hatası: {e}")

    async def on_ready(self):
        logging.info(f"Bot Başarıyla Giriş Yaptı: {self.user} (ID: {self.user.id})")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="1v1 Turnuvalar & Sunucu Güvenliği | /turnuva-olustur"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")

    if not token or token.strip() == "":
        logging.error("HATA: BOT_TOKEN girilmemiş!")
        return

    logging.info("Token hazır! Discord'a bağlanılıyor...")
    bot = TournamentBot()
    async with bot:
        await bot.start(token.strip())

if __name__ == "__main__":
    asyncio.run(main())
