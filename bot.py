#!/usr/bin/env python3
import logging
import os
import requests
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

from metro import fetch_parada, formato_parada

load_dotenv()  # carga el .env antes de os.environ[...]
requests.packages.urllib3.disable_warnings()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]  # ej: https://tu-app.onrender.com

# comando → nombre exacto en la web
COMANDOS = {
    "albolote":       "Albolote",
    "juncaril":       "Juncaril",
    "vicuna":         "Vicuña",
    "anfiteatro":     "Anfiteatro",
    "maracena":       "Maracena",
    "cerrillo":       "Cerrillo de Maracena",
    "jaen":           "Jaén",
    "autobuses":      "Estación de autobuses",
    "argentinita":    "Argentinita",
    "luisamador":     "Luís Amador",
    "villarejo":      "Villarejo",
    "caleta":         "Caleta",
    "ferrocarril":    "Estación de ferrocarril",
    "universidad":    "Universidad",
    "mendez":         "Méndez Núñez",
    "recogidas":      "Recogidas",
    "alcazar":        "Alcázar Genil",
    "hipica":         "Hípica",
    "andressegovia":  "Andrés Segovia",
    "palacio":        "Palacio de deportes",
    "carmenes":       "Nuevo Los Cármenes",
    "dilar":          "Dílar",
    "parque":         "Parque tecnológico",
    "sierranevada":   "Sierra Nevada",
    "fernando":       "Fernando de los Ríos",
    "armilla":        "Armilla",
}


async def cmd_parada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comando = update.message.text.split()[0][1:].split("@")[0].lower()
    nombre = COMANDOS.get(comando)
    if not nombre:
        await update.message.reply_text("Comando desconocido.")
        return
    try:
        t = fetch_parada(nombre)
        await update.message.reply_text(formato_parada(nombre, t))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lista = "\n".join(f"/{cmd} — {nombre}" for cmd, nombre in COMANDOS.items())
    await update.message.reply_text(f"Paradas disponibles:\n\n{lista}")


async def post_init(app):
    comandos_bot = [BotCommand(cmd, nombre) for cmd, nombre in COMANDOS.items()]
    comandos_bot.insert(0, BotCommand("start", "Ver todas las paradas"))
    await app.bot.set_my_commands(comandos_bot)


if __name__ == "__main__":
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    for cmd in COMANDOS:
        app.add_handler(CommandHandler(cmd, cmd_parada))

    print("Bot arrancado con webhook.")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        webhook_url=f"{WEBHOOK_URL}/webhook",
        url_path="/webhook",
    )