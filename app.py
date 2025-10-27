import telebot
import json
import os
import logging
import flask
import time

# --- Configurações ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE")

ADMIN_ID = 565812291
ARQUIVO_ASSINANTES = "assinantes.json"
PORT = int(os.environ.get('PORT', 5000))

# --- Validação ---
if not BOT_TOKEN:
    raise ValueError("ERRO: BOT_TOKEN não definido no ambiente!")

# --- Inicialização ---
bot = telebot.TeleBot(BOT_TOKEN)
app = flask.Flask(__name__)

assinantes = {}
free_users = set()
ultimos_sinais = []

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Persistência ---
def salvar_assinantes():
    try:
        with open(ARQUIVO_ASSINANTES, "w", encoding="utf-8") as f:
            json.dump({"assinantes": assinantes, "free_users": list(free_users)}, f, ensure_ascii=False, indent=2)
        logging.info("Assinantes salvos.")
    except Exception as e:
        logging.error(f"Erro ao salvar: {e}")

def carregar_assinantes():
    global assinantes, free_users
    if os.path.exists(ARQUIVO_ASSINANTES):
        try:
            with open(ARQUIVO_ASSINANTES, "r", encoding="utf-8") as f:
                dados = json.load(f)
                assinantes = {int(k): v for k, v in dados.get("assinantes", {}).items()}
                free_users = set(dados.get("free_users", []))
            logging.info("Assinantes carregados.")
        except Exception as e:
            logging.error(f"Erro ao carregar: {e}")
    else:
        logging.info("Nenhum arquivo de assinantes encontrado.")

# --- Comandos ---
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    nome = msg.from_user.first_name or "Usuário"

    if user_id not in assinantes:
        assinantes[user_id] = {"ativo": False, "nome": nome}
        free_users.add(user_id)
        salvar_assinantes()

    texto = (
        f"🎯 Bem\\-vindo\\(a\\), *{nome}*\\!\\n\\n"
        "✅ Assinantes recebem a lista completa de sinais\\.\n"
        "🆓 Usuários free recebem apenas 2 sinais\\.\n"
        "💰 Plano Premium: R\\$49/mês\\.\n\n"
        "Use /sinais para ver os sinais disponíveis\\."
    )
    bot.reply_to(msg, texto, parse_mode="MarkdownV2")

@bot.message_handler(commands=["sinais"])
def sinais(msg):
    user_id = msg.from_user.id
    is_active = assinantes.get(user_id, {}).get("ativo", False)

    if not ultimos_sinais:
        bot.reply_to(msg, "Ainda não há sinais disponíveis\\.")
        return

    if is_active:
        resposta = "📜 *Últimos sinais:*\\n\\n" + "\\n".join(ultimos_sinais)
    else:
        preview = ultimos_sinais[:2]
        resposta = (
            "🆓 *Prévia gratuita \\(2 sinais\\):*\\n\\n"
            + "\\n".join(preview)
            + "\\n\\n💡 Assine por R\\$49,00 para receber a lista completa\\! "
              "[Clique aqui](https://buy.stripe.com/eVq7sE9F73Rcb2Ua4Y1gs00)"
        )
    bot.reply_to(msg, resposta, parse_mode="MarkdownV2", disable_web_page_preview=True)

@bot.message_handler(commands=["status"])
def status(msg):
    user_id = msg.from_user.id
    if assinantes.get(user_id, {}).get("ativo", False):
        bot.reply_to(msg, "✅ Sua assinatura está *ativa*\\!", parse_mode="MarkdownV2")
    else:
        bot.reply_to(msg, "❌ Você ainda não é assinante\\.\n💳 Fale com o admin\\.", parse_mode="MarkdownV2")

@bot.message_handler(commands=["ativar"])
def ativar(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando\\.", parse_mode="MarkdownV2")
        return

    try:
        target_id = int(msg.text.split()[1])
        if target_id not in assinantes:
            assinantes[target_id] = {"ativo": True, "nome": f"ID {target_id}"}
        else:
            assinantes[target_id]["ativo"] = True
        free_users.discard(target_id)
        salvar_assinantes()
        bot.reply_to(msg, f"Usuário `{target_id}` ativado ✅", parse_mode="MarkdownV2")  # ← CORRIGIDO!
    except (IndexError, ValueError):
        bot.reply_to(msg, "Uso: /ativar <user_id>")

@bot.message_handler(commands=["desativar"])
def desativar(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando\\.", parse_mode="MarkdownV2")
        return

    try:
        target_id = int(msg.text.split()[1])
        if target_id in assinantes:
            assinantes[target_id]["ativo"] = False
            free_users.add(target_id)
            salvar_assinantes()
            bot.reply_to(msg, f"Usuário `{target_id}` desativado ✅", parse_mode="MarkdownV2")
        else:
            bot.reply_to(msg, "Usuário não encontrado\\.")
    except (IndexError, ValueError):
        bot.reply_to(msg, "Uso: /desativar <user_id>")

@bot.message_handler(commands=["usuarios"])
def usuarios(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando\\.", parse_mode="MarkdownV2")
        return

    if not assinantes:
        bot.reply_to(msg, "⚠️ Nenhum usuário registrado\\.")
        return

    texto = "*📜 Lista de Usuários:*\\n\\n"
    for uid, dados in assinantes.items():
        status = "✅ Assinante" if dados.get("ativo") else "🆓 Free"
        nome = dados.get("nome", "Sem nome")
        texto += f"• `{uid}` \\| {nome} \\| {status}\\n"
    bot.reply_to(msg, texto, parse_mode="MarkdownV2")

@bot.message_handler(commands=["sinaisadmin"])
def sinais_admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Sem permissão\\.", parse_mode="MarkdownV2")
        return

    raw_text = msg.text.partition(" ")[2].strip()
    if not raw_text:
        bot.reply_to(msg, "Use: /sinaisadmin SINAL1\\nSINAL2\\nSINAL3")
        return

    lista = [s.strip() for s in raw_text.splitlines() if s.strip()]
    if not lista:
        bot.reply_to(msg, "Nenhum sinal válido\\.")
        return

    global ultimos_sinais
    ultimos_sinais = lista

    for uid, dados in assinantes.items():
        if dados.get("ativo"):
            try:
                bot.send_message(uid, "📡 *Lista completa:*\\n\\n" + "\\n".join(lista), parse_mode="MarkdownV2")
            except Exception as e:
                logging.error(f"Erro ao enviar para {uid}: {e}")

    preview = "\\n".join(lista[:2]) if len(lista) >= 2 else "\\n".join(lista)
    for uid in free_users:
        try:
            bot.send_message(uid, f"🆓 *Prévia \\(2 sinais\\):*\\n\\n{preview}\\n\\n💡 Assine\\!", parse_mode="MarkdownV2")
        except Exception as e:
            logging.error(f"Erro ao enviar preview para {uid}: {e}")

    bot.reply_to(msg, f"✅ {len(lista)} sinais enviados\\.", parse_mode="MarkdownV2")

# --- Flask Routes ---
@app.route('/', methods=['GET', 'HEAD'])
def index():
    logging.info("Raiz acessada — servidor vivo!")
    return 'Bot OK e pronto pro Telegram! 🚀', 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        logging.info(f"Update recebido: {update.message.text if update.message else 'sem texto'}")
        bot.process_new_updates([update])
        return '!', 200
    flask.abort(403)

# --- Inicialização ---
carregar_assinantes()

if __name__ == '__main__':
    if not WEBHOOK_URL_BASE:
        logging.warning("WEBHOOK_URL_BASE ausente → modo polling local")
        bot.infinity_polling()
    else:
        webhook_url = f"{WEBHOOK_URL_BASE}/{BOT_TOKEN}"
        logging.info(f"Configurando webhook: {webhook_url}")
        bot.remove_webhook()
        time.sleep(1)
        if bot.set_webhook(url=webhook_url):
            logging.info("Webhook configurado com sucesso!")
        else:
            logging.error("Falha ao configurar webhook!")
else:
    # Executado pelo gunicorn no Render
    if WEBHOOK_URL_BASE and BOT_TOKEN:
        webhook_url = f"{WEBHOOK_URL_BASE}/{BOT_TOKEN}"
        logging.info(f"[Render] Configurando webhook: {webhook_url}")
        bot.remove_webhook()
        time.sleep(1)
        if not bot.set_webhook(url=webhook_url):
            logging.error("FALHA CRÍTICA: Webhook não configurado!")
        else:
            logging.info("Webhook ativo no Render! 🚀")
