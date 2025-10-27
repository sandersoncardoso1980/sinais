import logging
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configurações do bot
BOT_TOKEN = "7705926836:AAFBvmXyzrnQN9Lrtp3TUwvc-S-49vnisHA"
ADMIN_ID = 565812291  # teu ID do Telegram
assinantes = {}  # {user_id: {"ativo": True/False, "nome": str}}
free_users = set()
ultimos_sinais = []

ARQUIVO_ASSINANTES = "assinantes.json"

logging.basicConfig(level=logging.INFO)

# Funções de persistência
def salvar_assinantes():
    with open(ARQUIVO_ASSINANTES, "w") as f:
        json.dump({"assinantes": assinantes, "free_users": list(free_users)}, f)

def carregar_assinantes():
    global assinantes, free_users
    if os.path.exists(ARQUIVO_ASSINANTES):
        with open(ARQUIVO_ASSINANTES, "r") as f:
            dados = json.load(f)
            assinantes = dados.get("assinantes", {})
            free_users = set(dados.get("free_users", []))

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    nome = update.message.from_user.first_name

    if user_id not in assinantes:
        assinantes[user_id] = {"ativo": False, "nome": nome}
        free_users.add(user_id)
        salvar_assinantes()

    msg = f"🎯 Bem-vindo(a), {nome}!\n\n"
    msg += "✅ Assinantes recebem a lista completa de sinais.\n"
    msg += "🆓 Usuários free recebem apenas 2 sinais como prévia.\n"
    msg += "💰 Plano Premium: R$49/mês.\n\n"
    msg += "Use /sinais para ver os sinais disponíveis."
    await update.message.reply_text(msg)

# /sinais
async def sinais(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id in assinantes and assinantes[user_id]["ativo"]:
        if ultimos_sinais:
            await update.message.reply_text("📜 Últimos sinais:\n\n" + "\n".join(ultimos_sinais))
        else:
            await update.message.reply_text("Ainda não há sinais disponíveis.")
    else:
        if ultimos_sinais:
            await update.message.reply_text(
                "🆓 Prévia gratuita (2 sinais):\n\n" +
                "\n".join(ultimos_sinais[:2]) +
                "\n\n💡 Assine por R$49,00 para receber a lista completa! Fale com @sandersoncardoso"
            )
        else:
            await update.message.reply_text("Ainda não há sinais disponíveis.")

# /status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in assinantes and assinantes[user_id]["ativo"]:
        await update.message.reply_text("✅ Sua assinatura está ativa. Aproveite os sinais!")
    else:
        await update.message.reply_text("❌ Você ainda não é assinante. Recebe apenas 2 sinais free.\n💳 Fale com o admin para assinar.")

# /ativar
async def ativar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Somente admin pode usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Uso: /ativar <user_id>")
        return

    try:
        target_id = int(context.args[0])
        if target_id in assinantes:
            assinantes[target_id]["ativo"] = True
        else:
            assinantes[target_id] = {"ativo": True, "nome": "Usuário Ativo"}
        free_users.discard(target_id)
        salvar_assinantes()
        await update.message.reply_text(f"Usuário {target_id} ativado como assinante ✅")
    except Exception as e:
        await update.message.reply_text(f"Erro ao ativar: {e}")

# /desativar
async def desativar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Somente admin pode usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Uso: /desativar <user_id>")
        return

    try:
        target_id = int(context.args[0])
        if target_id in assinantes:
            assinantes[target_id]["ativo"] = False
            free_users.add(target_id)
            salvar_assinantes()
            await update.message.reply_text(f"Usuário {target_id} desativado ✅")
        else:
            await update.message.reply_text("Usuário não encontrado.")
    except Exception as e:
        await update.message.reply_text(f"Erro ao desativar: {e}")

# /remover
async def remover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Somente admin pode usar este comando.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Uso: /remover <user_id>")
        return

    try:
        target_id = int(context.args[0])
        if target_id in assinantes:
            del assinantes[target_id]
            free_users.discard(target_id)
            salvar_assinantes()
            await update.message.reply_text(f"Usuário {target_id} removido ✅")
        else:
            await update.message.reply_text("Usuário não encontrado.")
    except Exception as e:
        await update.message.reply_text(f"Erro ao remover: {e}")

# /usuarios
async def usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Somente admin pode usar este comando.")
        return

    if not assinantes:
        await update.message.reply_text("⚠️ Nenhum usuário registrado ainda.")
        return

    msg = "📜 Lista de usuários:\n\n"
    for uid, dados in assinantes.items():
        status = "✅ Assinante" if dados["ativo"] else "🆓 Free"
        msg += f"ID: {uid} | Nome: {dados['nome']} | Status: {status}\n"

    await update.message.reply_text(msg)

# /sinaisadmin
async def sinais_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Você não tem permissão para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("Use: /sinaisadmin M5;EURJPY;01:05;CALL M5;EURJPY;02:00;CALL ...")
        return

    raw_text = update.message.text.partition(' ')[2]
    lista_sinais = [s.strip() for s in raw_text.replace("\n", " ").split(" ") if s.strip()]
    global ultimos_sinais
    ultimos_sinais = lista_sinais

    for uid, dados in assinantes.items():
        if dados["ativo"]:
            try:
                await context.bot.send_message(uid, "📡 Lista completa de sinais:\n\n" + "\n".join(lista_sinais))
            except:
                logging.warning(f"Não consegui mandar pro {uid}")

    for uid in free_users:
        try:
            await context.bot.send_message(uid, "🆓 Prévia gratuita (2 sinais):\n\n" + "\n".join(lista_sinais[:2]) +
                                           "\n\n💡 Assine para receber todos!")
        except:
            logging.warning(f"Não consegui mandar pro {uid}")

    await update.message.reply_text("✅ Sinais enviados para todos.")

# main
def main():
    carregar_assinantes()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sinais", sinais))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("ativar", ativar))
    app.add_handler(CommandHandler("desativar", desativar))
    app.add_handler(CommandHandler("remover", remover))
    app.add_handler(CommandHandler("usuarios", usuarios))
    app.add_handler(CommandHandler("sinaisadmin", sinais_admin))

    print("Bot rodando 🚀")
    app.run_polling()

if __name__ == "__main__":
    main()
