import telebot
import json
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 565812291
ARQUIVO_ASSINANTES = "assinantes.json"

bot = telebot.TeleBot(BOT_TOKEN)
assinantes = {}
free_users = set()
ultimos_sinais = []

# ---------- Funções de persistência ----------
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

# ---------- Comandos ----------
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    nome = msg.from_user.first_name
    if user_id not in assinantes:
        assinantes[user_id] = {"ativo": False, "nome": nome}
        free_users.add(user_id)
        salvar_assinantes()

    texto = (
        f"🎯 Bem-vindo(a), {nome}!\n\n"
        "✅ Assinantes recebem a lista completa de sinais.\n"
        "🆓 Usuários free recebem apenas 2 sinais.\n"
        "💰 Plano Premium: R$49/mês.\n\n"
        "Use /sinais para ver os sinais disponíveis."
    )
    bot.reply_to(msg, texto)

@bot.message_handler(commands=["sinais"])
def sinais(msg):
    user_id = msg.from_user.id
    if user_id in assinantes and assinantes[user_id]["ativo"]:
        if ultimos_sinais:
            bot.reply_to(msg, "📜 Últimos sinais:\n\n" + "\n".join(ultimos_sinais))
        else:
            bot.reply_to(msg, "Ainda não há sinais disponíveis.")
    else:
        if ultimos_sinais:
            texto = (
                "🆓 Prévia gratuita (2 sinais):\n\n"
                + "\n".join(ultimos_sinais[:2])
                + "\n\n💡 Assine por R$49,00 para receber a lista completa! Fale com @sandersoncardoso"
            )
            bot.reply_to(msg, texto)
        else:
            bot.reply_to(msg, "Ainda não há sinais disponíveis.")

@bot.message_handler(commands=["status"])
def status(msg):
    user_id = msg.from_user.id
    if user_id in assinantes and assinantes[user_id]["ativo"]:
        bot.reply_to(msg, "✅ Sua assinatura está ativa!")
    else:
        bot.reply_to(msg, "❌ Você ainda não é assinante.\n💳 Fale com o admin para assinar.")

@bot.message_handler(commands=["ativar"])
def ativar(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando.")
        return

    try:
        target_id = int(msg.text.split()[1])
        assinantes[target_id] = {"ativo": True, "nome": "Usuário Ativo"}
        free_users.discard(target_id)
        salvar_assinantes()
        bot.reply_to(msg, f"Usuário {target_id} ativado ✅")
    except:
        bot.reply_to(msg, "Uso: /ativar <user_id>")

@bot.message_handler(commands=["desativar"])
def desativar(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando.")
        return

    try:
        target_id = int(msg.text.split()[1])
        if target_id in assinantes:
            assinantes[target_id]["ativo"] = False
            free_users.add(target_id)
            salvar_assinantes()
            bot.reply_to(msg, f"Usuário {target_id} desativado ✅")
        else:
            bot.reply_to(msg, "Usuário não encontrado.")
    except:
        bot.reply_to(msg, "Uso: /desativar <user_id>")

@bot.message_handler(commands=["usuarios"])
def usuarios(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando.")
        return

    if not assinantes:
        bot.reply_to(msg, "⚠️ Nenhum usuário registrado.")
        return

    texto = "📜 Usuários:\n\n"
    for uid, dados in assinantes.items():
        status = "✅ Assinante" if dados["ativo"] else "🆓 Free"
        texto += f"ID: {uid} | {dados['nome']} | {status}\n"
    bot.reply_to(msg, texto)

@bot.message_handler(commands=["sinaisadmin"])
@bot.message_handler(commands=["sinaisadmin"])
def sinais_admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Sem permissão.")
        return

    raw_text = msg.text.partition(" ")[2].strip()
    if not raw_text:
        bot.reply_to(msg, "Use: /sinaisadmin SINAL1;SINAL2;SINAL3 (separe por ';' ou por quebras de linha)")
        return

    # Tentamos primeiro por ';', se não existir, por linhas
    if ";" in raw_text:
        lista = [s.strip() for s in raw_text.split(";") if s.strip()]
    else:
        lista = [s.strip() for s in raw_text.splitlines() if s.strip()]

    global ultimos_sinais
    ultimos_sinais = lista

    # Envia a lista completa para assinantes
    for uid, dados in assinantes.items():
        if dados.get("ativo"):
            try:
                bot.send_message(uid, "📡 Lista completa de sinais:\n\n" + "\n".join(lista))
            except Exception:
                logging.exception(f"Erro ao enviar sinais para {uid}")

    # Envia prévia para free users (2 sinais)
    for uid in free_users:
        try:
            preview = "\n".join(lista[:2]) if len(lista) >= 2 else "\n".join(lista)
            bot.send_message(uid, "🆓 Prévia gratuita (2 sinais):\n\n" + preview + "\n\n💡 Assine para receber todos!")
        except Exception:
            logging.exception(f"Erro ao enviar preview para {uid}")

    bot.reply_to(msg, "✅ Sinais processados e enviados.")
    # ... (código existente)

if __name__ == '__main__':
    carregar_assinantes() # Carrega os dados antes de iniciar o bot
    print("Bot iniciado e escutando...")
    # Inicia o loop de polling que mantém o bot ativo
    bot.infinity_polling()




