import discord
from discord.ext import commands
from discord import app_commands

class GameRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Valorant 🎯", style=discord.ButtonStyle.primary, custom_id="role_valorant")
    async def toggle_valorant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "Valorant")

    @discord.ui.button(label="League of Legends ⚔️", style=discord.ButtonStyle.primary, custom_id="role_lol")
    async def toggle_lol(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "League of Legends")

    @discord.ui.button(label="FC24 / FIFA ⚽", style=discord.ButtonStyle.primary, custom_id="role_fifa")
    async def toggle_fifa(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "FC24")

    @discord.ui.button(label="Counter-Strike 2 💥", style=discord.ButtonStyle.primary, custom_id="role_cs2")
    async def toggle_cs2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.toggle_role(interaction, "CS2")

    async def toggle_role(self, interaction: discord.Interaction, role_name: str):
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            # Rol yoksa otomatik oluştur
            try:
                role = await guild.create_role(name=role_name, mentionable=True, reason="Oyun Rol Paneli için otomatik oluşturuldu.")
            except Exception as e:
                await interaction.response.send_message(f"❌ Rol oluşturulamadı: {e}", ephemeral=True)
                return

        user = interaction.user
        if role in user.roles:
            await user.remove_roles(role)
            await interaction.response.send_message(f"🔴 **{role.name}** rolü üzerinizden alındı.", ephemeral=True)
        else:
            await user.add_roles(role)
            await interaction.response.send_message(f"🟢 **{role.name}** rolü üzerinize eklendi!", ephemeral=True)


class AutoRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(GameRoleView())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.bot.db.get_config(member.guild.id)
        if config and config['auto_role_id']:
            role = member.guild.get_role(config['auto_role_id'])
            if role:
                try:
                    await member.add_roles(role, reason="Oto-Rol Sistemi")
                except Exception:
                    pass

    @app_commands.command(name="oto-rol-ayarla", description="Sunucuya yeni katılan üyelere verilecek varsayılan rolü belirler.")
    @app_commands.checks.has_permissions(administrator=True)
    async def oto_rol_ayarla(self, interaction: discord.Interaction, rol: discord.Role):
        await self.bot.db.set_config(interaction.guild.id, auto_role_id=rol.id)
        await interaction.response.send_message(f"✅ Yeni katılan üyelere verilecek oto-rol: {rol.mention} olarak ayarlandı.", ephemeral=True)

    @app_commands.command(name="rol-paneli-kur", description="Kullanıcıların kendi oyun rollerini alabileceği butonlu paneli kurar.")
    @app_commands.checks.has_permissions(administrator=True)
    async def rol_paneli_kur(self, interaction: discord.Interaction, kanal: discord.TextChannel = None):
        target_channel = kanal or interaction.channel
        
        embed = discord.Embed(
            title="🎮 Oyun Rolü Seçim Paneli",
            description="Oynadığınız oyunların rolünü alarak turnuvalardan ve etkinliklerden haberdar olmak için aşağıdaki butonlara tıklayın!",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Rolü tekrar almak veya çıkarmak için aynı butona basabilirsiniz.")

        await target_channel.send(embed=embed, view=GameRoleView())
        await interaction.response.send_message(f"✅ Rol paneli {target_channel.mention} kanalında kuruldu!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
