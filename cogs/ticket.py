import discord
from discord.ext import commands
from discord import app_commands
import io
import datetime

class TicketControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🔒 Talebi Kapat", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Destek talebi kapatılıyor... Kanal 5 saniye içinde silinecektir.", ephemeral=False)
        await self.bot.db.close_ticket(interaction.channel_id)
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Ticket kapatıldı.")
        except Exception:
            pass

    @discord.ui.button(label="📋 Transcript Al", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript_btn")
    async def generate_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        messages = [message async for message in interaction.channel.history(limit=500, oldest_first=True)]
        
        transcript_text = f"=== TİCKET SOHBET DÖKÜMÜ - {interaction.channel.name} ===\n"
        transcript_text += f"Oluşturulma Tarihi: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for msg in messages:
            transcript_text += f"[{msg.created_at.strftime('%H:%M:%S')}] {msg.author} ({msg.author.id}): {msg.content}\n"
            if msg.attachments:
                for att in msg.attachments:
                    transcript_text += f"  [Ek/Dosya]: {att.url}\n"
                    
        file = discord.File(io.BytesIO(transcript_text.encode("utf-8")), filename=f"{interaction.channel.name}-transcript.txt")
        await interaction.followup.send("📋 Sohbet dökümü hazırlandı:", file=file, ephemeral=True)


class TicketCreateView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="📩 Destek Talebi Oluştur", style=discord.ButtonStyle.primary, custom_id="ticket_create_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Zaten açık bileti var mı kontrol et
        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"❌ Zaten açık bir destek talebiniz bulunuyor: {existing_channel.mention}", ephemeral=True)
            return

        config = await self.bot.db.get_config(guild.id)
        category = None
        if config and config['ticket_category_id']:
            category = guild.get_channel(config['ticket_category_id'])
        
        if not category:
            category = discord.utils.get(guild.categories, name="Ticket oluştur") or discord.utils.get(guild.categories, name="Organizasyon")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites,
            reason=f"{user.display_name} tarafından destek talebi açıldı."
        )

        await self.bot.db.create_ticket(guild.id, user.id, channel.id)

        embed = discord.Embed(
            title="📩 Destek Talebi Oluşturuldu",
            description=f"Merhaba {user.mention},\nYetkililerimiz en kısa sürede sizinle ilgilenecektir.\nLütfen sorununuzu detaylı bir şekilde açıklayın.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Aşağıdaki butonları kullanarak talebi yönetebilirsiniz.")

        await channel.send(content=f"{user.mention} | Yetkili Ekibi", embed=embed, view=TicketControlView(self.bot))
        await interaction.response.send_message(f"✅ Destek talebiniz oluşturuldu: {channel.mention}", ephemeral=True)


class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Persistent UI views
        self.bot.add_view(TicketCreateView(self.bot))
        self.bot.add_view(TicketControlView(self.bot))

    @app_commands.command(name="ticket-kur", description="Belirtilen kanala Destek Talebi (Ticket) buton paneli kurar.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_kur(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        target_channel = kanal or interaction.channel
        
        embed = discord.Embed(
            title="🎫 Destek & Bilet Sistemi",
            description="Turnuva, şikayet veya genel sorularınız için aşağıdaki **Destek Talebi Oluştur** butonuna tıklayarak özel destek kanalı açabilirsiniz.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.add_field(name="⏰ Çalışma Saatleri", value="7/24 Aktif Destek Ekibi", inline=False)
        
        await target_channel.send(embed=embed, view=TicketCreateView(self.bot))
        await interaction.response.send_message(f"✅ Ticket paneli {target_channel.mention} kanalında kuruldu!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
