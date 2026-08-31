import discord
from discord.ext import commands
import json
import os
from datetime import datetime

RUTA_DATOS = "data/mascotas.json"

# Cuánto baja el hambre por cada hora que pasa sin comer
HAMBRE_POR_HORA = 3


def cargar_datos():
    """Lee el archivo JSON donde se guardan todos los gatos adoptados.
    Si no existe, lo crea vacío."""
    if not os.path.exists(RUTA_DATOS):
        os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
        with open(RUTA_DATOS, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(RUTA_DATOS, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_datos(datos):
    """Escribe los datos actualizados de vuelta al archivo JSON."""
    with open(RUTA_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def crear_barra(valor, maximo=100, longitud=10):
    """Genera una barra visual tipo ████░░░░░░ con emojis."""
    llenos = int((valor / maximo) * longitud)
    return "🟩" * llenos + "⬜" * (longitud - llenos)


def actualizar_hambre(gato):
    """Calcula cuánto bajó el hambre desde la última vez que se revisó,
    según las horas que pasaron. Modifica el diccionario 'gato' en el lugar
    y devuelve True si el hambre cambió (para saber si hay que guardar)."""
    ahora = datetime.now()
    ultima = datetime.fromisoformat(gato.get("ultima_actualizacion", ahora.isoformat()))

    horas_pasadas = (ahora - ultima).total_seconds() / 3600
    if horas_pasadas <= 0:
        return False

    baja = int(horas_pasadas * HAMBRE_POR_HORA)
    if baja <= 0:
        return False

    gato["hambre"] = max(0, gato["hambre"] - baja)
    gato["ultima_actualizacion"] = ahora.isoformat()
    return True


class Mascotas(commands.Cog):
    """Mini-juego de gatos virtuales: adoptar, alimentar y ver el perfil."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="adoptar")
    async def adoptar(self, ctx, *, nombre: str = None):
        """Uso: !adoptar NombreDelGato"""
        if nombre is None:
            await ctx.send("❓ Tenés que darle un nombre a tu gato. Uso: `!adoptar NombreDelGato`")
            return

        datos = cargar_datos()
        id_usuario = str(ctx.author.id)

        if id_usuario in datos:
            nombre_actual = datos[id_usuario]["nombre"]
            await ctx.send(f"😾 Ya tenés un gato llamado **{nombre_actual}**. ¡No podés adoptar otro (todavía)!")
            return

        datos[id_usuario] = {
            "nombre": nombre,
            "hambre": 50,
            "felicidad": 50,
            "adoptado": datetime.now().strftime("%Y-%m-%d"),
            "ultima_actualizacion": datetime.now().isoformat()
        }
        guardar_datos(datos)

        embed = discord.Embed(
            title="🎉 ¡Adopción exitosa!",
            description=f"**{ctx.author.display_name}** adoptó a **{nombre}** 🐱",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(name="alimentar")
    async def alimentar(self, ctx):
        """Uso: !alimentar"""
        datos = cargar_datos()
        id_usuario = str(ctx.author.id)

        if id_usuario not in datos:
            await ctx.send("😿 No tenés un gato todavía. Usá `!adoptar NombreDelGato` primero.")
            return

        gato = datos[id_usuario]
        actualizar_hambre(gato)  # primero descontamos lo que bajó con el tiempo

        gato["hambre"] = min(100, gato["hambre"] + 20)
        gato["felicidad"] = min(100, gato["felicidad"] + 5)
        gato["ultima_actualizacion"] = datetime.now().isoformat()
        guardar_datos(datos)

        await ctx.send(f"🍗 Alimentaste a **{gato['nombre']}**. ¡Ahora está más contento! 😸")

    @commands.command(name="perfil")
    async def perfil(self, ctx, miembro: discord.Member = None):
        """Uso: !perfil [@usuario opcional]"""
        miembro = miembro or ctx.author
        datos = cargar_datos()
        id_usuario = str(miembro.id)

        if id_usuario not in datos:
            if miembro == ctx.author:
                await ctx.send("😿 Todavía no tenés un gato. Usá `!adoptar NombreDelGato`.")
            else:
                await ctx.send(f"😿 **{miembro.display_name}** todavía no tiene un gato.")
            return

        gato = datos[id_usuario]
        if actualizar_hambre(gato):
            guardar_datos(datos)  # solo guardamos si realmente cambió algo

        aviso_hambre = ""
        if gato["hambre"] <= 20:
            aviso_hambre = "\n⚠️ ¡Tiene mucha hambre, dale de comer con `!alimentar`!"

        embed = discord.Embed(
            title=f"🐱 Perfil de {gato['nombre']}",
            description=f"Dueño/a: {miembro.display_name}",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="🍖 Hambre",
            value=f"{crear_barra(gato['hambre'])}  {gato['hambre']}/100",
            inline=False
        )
        embed.add_field(
            name="😺 Felicidad",
            value=f"{crear_barra(gato['felicidad'])}  {gato['felicidad']}/100",
            inline=False
        )
        embed.set_footer(text=f"Adoptado el {gato['adoptado']}")
        if aviso_hambre:
            embed.description += aviso_hambre
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Mascotas(bot))
