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

PAYMENT_INFO = """💳 *Métodos de pago:*

• Bizum: `612 345 678`
• PayPal: `tupaypal@email.com`
• Crypto (USDT/BTC): consulta al admin

📩 Envía el comprobante a """ + SUPPORT_USER

PLANES = {
    "mensual":    {"precio": 149,  "nombre": "Mensual",    "dias": 30,  "emoji": "🥉"},
    "trimestral": {"precio": 399,  "nombre": "Trimestral", "dias": 90,  "emoji": "🥈"},
    "semestral":  {"precio": 799,  "nombre": "Semestral",  "dias": 180, "emoji": "🥇"},
    "anual":      {"precio": 1499, "nombre": "Anual",      "dias": 365, "emoji": "💎"},
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

# ═══════════════════════════════════════════════
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

pendientes = {}

MENU_TECLADO = ReplyKeyboardMarkup(
    [[KeyboardButton("📋 Planes y Precios"), KeyboardButton("📊 Mi Suscripción")],
     [KeyboardButton("💬 Soporte"),          KeyboardButton("🏠 Inicio")]],
    resize_keyboard=True
)

def precio_con_descuento(precio, cupon):
    pct = CUPONES.get(cupon.upper(), 0)
    return int(precio * (1 - pct / 100)), pct

def estado_suscripcion_texto(user_id):
    sub = get_suscripcion(user_id)
    if not sub:
        return "❌ No tienes ninguna suscripción activa."
    fin = datetime.fromisoformat(sub["fin"])
    ahora = datetime.now()
    if ahora > fin:
        return "⚠️ Tu suscripción ha *expirado*."
    restante = fin - ahora
    dias = restante.days
    horas = restante.seconds // 3600
    plan = PLANES[sub["plan"]]["nombre"]
    inicio_str = datetime.fromisoformat(sub["inicio"]).strftime("%d/%m/%Y")
    fin_str = fin.strftime("%d/%m/%Y")
    usado = 1 - restante.total_seconds() / timedelta(days=PLANES[sub["plan"]]["dias"]).total_seconds()
    barra = min(int(usado * 10), 10)
    barra_txt = "🟩" * (10 - barra) + "⬜" * barra
    return (
        f"✅ *Suscripción activa — {plan}*\n\n"
        f"📅 Inicio: {inicio_str}\n"
        f"📅 Vence:  {fin_str}\n\n"
        f"⏳ Tiempo restante: *{dias} días y {horas}h*\n"
        f"{barra_txt}"
    )

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    nombre = update.effective_user.first_name
    texto = (
        f"👋 ¡Hola, *{nombre}*! Bienvenido a *AC Premium Signals* 📈\n\n"
        "Aquí puedes:\n"
        "• 💰 Comprar una suscripción premium\n"
        "• 📊 Ver el estado de tu membresía\n"
        "• 🔗 Acceder al canal de señales\n\n"
        "Si eres nuevo, usa el cupón *NEW20* para obtener un *20% de descuento* 🍀\n\n"
        "Usa el menú de abajo o elige una opción:"
    )
    teclado_inline = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Ver Planes y Precios", callback_data="ver_precios")],
        [InlineKeyboardButton("📊 Mi Suscripción",       callback_data="mi_suscripcion")],
        [InlineKeyboardButton("💬 Contactar Soporte",    callback_data="soporte")],
    ])
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=MENU_TECLADO)
    await update.message.reply_text("¿Qué quieres hacer?", reply_markup=teclado_inline)

def _precios_contenido():
    texto = "💎 *Planes AC Premium Signals*\n\n"
    for key, p in PLANES.items():
        texto += f"{p['emoji']} *{p['nombre']}* — *{p['precio']}€*\n"
    texto += f"\n🍀 Usa el código *NEW20* al contratar y obtén un *20% de descuento*"
    botones = []
    for key, p in PLANES.items():
        botones.append([InlineKeyboardButton(
            f"{p['emoji']} {p['nombre']} — {p['precio']}€",
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

async def mi_suscripcion_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    texto = estado_suscripcion_texto(update.effective_user.id)
    botones = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Ver Planes", callback_data="ver_precios")]])
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)

async def mi_suscripcion_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    texto = estado_suscripcion_texto(query.from_user.id)
    botones = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Ver Planes", callback_data="ver_precios")]])
    await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)

async def soporte_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💬 *Soporte AC Premium*\n\nEscríbenos directamente:\n👉 {SUPPORT_USER}\n\nEstamos disponibles 24/7 ✅",
        parse_mode="Markdown"
    )

async def soporte_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        f"💬 *Soporte AC Premium*\n\nEscríbenos directamente:\n👉 {SUPPORT_USER}\n\nEstamos disponibles 24/7 ✅",
        parse_mode="Markdown"
    )

async def contratar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan = query.data.replace("contratar_", "")
    user_id = query.from_user.id
    pendientes[user_id] = {"plan": plan, "cupon": None}
    p = PLANES[plan]
    texto = (
        f"{p['emoji']} *Plan seleccionado: {p['nombre']} — {p['precio']}€*\n\n"
        "¿Tienes un cupón de descuento?\n"
        "Escríbelo ahora o pulsa *Sin cupón* para continuar:"
    )
    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Continuar sin cupón", callback_data=f"pago_{plan}_nocupon")],
        [InlineKeyboardButton("🔙 Ver otros planes",    callback_data="ver_precios")],
    ])
    await query.message.reply_text(texto, parse_mode="Markdown", reply_markup=botones)

async def mensaje_texto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    texto = update.message.text.strip()
    if texto == "📋 Planes y Precios":
        return await ver_precios_msg(update, ctx)
    if texto == "📊 Mi Suscripción":
        return await mi_suscripcion_msg(update, ctx)
    if texto == "💬 Soporte":
        return await soporte_msg(update, ctx)
    if texto == "🏠 Inicio":
        return await start(update, ctx)
    if user_id in pendientes and pendientes[user_id].get("cupon") is None:
        plan = pendientes[user_id]["plan"]
        cupon = texto.upper()
        if cupon in CUPONES:
            pendientes[user_id]["cupon"] = cupon
            precio_orig = PLANES[plan]["precio"]
            precio_final, pct = precio_con_descuento(precio_orig, cupon)
            await update.message.reply_text(
                f"✅ *¡Cupón {cupon} aplicado!* -{pct}% de descuento\n\n"
                f"~~{precio_orig}€~~ → *{precio_final}€*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Ir a pagar", callback_data=f"pago_{plan}_{cupon}")]
                ])
            )
        else:
            await update.message.reply_text(
                "❌ Cupón no válido. Inténtalo de nuevo o continúa sin cupón.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➡️ Continuar sin cupón", callback_data=f"pago_{plan}_nocupon")]
                ])
            )

async def mostrar_pago(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    partes = query.data.split("_")
    plan  = partes[1]
    cupon = partes[2] if partes[2] != "nocupon" else None
    user_id = query.from_user.id
    p = PLANES[plan]
    precio_final = p["precio"]
    linea_cupon = ""
    if cupon and cupon in CUPONES:
        precio_final, pct = precio_con_descuento(p["precio"], cupon)
        linea_cupon = f"🍀 Cupón *{cupon}*: -{pct}% aplicado\n"
    pendientes[user_id] = {"plan": plan, "cupon": cupon}
    texto = (
        f"🛒 *Resumen de tu pedido*\n\n"
        f"{p['emoji']} Plan: *{p['nombre']}*\n"
        f"{linea_cupon}"
        f"💰 Total: *{precio_final}€*\n\n"
        f"{PAYMENT_INFO}\n\n"
        "Una vez enviado el comprobante, *confirmaremos tu acceso en menos de 24h* ✅"
    )
    await query.message.reply_text(texto, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contactar Soporte", callback_data="soporte")],
            [InlineKeyboardButton("🔙 Ver Planes", callback_data="ver_precios")],
        ]))
    await ctx.bot.send_message(
        ADMIN_ID,
        f"🔔 *Nuevo interesado en pagar*\n"
        f"👤 [{query.from_user.first_name}](tg://user?id={user_id}) — ID: `{user_id}`\n"
        f"📦 Plan: *{p['nombre']}* — {precio_final}€"
        + (f" (cupón {cupon})" if cupon else "") +
        f"\n\n▶️ Para aprobar: `/aprobar {user_id}`",
        parse_mode="Markdown"
    )

async def aprobar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sin permisos.")
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
        f"✅ *¡Pago confirmado! Bienvenido a AC Premium* 🎉\n\n"
        f"📦 Plan: *{PLANES[plan]['nombre']}*\n"
        f"📅 Tu acceso vence el: *{fin}*\n\n"
        f"🔗 *Tu link de acceso exclusivo:*\n{link}\n\n"
        f"⚠️ Este link es personal, no lo compartas.\n"
        f"Cualquier duda: {SUPPORT_USER} 🚀",
        parse_mode="Markdown"
    )
    await update.message.reply_text(f"✅ Aprobado. Plan *{plan}* hasta {fin}.", parse_mode="Markdown")
    pendientes.pop(user_id, None)

async def ver_pendientes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not pendientes:
        await update.message.reply_text("No hay usuarios pendientes.")
        return
    texto = "📋 *Pendientes:*\n\n"
    for uid, datos in pendientes.items():
        texto += f"• `{uid}` — *{datos['plan']}*\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

async def ver_suscripciones(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = cargar_db()
    if not db:
        await update.message.reply_text("No hay suscripciones.")
        return
    ahora = datetime.now()
    texto = "📊 *Suscripciones:*\n\n"
    for uid, sub in db.items():
        fin = datetime.fromisoformat(sub["fin"])
        estado = "✅" if fin > ahora else "❌"
        dias_rest = max((fin - ahora).days, 0)
        texto += f"{estado} `{uid}` — *{sub['plan']}* — {dias_rest}d\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

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
    app.add_handler(CallbackQueryHandler(mostrar_pago,      pattern="^pago_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje_texto))
    print("🤖 AC Premium Bot arrancado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
