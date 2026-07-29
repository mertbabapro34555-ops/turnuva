import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from database import Database

# Logging Yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

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
        # 1. Veritabanını İlklendir
        await self.db.init_db()
        logging.info("SQLite Veritabanı ilklendirildi.")

        # 2. Cog Modüllerini Yükle
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

        # 3. Slash Komutlarını Discord API ile Senkronize Et
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
    if not TOKEN or TOKEN == "BURAYA_BOT_TOKENINIZI_YAZIN":
        print("❌ HATA: .env dosyasında DISCORD_BOT_TOKEN tanımlı değil!")
        print("Lütfen .env dosyasını açıp Discord Developer Portal'dan aldığınız Bot Token'ınızı yapıştırın.")
        return

    bot = TournamentBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
