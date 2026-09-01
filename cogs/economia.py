import discord
from discord.ext import commands, tasks
import json
import os
import random
from datetime import datetime, timedelta
from cogs.mascotas import cargar_datos as cargar_mascotas, guardar_datos as guardar_mascotas

RUTA_ECONOMIA = "data/economia.json"
RUTA_TIENDA = "data/tienda.json"
RUTA_LEADERBOARD = "data/leaderboard.json"

# --- Configuración ajustable ---
RECOMPENSA_DAILY_MIN = 100
RECOMPENSA_DAILY_MAX = 300
RECOMPENSA_CHAT_MIN = 1
RECOMPENSA_CHAT_MAX = 5
MENSAJES_MINIMOS_PARA_GANAR = 2      # cada cuántos mensajes (mínimo) se gana moneda
MENSAJES_MAXIMOS_PARA_GANAR = 3      # cada cuántos mensajes (máximo) se gana moneda
RECOMPENSA_ALIMENTAR = 15            # monedas por usar !alimentar
INTERVALO_LEADERBOARD_SEGUNDOS = 15   # cada cuánto se actualiza el Top 10

# Qué le hace cada ítem de mascota a tu gato cuando lo usás.
# Podés agregar más ítems acá (tienen que coincidir con los "id" de tienda.json).
EFECTOS_ITEMS = {
    "juguete_estambre": {"felicidad": 20},
    "collar_oro": {"felicidad": 15, "hambre": 15},
}

APUESTA_MINIMA = 10
APUESTA_MAXIMA = 500   # tope para que nadie se juegue todo de una

# Roles que pueden usar !michiotorgar (dar monedas libremente)
ROLES_STAFF_IDS = [1503188014741065809, 1503939375141097502]
# Canal donde funciona ese comando
CANAL_STAFF_ECONOMIA_ID = 1503484765368746044


# ---------- Funciones auxiliares para leer/escribir JSON ----------

def _cargar_json(ruta, valor_por_defecto):
    if not os.path.exists(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(valor_por_defecto, f)
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)


def cargar_economia():
    return _cargar_json(RUTA_ECONOMIA, {})


def guardar_economia(datos):
    _guardar_json(RUTA_ECONOMIA, datos)


def cargar_tienda():
    return _cargar_json(RUTA_TIENDA, [])


def obtener_usuario(datos, id_usuario):
    """Devuelve (y crea si hace falta) el registro económico de un usuario."""
    if id_usuario not in datos:
        datos[id_usuario] = {
            "monedas": 0,
            "ultimo_daily": None,
            "contador_mensajes": 0,
            "umbral_mensajes": random.randint(MENSAJES_MINIMOS_PARA_GANAR, MENSAJES_MAXIMOS_PARA_GANAR),
            "inventario": []
        }
    return datos[id_usuario]


class Economia(commands.Cog):
    """Sistema de monedas, tienda y leaderboard en vivo."""

    def __init__(self, bot):
        self.bot = bot
        self.canal_economia_id = os.getenv("CANAL_ECONOMIA_ID")
        if self.canal_economia_id:
            self.canal_economia_id = int(self.canal_economia_id)
        self.tarea_leaderboard_iniciada = False

    async def cog_check(self, ctx):
        """Se aplica a TODOS los comandos de este cog (!michidaily, !michisaldo, etc).
        Si hay un canal de economía configurado, solo se pueden usar ahí.
        Excepción: !michiotorgar valida su propio canal y rol más abajo."""
        if ctx.command and ctx.command.name == "michiotorgar":
            return True
        if not self.canal_economia_id:
            return True
        return ctx.channel.id == self.canal_economia_id

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            canal = self.bot.get_channel(self.canal_economia_id) if self.canal_economia_id else None
            if canal:
                await ctx.send(f"🚫 Los comandos de MichiBot economía solo se usan en {canal.mention}", delete_after=8)
            return
        print(f"⚠️ Error en comando de economía '{ctx.command}': {error}")

    # ---------- DAILY ----------

    @commands.command(name="michidaily")
    async def daily(self, ctx):
        """Uso: !michidaily — reclamá tu recompensa diaria."""
        datos = cargar_economia()
        id_usuario = str(ctx.author.id)
        usuario = obtener_usuario(datos, id_usuario)

        ahora = datetime.now()
        if usuario["ultimo_daily"]:
            ultima_vez = datetime.fromisoformat(usuario["ultimo_daily"])
            tiempo_pasado = ahora - ultima_vez
            if tiempo_pasado < timedelta(hours=24):
                falta = timedelta(hours=24) - tiempo_pasado
                horas = int(falta.total_seconds() // 3600)
                minutos = int((falta.total_seconds() % 3600) // 60)
                await ctx.send(
                    f"⏳ Ya reclamaste tu daily hoy. Volvé a intentarlo en "
                    f"**{horas}h {minutos}m**."
                )
                return

        recompensa = random.randint(RECOMPENSA_DAILY_MIN, RECOMPENSA_DAILY_MAX)
        usuario["monedas"] += recompensa
        usuario["ultimo_daily"] = ahora.isoformat()
        guardar_economia(datos)

        embed = discord.Embed(
            title="🎁 ¡Recompensa diaria reclamada!",
            description=f"Ganaste **{recompensa}** 🪙 monedas.",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Saldo total: {usuario['monedas']} 🪙")
        await ctx.send(embed=embed)

    # ---------- SALDO ----------

    @commands.command(name="michisaldo", aliases=["michimonedas"])
    async def saldo(self, ctx, miembro: discord.Member = None):
        """Uso: !michisaldo [@usuario]"""
        miembro = miembro or ctx.author
        datos = cargar_economia()
        usuario = obtener_usuario(datos, str(miembro.id))
        guardar_economia(datos)

        embed = discord.Embed(
            description=f"🪙 **{miembro.display_name}** tiene **{usuario['monedas']}** monedas.",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    # ---------- GANAR MONEDAS CHATEANDO (cada 2-3 mensajes, no por tiempo) ----------

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith("!"):
            return  # los comandos no cuentan como mensaje de chat

        datos = cargar_economia()
        id_usuario = str(message.author.id)
        usuario = obtener_usuario(datos, id_usuario)

        usuario["contador_mensajes"] += 1

        if usuario["contador_mensajes"] >= usuario["umbral_mensajes"]:
            recompensa = random.randint(RECOMPENSA_CHAT_MIN, RECOMPENSA_CHAT_MAX)
            usuario["monedas"] += recompensa
            usuario["contador_mensajes"] = 0
            # el próximo "premio" será dentro de 2 o 3 mensajes de nuevo, al azar
            usuario["umbral_mensajes"] = random.randint(MENSAJES_MINIMOS_PARA_GANAR, MENSAJES_MAXIMOS_PARA_GANAR)

        guardar_economia(datos)

    # ---------- GANAR MONEDAS CUIDANDO LA MASCOTA ----------

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Se dispara cuando cualquier comando termina bien.
        Si fue !alimentar, le sumamos monedas también."""
        if ctx.command and ctx.command.name == "alimentar":
            datos = cargar_economia()
            usuario = obtener_usuario(datos, str(ctx.author.id))
            usuario["monedas"] += RECOMPENSA_ALIMENTAR
            guardar_economia(datos)
            await ctx.send(
                f"🪙 Además ganaste **{RECOMPENSA_ALIMENTAR}** monedas por cuidar a tu gato.",
                delete_after=10
            )

    # ---------- TIENDA ----------

    @commands.command(name="michitienda")
    async def tienda(self, ctx):
        """Uso: !michitienda — mostrá los ítems disponibles."""
        items = cargar_tienda()
        if not items:
            await ctx.send("🛒 La tienda está vacía por ahora.")
            return

        embed = discord.Embed(
            title="🛒 Tienda de MichiBot",
            description="Usá `!michicomprar <id>` para adquirir un ítem.",
            color=discord.Color.green()
        )
        for item in items:
            embed.add_field(
                name=f"{item['nombre']} — {item['precio']} 🪙",
                value=f"ID: `{item['id']}`",
                inline=False
            )
        await ctx.send(embed=embed)

    # ---------- COMPRAR ----------

    @commands.command(name="michicomprar")
    async def comprar(self, ctx, id_item: str = None):
        """Uso: !michicomprar <id_del_item>"""
        if id_item is None:
            await ctx.send("❓ Uso: `!michicomprar <id>` — mirá los IDs con `!michitienda`.")
            return

        items = cargar_tienda()
        item = next((i for i in items if i["id"] == id_item), None)
        if item is None:
            await ctx.send("❌ No existe ese ítem. Revisá `!michitienda` para ver los IDs disponibles.")
            return

        datos = cargar_economia()
        usuario = obtener_usuario(datos, str(ctx.author.id))

        if usuario["monedas"] < item["precio"]:
            faltante = item["precio"] - usuario["monedas"]
            await ctx.send(f"😿 Te faltan **{faltante}** 🪙 monedas para comprar **{item['nombre']}**.")
            return

        # Si es un rol, se lo asignamos directamente
        if item["tipo"] == "rol":
            rol_id = item.get("rol_id")
            rol = ctx.guild.get_role(int(rol_id)) if rol_id else None
            if rol is None:
                await ctx.send(
                    "⚠️ Este rol todavía no está configurado correctamente "
                    "(falta el rol_id en `data/tienda.json`). Avisale a un admin."
                )
                return
            if rol in ctx.author.roles:
                await ctx.send(f"😅 Ya tenés el rol **{rol.name}**.")
                return
            await ctx.author.add_roles(rol)

        # Si es un ítem para la mascota, se agrega al inventario
        elif item["tipo"] == "item_mascota":
            usuario["inventario"].append(item["id"])

        usuario["monedas"] -= item["precio"]
        guardar_economia(datos)

        await ctx.send(f"✅ **{ctx.author.display_name}** compró **{item['nombre']}** por {item['precio']} 🪙.")

    # ---------- USAR ÍTEM EN LA MASCOTA ----------

    @commands.command(name="michiusar")
    async def usar(self, ctx, id_item: str = None):
        """Uso: !michiusar <id_del_item> — gastá un ítem de tu inventario en tu gato."""
        if id_item is None:
            await ctx.send("❓ Uso: `!michiusar <id>` — mirá tu inventario comprando en `!michitienda`.")
            return

        datos = cargar_economia()
        usuario = obtener_usuario(datos, str(ctx.author.id))

        if id_item not in usuario["inventario"]:
            await ctx.send("😿 No tenés ese ítem en tu inventario. Comprálo primero con `!michicomprar`.")
            return

        if id_item not in EFECTOS_ITEMS:
            await ctx.send("⚠️ Ese ítem no tiene un efecto para usar (puede ser solo cosmético).")
            return

        # Buscamos el gato del usuario en los datos de mascotas
        datos_mascotas = cargar_mascotas()
        id_usuario = str(ctx.author.id)
        if id_usuario not in datos_mascotas:
            await ctx.send("😿 Primero necesitás adoptar un gato con `!adoptar NombreDelGato`.")
            return

        gato = datos_mascotas[id_usuario]
        efecto = EFECTOS_ITEMS[id_item]

        subidas = []
        for estadistica, valor in efecto.items():
            gato[estadistica] = min(100, gato.get(estadistica, 0) + valor)
            emoji = "😺" if estadistica == "felicidad" else "🍖"
            subidas.append(f"{emoji} +{valor} {estadistica}")

        guardar_mascotas(datos_mascotas)

        # El ítem se consume: se saca del inventario
        usuario["inventario"].remove(id_item)
        guardar_economia(datos)

        items_tienda = cargar_tienda()
        info_item = next((i for i in items_tienda if i["id"] == id_item), None)
        nombre_item = info_item["nombre"] if info_item else id_item

        embed = discord.Embed(
            description=(
                f"🎉 **{ctx.author.display_name}** usó **{nombre_item}** en **{gato['nombre']}**\n"
                + "\n".join(subidas)
            ),
            color=discord.Color.pink()
        )
        await ctx.send(embed=embed)

    # ---------- TRANSFERIR MONEDAS A OTRO USUARIO ----------

    @commands.command(name="michitransferir", aliases=["michidar"])
    async def transferir(self, ctx, miembro: discord.Member = None, cantidad: int = None):
        """Uso: !michitransferir @usuario <cantidad>"""
        if miembro is None or cantidad is None:
            await ctx.send("❓ Uso: `!michitransferir @usuario <cantidad>`")
            return
        if miembro.bot:
            await ctx.send("😅 No le podés transferir monedas a un bot.")
            return
        if miembro == ctx.author:
            await ctx.send("😅 No te podés transferir monedas a vos mismo.")
            return
        if cantidad <= 0:
            await ctx.send("❌ La cantidad tiene que ser mayor a 0.")
            return

        datos = cargar_economia()
        emisor = obtener_usuario(datos, str(ctx.author.id))
        receptor = obtener_usuario(datos, str(miembro.id))

        if emisor["monedas"] < cantidad:
            await ctx.send(f"😿 No tenés suficientes monedas. Te faltan **{cantidad - emisor['monedas']}** 🪙.")
            return

        emisor["monedas"] -= cantidad
        receptor["monedas"] += cantidad
        guardar_economia(datos)

        embed = discord.Embed(
            description=f"💸 **{ctx.author.display_name}** le transfirió **{cantidad}** 🪙 a **{miembro.display_name}**.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    # ---------- APOSTAR (cara o cruz, con monedas virtuales) ----------

    @commands.command(name="michiapostar", aliases=["michiapuesta"])
    async def apostar(self, ctx, cantidad: int = None, eleccion: str = None):
        """Uso: !michiapostar <cantidad> [cara/cruz] — jugás cara o cruz contra el bot."""
        if cantidad is None:
            await ctx.send(
                f"❓ Uso: `!michiapostar <cantidad> [cara/cruz]` "
                f"— apostá entre **{APUESTA_MINIMA}** y **{APUESTA_MAXIMA}** 🪙."
            )
            return

        if cantidad < APUESTA_MINIMA or cantidad > APUESTA_MAXIMA:
            await ctx.send(f"⚠️ Solo podés apostar entre **{APUESTA_MINIMA}** y **{APUESTA_MAXIMA}** 🪙 por vez.")
            return

        datos = cargar_economia()
        usuario = obtener_usuario(datos, str(ctx.author.id))

        if usuario["monedas"] < cantidad:
            await ctx.send(f"😿 No tenés suficientes monedas. Te faltan **{cantidad - usuario['monedas']}** 🪙.")
            return

        eleccion = (eleccion or "cara").lower()
        if eleccion not in ("cara", "cruz"):
            await ctx.send("❓ Elegí `cara` o `cruz`. Ejemplo: `!michiapostar 50 cara`")
            return

        resultado = random.choice(["cara", "cruz"])
        gano = eleccion == resultado

        if gano:
            usuario["monedas"] += cantidad
            descripcion = (
                f"🪙 La moneda cayó en **{resultado}**.\n"
                f"🎉 ¡Ganaste **{cantidad}** 🪙! Ahora tenés **{usuario['monedas']}** 🪙."
            )
            color = discord.Color.green()
        else:
            usuario["monedas"] -= cantidad
            descripcion = (
                f"🪙 La moneda cayó en **{resultado}**.\n"
                f"😿 Perdiste **{cantidad}** 🪙. Te quedan **{usuario['monedas']}** 🪙."
            )
            color = discord.Color.red()

        guardar_economia(datos)

        embed = discord.Embed(description=descripcion, color=color)
        await ctx.send(embed=embed)

    # ---------- DAR MONEDAS LIBREMENTE (SOLO STAFF) ----------

    @commands.command(name="michiotorgar", aliases=["michigive"])
    async def otorgar(self, ctx, cantidad: str = None, miembro: discord.Member = None):
        """Uso:
        !michiotorgar <cantidad> [@usuario] → SUMA (o resta, si es negativo) esa cantidad
        !michiotorgar =<cantidad> [@usuario] → FIJA el saldo exacto en ese número
        Solo staff. Si no ponés @usuario, te lo aplicás a vos mismo."""

        # Solo funciona en el canal designado para staff
        if ctx.channel.id != CANAL_STAFF_ECONOMIA_ID:
            canal = self.bot.get_channel(CANAL_STAFF_ECONOMIA_ID)
            if canal:
                await ctx.send(f"🚫 Este comando solo se usa en {canal.mention}", delete_after=8)
            return

        # Solo lo pueden usar los roles de staff configurados
        ids_roles_usuario = [rol.id for rol in ctx.author.roles]
        if not any(rid in ids_roles_usuario for rid in ROLES_STAFF_IDS):
            await ctx.send("🚫 Este comando es solo para staff.", delete_after=8)
            return

        if cantidad is None:
            await ctx.send(
                "❓ Uso: `!michiotorgar <cantidad> [@usuario]` (suma/resta)\n"
                "o `!michiotorgar =<cantidad> [@usuario]` (fija el saldo exacto, ej: `=0` para vaciarlo)"
            )
            return

        modo_fijar = cantidad.startswith("=")
        texto_numero = cantidad[1:] if modo_fijar else cantidad

        try:
            valor = int(texto_numero)
        except ValueError:
            await ctx.send("❌ Eso no es un número válido. Ejemplo: `!michiotorgar 100` o `!michiotorgar =0`")
            return

        objetivo = miembro or ctx.author

        datos = cargar_economia()
        usuario = obtener_usuario(datos, str(objetivo.id))

        if modo_fijar:
            usuario["monedas"] = max(0, valor)
            verbo = "le fijó el saldo en"
        else:
            usuario["monedas"] = max(0, usuario["monedas"] + valor)
            verbo = "le otorgó"

        guardar_economia(datos)

        embed = discord.Embed(
            description=(
                f"👑 **{ctx.author.display_name}** {verbo} **{valor}** 🪙 a **{objetivo.display_name}**.\n"
                f"Nuevo saldo: **{usuario['monedas']}** 🪙"
            ),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    # ---------- LEADERBOARD EN VIVO ----------

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.tarea_leaderboard_iniciada and self.canal_economia_id:
            self.actualizar_leaderboard.start()
            self.tarea_leaderboard_iniciada = True

    @tasks.loop(seconds=INTERVALO_LEADERBOARD_SEGUNDOS)
    async def actualizar_leaderboard(self):
        canal = self.bot.get_channel(self.canal_economia_id)
        if canal is None:
            return

        datos = cargar_economia()
        # Ordenamos a los usuarios por monedas, de mayor a menor
        top = sorted(datos.items(), key=lambda x: x[1]["monedas"], reverse=True)[:10]

        embed = discord.Embed(
            title="🏆 Top 10 Millonarios de MichiBot",
            color=discord.Color.gold()
        )

        if not top:
            embed.description = "Todavía nadie tiene monedas. ¡Usá `!michidaily` para empezar!"
        else:
            medallas = ["🥇", "🥈", "🥉"]
            lineas = []
            for i, (id_usuario, info) in enumerate(top):
                posicion = medallas[i] if i < 3 else f"`#{i + 1}`"
                # Usamos una mención real (<@ID>): Discord la muestra con el nombre
                # actualizado y, al tocarla/pasar el mouse, aparece la tarjeta de
                # perfil con sus roles, sin que tengamos que programar nada de eso.
                lineas.append(f"{posicion} <@{id_usuario}> — {info['monedas']} 🪙")
            embed.description = "\n".join(lineas)

        embed.set_footer(text=f"Se actualiza cada {INTERVALO_LEADERBOARD_SEGUNDOS} segundos")
        embed.timestamp = datetime.now()

        # Buscamos si ya existe un mensaje guardado para editar, sino creamos uno nuevo
        guardado = _cargar_json(RUTA_LEADERBOARD, {})
        mensaje = None

        if guardado.get("mensaje_id"):
            try:
                mensaje = await canal.fetch_message(guardado["mensaje_id"])
            except discord.NotFound:
                mensaje = None

        if mensaje:
            await mensaje.edit(embed=embed)
        else:
            nuevo_mensaje = await canal.send(embed=embed)
            try:
                await nuevo_mensaje.pin()
            except discord.HTTPException:
                pass  # si no se puede anclar (ej: ya hay 50 mensajes fijados), no pasa nada grave
            _guardar_json(RUTA_LEADERBOARD, {"mensaje_id": nuevo_mensaje.id})

    @actualizar_leaderboard.before_loop
    async def antes_de_actualizar(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Economia(bot))
