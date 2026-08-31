import discord
from discord.ext import commands
import aiohttp


class Gatos(commands.Cog):
    """Comandos relacionados a fotos de gatos."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gatito", aliases=["michi"])
    async def gatito(self, ctx):
        """Envía una foto aleatoria de un gato (usa TheCatAPI, sin necesidad de API key)."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://api.thecatapi.com/v1/images/search") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        url_imagen = data[0]["url"]

                        embed = discord.Embed(
                            title="🐱 ¡Miau!",
                            color=discord.Color.orange()
                        )
                        embed.set_image(url=url_imagen)
                        embed.set_footer(text=f"Pedido por {ctx.author.display_name}")
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("😿 No pude conseguir un gatito ahora mismo, intenta de nuevo.")
            except Exception as e:
                await ctx.send("😿 Ocurrió un error buscando el gatito.")
                print(f"Error en !gatito: {e}")


async def setup(bot):
    await bot.add_cog(Gatos(bot))
