import discord
from discord.ext import commands
import aiohttp


class Interaccion(commands.Cog):
    """Comandos de interacción social entre usuarios, con GIFs animados."""

    def __init__(self, bot):
        self.bot = bot

    async def obtener_gif(self, reaccion: str):
        """Pide un gif aleatorio a la API gratuita OtakuGIFs (no necesita API key)."""
        url = f"https://api.otakugifs.xyz/gif?reaction={reaccion}&format=gif"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("url")
            except Exception as e:
                print(f"Error obteniendo gif de '{reaccion}': {e}")
        return None

    @commands.command(name="abrazar")
    async def abrazar(self, ctx, miembro: discord.Member = None):
        """Uso: !abrazar @usuario"""
        if miembro is None:
            await ctx.send("❓ Tieness que mencionar a alguien. Uso: `!abrazar @usuario`")
            return
        if miembro == ctx.author:
            await ctx.send("🫂 Te abrazas a ti mismo... un poco triste, pero válido.")
            return

        gif = await self.obtener_gif("hug")
        embed = discord.Embed(
            description=f"🤗 **{ctx.author.display_name}** abraza a **{miembro.display_name}**",
            color=discord.Color.pink()
        )
        if gif:
            embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.command(name="morder")
    async def morder(self, ctx, miembro: discord.Member = None):
        """Uso: !morder @usuario"""
        if miembro is None:
            await ctx.send("❓ Tienes que mencionar a alguien. Uso: `!morder @usuario`")
            return
        if miembro == ctx.author:
            await ctx.send("😵 ¿Te muerdes a vos mismo? Ok...")
            return

        gif = await self.obtener_gif("bite")
        embed = discord.Embed(
            description=f"😼 **{ctx.author.display_name}** muerde a **{miembro.display_name}**",
            color=discord.Color.red()
        )
        if gif:
            embed.set_image(url=gif)
        await ctx.send(embed=embed)

    @commands.command(name="ronronear")
    async def ronronear(self, ctx):
        """Uso: !ronronear"""
        await ctx.send(f"😻 **{ctx.author.display_name}** ronronea felizmente~ *purrrr* 🐾")


async def setup(bot):
    await bot.add_cog(Interaccion(bot))
