import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from keep_alive import keep_alive

# Cargar variables desde el archivo .env (ahí guardamos el token)
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ID del canal donde SÍ se pueden usar los comandos del bot.
# Si está vacío, el bot funciona en cualquier canal.
CANAL_COMANDOS_ID = os.getenv("CANAL_COMANDOS_ID")
if CANAL_COMANDOS_ID:
    CANAL_COMANDOS_ID = int(CANAL_COMANDOS_ID)

# Intents: son los "permisos" que le pedimos a Discord para que el bot
# pueda leer mensajes, ver miembros, etc.
intents = discord.Intents.default()
intents.message_content = True  # necesario para que el bot lea el texto de los comandos

# Creamos el bot con prefijo "!"
bot = commands.Bot(command_prefix="!", intents=intents, help_command=commands.DefaultHelpCommand())


@bot.event
async def on_ready():
    print(f"✅ {bot.user} está en línea!")
    print(f"📋 Conectado a {len(bot.guilds)} servidor(es)")
    if CANAL_COMANDOS_ID:
        print(f"🔒 Comandos restringidos al canal ID: {CANAL_COMANDOS_ID}")
    print("-" * 40)


@bot.check
async def solo_en_canal_de_comandos(ctx):
    """Se ejecuta antes de CUALQUIER comando. Si hay un canal configurado
    en CANAL_COMANDOS_ID, solo deja pasar comandos escritos ahí."""
    if not CANAL_COMANDOS_ID:
        return True  # no hay restricción configurada, funciona en todos lados
    return ctx.channel.id == CANAL_COMANDOS_ID


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # El usuario escribió el comando en un canal que no es el permitido
        canal = bot.get_channel(CANAL_COMANDOS_ID)
        if canal:
            await ctx.send(f"🚫 Ese comando solo se puede usar en {canal.mention}", delete_after=8)
        return
    # Cualquier otro error lo mostramos en la consola para poder debuggear
    print(f"⚠️ Error en comando '{ctx.command}': {error}")


# Lista de cogs (módulos) que el bot va a cargar al iniciar
COGS_INICIALES = [
    "cogs.gatos",
    "cogs.interaccion",
    "cogs.mascotas",
    "cogs.economia",
]


async def cargar_cogs():
    for cog in COGS_INICIALES:
        try:
            await bot.load_extension(cog)
            print(f"🔹 Módulo cargado: {cog}")
        except Exception as e:
            print(f"❌ Error cargando {cog}: {e}")


async def main():
    if not TOKEN:
        print("❌ No se encontró el DISCORD_TOKEN. Revisa tu archivo .env")
        return

    keep_alive()  # arranca el mini servidor web que mantiene el bot despierto

    async with bot:
        await cargar_cogs()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
