# 🐱 MichiBot

Bot oficial del servidor, temática gatitos, interacción social y entretenimiento.

## 📁 Estructura del proyecto

```
MichiBot/
├── main.py              # Arranca el bot y carga los módulos
├── .env                 # Tu token secreto (lo creás vos, no viene incluido)
├── .env.example          # Plantilla de referencia
├── requirements.txt      # Librerías necesarias
├── data/
│   └── mascotas.json     # Se crea solo, guarda los gatos adoptados
└── cogs/                 # Cada archivo es un "módulo" de comandos
    ├── gatos.py           # !gatito / !michi
    ├── interaccion.py     # !abrazar, !morder, !ronronear
    └── mascotas.py        # !adoptar, !alimentar, !perfil
```

## 🚀 Cómo ponerlo a andar

### 1. Copiá esta carpeta a tu proyecto `BotDiscord`

Reemplazá tu `main.py` actual y agregá la carpeta `cogs/` y los demás archivos.

### 2. Instalá las librerías

En la terminal de VS Code (con el venv activado):

```bash
pip install -r requirements.txt
```

### 3. Configurá tu token

- Copiá `.env.example` y renombralo a `.env`
- Andá a https://discord.com/developers/applications → tu aplicación → **Bot**
- Copiá el token y pegalo en `.env`:

```
DISCORD_TOKEN=tu_token_real_aca
```

⚠️ **Nunca subas el `.env` a GitHub** — el `.gitignore` incluido ya lo excluye.

### 4. Activá los Intents necesarios

En el panel de desarrolladores, en la sección **Bot**, activá:
- ✅ `MESSAGE CONTENT INTENT`

(Sin esto, el bot no puede leer los comandos `!algo`)

### 5. Corré el bot

```bash
python main.py
```

Deberías ver algo como:

```
🔹 Módulo cargado: cogs.gatos
🔹 Módulo cargado: cogs.interaccion
🔹 Módulo cargado: cogs.mascotas
✅ MichiBot está en línea!
```

## 📋 Comandos disponibles

| Comando | Descripción |
|---|---|
| `!gatito` o `!michi` | Envía una foto aleatoria de un gato |
| `!abrazar @usuario` | Abraza a otro miembro con un gif |
| `!morder @usuario` | Muerde a otro miembro con un gif |
| `!ronronear` | Ronronea felizmente |
| `!adoptar NombreDelGato` | Adopta tu gato virtual |
| `!alimentar` | Alimenta a tu gato (sube hambre y felicidad) |
| `!perfil [@usuario]` | Muestra el estado de tu gato (o el de otro usuario) |

## 🌐 APIs usadas (ninguna requiere clave/registro)

- **[TheCatAPI](https://thecatapi.com/)** — fotos aleatorias de gatos
- **[OtakuGIFs](https://otakugifs.xyz/)** — gifs animados de reacciones (hug, bite, etc.)

## 💡 Ideas para seguir mejorando

- Que el hambre baje solo con el tiempo (usando `tasks.loop` de discord.py)
- Agregar más acciones: `!jugar`, `!dormir`, subir de nivel
- Slash commands (`/gatito`) en vez de prefijo `!`
- Guardar los datos en una base de datos real (SQLite) en vez de JSON
