import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ═══════════════════════════════════════════════
#  CONFIGURACIÓN
# ═══════════════════════════════════════════════
BOT_TOKEN    = os.environ.get("BOT_TOKEN")
ADMIN_ID     = 8315702370
SUPPORT_USER = "@ACPremiumSupport"

CHANNEL_LINKS = {
    "mensual":    "https://t.me/+LINK_MENSUAL",
    "trimestral": "https://t.me/+LINK_TRIMESTRAL",
    "semestral":  "https://t.me/+LINK_SEMESTRAL",
    "anual":      "https://t.me/+LINK_ANUAL",
}

# Direcciones de pago — edita con las tuyas
CRYPTO_ADDRESSES = {
    "BTC":        "12Sjcp9nP3QTeoApVsaXBfVmcXoWVQbTXv",
    "ETH":        "0x5728e223dbd22c8577e4eeae7b3f79ec901c9a49",
    "USDT ERC20": "0x5728e223dbd22c8577e4eeae7b3f79ec901c9a49",
    "USDT TRC20": "TRuY9nS7Q3xVUB7DaGHBwzchwsEt2eSrtY",
}
WISE_INFO = "Account Name: Andrés Cestona\nIBAN: BE17 9056 8810 0021\nSWIFT/BIC: TRWIBEB1XXX"

PLANES = {
    "mensual":    {"precio": 149,  "nombre": "1 Month Subscription",  "dias": 30,  "periodo": "1 mes"},
    "trimestral": {"precio": 349,  "nombre": "3 Month Subscription",  "dias": 90,  "periodo": "3 meses"},
    "semestral":  {"precio": 549,  "nombre": "6 Month Subscription",  "dias": 180, "periodo": "6 meses"},
    "anual":      {"precio": 999,  "nombre": "1 Year Subscription",   "dias": 365, "periodo": "1 año"},
}

CUPONES = {
    "NEW20": 20,
}

# ═══════════════════════════════════════════════
#  BASE DE DATOS
# ═══════════════════════════════════════════════
DB_FILE = "suscripciones.json"

def cargar_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def guardar_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_suscripcion(user_id):
    db = cargar_db()
    return db.get(str(user_id))

def guardar_suscripcion(user_id, plan, dias):
    db = cargar_db()
    inicio = datetime.now()
    fin = inicio + timedelta(days=dias)
    db[str(user_id)] = {
        "plan": plan,
        "inicio": inicio.isoformat(),
        "fin": fin.isoformat(),
    }
    guardar_db(db)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

pendientes = {}

MENU_TECLADO = ReplyKeyboardMarkup(
    [[KeyboardButton("Planes y precios"), KeyboardButton("Mi suscripción")],
     [KeyboardButton("Soporte"),          KeyboardButton("Inicio")]],
    resize_keyboard=True
)

def precio_con_descuento(precio, cupon):
    pct = CUPONES.get(cupon.upper(), 0)
    return int(precio * (1 - pct / 100)), pct

def estado_suscripcion_texto(user_id):
    sub = get_suscripcion(user_id)
    if not sub:
        return "No tienes ninguna suscripción activa en este momento."
    fin = datetime.fromisoformat(sub["fin"])
    ahora = datetime.now()
    if ahora > fin:
        return "Tu suscripción ha expirado.\n\nPuedes renovarla seleccionando un plan a continuación."
    restante = fin - ahora
    dias = restante.days
    horas = restante.seconds // 3600
    plan = PLANES[sub["plan"]]["nombre"]
    fin_str = fin.strftime("%d/%m/%Y, %H:%M")
    return (
        f"Plan: *{plan}*\n"
        f"Tu membresía es válida hasta: {fin_str}\n"
        f"(*{dias} días y {horas} horas* restantes)"
    )


# ── /start ────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    texto = (
        f"Hola, {nombre}.\n\n"
        "Bienvenido al bot de suscripciones de *AC Premium Signals*.\n\n"
        "Ofrecemos señales diarias de criptomonedas de alta precisión, "
        "con análisis técnico en tiempo real para BTC y los principales activos del mercado.\n\n"
        "Al suscribirte obtendrás acceso a:\n"
        "· Canal de señales diarias de BTC\n"
        "· Canal AC Swing Signals\n"
        "· Alertas de entrada y salida\n"
        "· Soporte directo con el equipo\n\n"
        "Si eres nuevo, puedes usar el código *NEW20* para obtener un 20% de descuento en cualquier plan.\n\n"
        f"Para cualquier consulta escríbenos a {SUPPORT_USER}.\n\n"
        "Selecciona una opción:"
    )
    teclado_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("Planes y precios", callback_data="ver_precios")],
        [InlineKeyboardButton("Mi suscripción",   callback_data="mi_suscripcion")],
        [InlineKeyboardButton("Soporte",          callback_data="soporte")],
    ])
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=MENU_TECLADO)
    await update.message.reply_text("¿Qué deseas hacer?", reply_markup=teclado_inline)


# ── Precios ───────────────────────────────────
def _precios_contenido():
    texto = "*AC Premium Signals — Planes de suscripción*\n\nSelecciona un plan para continuar:"
    botones = []
    for key, p in PLANES.items():
        botones.append([InlineKeyboardButton(
            f"{p['nombre']}: ${p['precio']}.00 / {p['periodo']}",
            callback_data=f"contratar_{key}"
        )])
    return texto, InlineKeyboardMarkup(botones)

async def ver_precios_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto, teclado = _precios_contenido()
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)

async def ver_precios_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    texto, teclado = _precios_contenido()
    await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=teclado)


# ── Mi suscripción ────────────────────────────
async def mi_suscripcion_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto = estado_suscripcion_texto(update.effective_user.id)
    botones = InlineKeyboardMarkup([[InlineKeyboardButton("Ver planes", callback_data="ver_precios")]])
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)

async def mi_suscripcion_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    texto = estado_suscripcion_texto(query.from_user.id)
    botones = InlineKeyboardMarkup([[InlineKeyboardButton("Ver planes", callback_data="ver_precios")]])
    await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)


# ── Soporte ───────────────────────────────────
async def soporte_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Para cualquier consulta escríbenos directamente a *{SUPPORT_USER}*.\n\nEstamos disponibles.",
        parse_mode="Markdown"
    )

async def soporte_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        f"Para cualquier consulta escríbenos directamente a *{SUPPORT_USER}*.\n\nEstamos disponibles.",
        parse_mode="Markdown"
    )


# ── Contratar ─────────────────────────────────
async def contratar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.replace("contratar_", "")
    user_id = query.from_user.id
    pendientes[user_id] = {"plan": plan, "cupon": None}
    p = PLANES[plan]
    texto = (
        f"*{p['nombre']}*\n"
        f"${p['precio']}.00 por {p['periodo']}\n\n"
        "Al completar este pedido obtendrás acceso a:\n"
        "· Canal AC Premium Signals (señales diarias de BTC)\n"
        "· Canal AC Swing Signals\n"
        "· Alertas de entrada y salida\n"
        "· Soporte directo con el equipo\n\n"
        "¿Dispones de un código de descuento?"
    )
    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("Sí, tengo un código", callback_data=f"tiene_cupon_{plan}"),
         InlineKeyboardButton("No",                  callback_data=f"elegir_pago_{plan}_nocupon")],
        [InlineKeyboardButton("Volver a los planes", callback_data="ver_precios")],
    ])
    await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)

async def tiene_cupon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.replace("tiene_cupon_", "")
    pendientes[query.from_user.id] = {"plan": plan, "cupon": None}
    await query.message.reply_text("Escribe tu código de descuento:")


# ── Elegir método de pago ─────────────────────
async def elegir_pago(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.replace("elegir_pago_", "").split("_")
    plan  = partes[0]
    cupon = partes[1] if len(partes) > 1 and partes[1] != "nocupon" else None
    user_id = query.from_user.id
    pendientes[user_id] = {"plan": plan, "cupon": cupon}

    p = PLANES[plan]
    precio_final = p["precio"]
    linea_cupon = ""
    if cupon and cupon in CUPONES:
        precio_final, pct = precio_con_descuento(p["precio"], cupon)
        linea_cupon = f"Código {cupon} aplicado: -{pct}%\n"

    texto = (
        f"*Resumen del pedido*\n\n"
        f"Plan: {p['nombre']}\n"
        f"{linea_cupon}"
        f"Total: *${precio_final}.00*\n\n"
        "Selecciona el método de pago:"
    )
    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("Wise",       callback_data=f"metodo_wise_{plan}_{precio_final}")],
        [InlineKeyboardButton("BTC",        callback_data=f"metodo_BTC_{plan}_{precio_final}"),
         InlineKeyboardButton("ETH",        callback_data=f"metodo_ETH_{plan}_{precio_final}")],
        [InlineKeyboardButton("USDT ERC20", callback_data=f"metodo_USDTERC20_{plan}_{precio_final}"),
         InlineKeyboardButton("USDT TRC20", callback_data=f"metodo_USDTTRC20_{plan}_{precio_final}")],
        [InlineKeyboardButton("Volver a los planes", callback_data="ver_precios")],
    ])
    await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)


# ── Mostrar dirección de pago ─────────────────
async def mostrar_metodo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.replace("metodo_", "").split("_")
    metodo     = partes[0]
    plan       = partes[1]
    precio_str = partes[2]
    user_id    = query.from_user.id
    p = PLANES[plan]

    if metodo == "wise":
        texto = (
            f"*Pago con Wise*\n\n"
            f"{WISE_INFO}\n\n"
            f"Importe: *${precio_str}.00*\n\n"
            f"Una vez realizado el pago, envía el comprobante a {SUPPORT_USER}.\n"
            "Tu acceso será activado en menos de 24 horas."
        )
    else:
        nombre_metodo = metodo.replace("USDTERC20", "USDT ERC20").replace("USDTTRC20", "USDT TRC20")
        direccion = CRYPTO_ADDRESSES.get(nombre_metodo, "Consulta con soporte")
        texto = (
            f"*Pago con {nombre_metodo}*\n\n"
            f"Dirección de envío:\n`{direccion}`\n\n"
            f"Importe: *${precio_str}.00*\n\n"
            f"Una vez realizado el pago, envía el hash de la transacción a {SUPPORT_USER}.\n"
            "Tu acceso será activado en menos de 24 horas."
        )

    await query.message.reply_text(texto, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Contactar soporte",   callback_data="soporte")],
            [InlineKeyboardButton("Volver a los planes", callback_data="ver_precios")],
        ]))

    await ctx.bot.send_message(
        ADMIN_ID,
        f"Nuevo interesado en pagar\n\n"
        f"Usuario: [{query.from_user.first_name}](tg://user?id={user_id}) — ID: `{user_id}`\n"
        f"Plan: {p['nombre']} — ${precio_str}.00\n"
        f"Método: {metodo}\n\n"
        f"Para aprobar: `/aprobar {user_id}`",
        parse_mode="Markdown"
    )


# ── Texto libre ───────────────────────────────
async def mensaje_texto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    texto = update.message.text.strip()

    if texto == "Planes y precios":
        return await ver_precios_msg(update, ctx)
    if texto == "Mi suscripción":
        return await mi_suscripcion_msg(update, ctx)
    if texto == "Soporte":
        return await soporte_msg(update, ctx)
    if texto == "Inicio":
        return await start(update, ctx)

    if user_id in pendientes and pendientes[user_id].get("cupon") is None:
        plan = pendientes[user_id]["plan"]
        cupon = texto.upper()
        if cupon in CUPONES:
            pendientes[user_id]["cupon"] = cupon
            precio_orig = PLANES[plan]["precio"]
            precio_final, pct = precio_con_descuento(precio_orig, cupon)
            await update.message.reply_text(
                f"Código *{cupon}* aplicado correctamente. -{pct}% de descuento.\n\n"
                f"Precio final: *${precio_final}.00*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Seleccionar método de pago", callback_data=f"elegir_pago_{plan}_{cupon}")]
                ])
            )
        else:
            await update.message.reply_text(
                "El código introducido no es válido. Inténtalo de nuevo o continúa sin código.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Continuar sin código", callback_data=f"elegir_pago_{plan}_nocupon")]
                ])
            )


# ── /aprobar ──────────────────────────────────
async def aprobar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Sin permisos.")
        return
    if not ctx.args:
        await update.message.reply_text("Uso: `/aprobar USER_ID`", parse_mode="Markdown")
        return
    user_id = int(ctx.args[0])
    plan = ctx.args[1] if len(ctx.args) > 1 else pendientes.get(user_id, {}).get("plan", "mensual")
    dias = PLANES[plan]["dias"]
    link = CHANNEL_LINKS[plan]
    guardar_suscripcion(user_id, plan, dias)
    fin = (datetime.now() + timedelta(days=dias)).strftime("%d/%m/%Y")
    await ctx.bot.send_message(
        user_id,
        f"Hola,\n\n"
        f"Tu pago ha sido confirmado. Bienvenido a *AC Premium Signals*.\n\n"
        f"Plan contratado: *{PLANES[plan]['nombre']}*\n"
        f"Tu acceso vence el: *{fin}*\n\n"
        f"Enlace de acceso al canal:\n{link}\n\n"
        f"Este enlace es personal. Por favor, no lo compartas.\n\n"
        f"Para cualquier consulta escríbenos a {SUPPORT_USER}.",
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        f"Acceso activado para `{user_id}` — {plan} hasta {fin}.",
        parse_mode="Markdown"
    )
    pendientes.pop(user_id, None)


# ── /pendientes ───────────────────────────────
async def ver_pendientes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not pendientes:
        await update.message.reply_text("No hay usuarios pendientes.")
        return
    texto = "*Pendientes de aprobación:*\n\n"
    for uid, datos in pendientes.items():
        texto += f"· `{uid}` — {datos['plan']}\n"
    await update.message.reply_text(texto, parse_mode="Markdown")


# ── /suscripciones ────────────────────────────
async def ver_suscripciones(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = cargar_db()
    if not db:
        await update.message.reply_text("No hay suscripciones registradas.")
        return
    ahora = datetime.now()
    texto = "*Suscripciones:*\n\n"
    for uid, sub in db.items():
        fin = datetime.fromisoformat(sub["fin"])
        estado = "Activa" if fin > ahora else "Expirada"
        dias_rest = max((fin - ahora).days, 0)
        texto += f"· `{uid}` — {sub['plan']} — {estado} — {dias_rest}d\n"
    await update.message.reply_text(texto, parse_mode="Markdown")


# ── Main ──────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",         start))
    app.add_handler(CommandHandler("aprobar",       aprobar))
    app.add_handler(CommandHandler("pendientes",    ver_pendientes))
    app.add_handler(CommandHandler("suscripciones", ver_suscripciones))
    app.add_handler(CallbackQueryHandler(ver_precios_cb,    pattern="^ver_precios$"))
    app.add_handler(CallbackQueryHandler(mi_suscripcion_cb, pattern="^mi_suscripcion$"))
    app.add_handler(CallbackQueryHandler(soporte_cb,        pattern="^soporte$"))
    app.add_handler(CallbackQueryHandler(contratar,         pattern="^contratar_"))
    app.add_handler(CallbackQueryHandler(tiene_cupon,       pattern="^tiene_cupon_"))
    app.add_handler(CallbackQueryHandler(elegir_pago,       pattern="^elegir_pago_"))
    app.add_handler(CallbackQueryHandler(mostrar_metodo,    pattern="^metodo_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_texto))
    print("AC Premium Bot arrancado.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
