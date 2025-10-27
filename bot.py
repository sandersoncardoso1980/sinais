import telebot
import json
import os
import logging
import flask # Importa o framework Flask
import threading # Para o modo de teste local, se necessário

# --- Configurações Essenciais ---
# Define a variável de ambiente para o modo de webhook
WEBHOOK_URL_BASE = os.getenv("WEBHOOK_URL_BASE") 
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configuração do bot e variáveis
ADMIN_ID = 565812291
ARQUIVO_ASSINANTES = "assinantes.json"

# Configuração do Flask
# Obtém a porta do Render. Se não estiver em ambiente Render, usa 5000 para teste local.
PORT = int(os.environ.get('PORT', 5000))

bot = telebot.TeleBot(BOT_TOKEN)
assinantes = {}
free_users = set()
ultimos_sinais = []

# Configuração de Log (opcional, mas recomendado)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cria a instância do servidor Flask
app = flask.Flask(__name__)

# ---------- Funções de persistência ----------
def salvar_assinantes():
    try:
        with open(ARQUIVO_ASSINANTES, "w") as f:
            json.dump({"assinantes": assinantes, "free_users": list(free_users)}, f)
    except Exception as e:
        logging.error(f"Erro ao salvar assinantes: {e}")

def carregar_assinantes():
    global assinantes, free_users
    if os.path.exists(ARQUIVO_ASSINANTES):
        try:
            with open(ARQUIVO_ASSINANTES, "r") as f:
                dados = json.load(f)
                assinantes = {int(k): v for k, v in dados.get("assinantes", {}).items()}
                free_users = set(dados.get("free_users", []))
        except Exception as e:
            logging.error(f"Erro ao carregar assinantes: {e}")

# ---------- Comandos (Os mesmos) ----------
@bot.message_handler(commands=["start"])
def start(msg):
    user_id = msg.from_user.id
    nome = msg.from_user.first_name
    
    # Garante que o ID do usuário seja salvo como string ou inteiro, dependendo da necessidade
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
    is_active = assinantes.get(user_id, {}).get("ativo", False)

    if is_active:
        if ultimos_sinais:
            bot.reply_to(msg, "📜 Últimos sinais:\n\n" + "\n".join(ultimos_sinais))
        else:
            bot.reply_to(msg, "Ainda não há sinais disponíveis.")
    else:
        if ultimos_sinais:
            texto = (
                "🆓 Prévia gratuita (2 sinais):\n\n"
                + "\n".join(ultimos_sinais[:2])
                + "\n\n💡 Assine por R$49,00 para receber a lista completa! https://buy.stripe.com/eVq7sE9F73Rcb2Ua4Y1gs00"
            )
            bot.reply_to(msg, texto)
        else:
            bot.reply_to(msg, "Ainda não há sinais disponíveis.")

@bot.message_handler(commands=["status"])
def status(msg):
    user_id = msg.from_user.id
    if assinantes.get(user_id, {}).get("ativo"):
        bot.reply_to(msg, "✅ Sua assinatura está ativa!")
    else:
        bot.reply_to(msg, "❌ Você ainda não é assinante.\n💳 Fale com o admin para assinar.")

@bot.message_handler(commands=["ativar"])
def ativar(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Somente o admin pode usar este comando.")
        return

    try:
        # Pega o ID do usuário após o comando /ativar
        target_id = int(msg.text.split()[1])
        
        # Garante que o usuário exista ou cria um placeholder
        if target_id not in assinantes:
             assinantes[target_id] = {"ativo": False, "nome": f"ID {target_id}"}
             
        assinantes[target_id]["ativo"] = True
        free_users.discard(target_id)
        salvar_assinantes()
        bot.reply_to(msg, f"Usuário {target_id} ativado ✅")
    except (IndexError, ValueError):
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
    except (IndexError, ValueError):
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
        status = "✅ Assinante" if dados.get("ativo") else "🆓 Free"
        nome = dados.get("nome", "Nome não definido")
        texto += f"ID: {uid} | {nome} | {status}\n"
    bot.reply_to(msg, texto)

@bot.message_handler(commands=["sinaisadmin"])
def sinais_admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "🚫 Sem permissão.")
        return

    raw_text = msg.text.partition(" ")[2].strip()
    if not raw_text:
        bot.reply_to(msg, "Use: /sinaisadmin SINAL1\nSINAL2\nSINAL3 (envie um sinal por linha)")
        return

    # Processa a lista de sinais, considerando um sinal por linha
    lista = [s.strip() for s in raw_text.splitlines() if s.strip()]

    global ultimos_sinais
    ultimos_sinais = lista

    # Envia a lista completa para assinantes
    for uid, dados in assinantes.items():
        if dados.get("ativo"):
            try:
                bot.send_message(uid, "📡 Lista completa de sinais:\n\n" + "\n".join(lista))
            except Exception:
                logging.exception(f"Erro ao enviar sinais para assinante {uid}")

    # Envia prévia para free users (2 sinais)
    for uid in free_users:
        try:
            preview = "\n".join(lista[:2]) if len(lista) >= 2 else "\n".join(lista)
            bot.send_message(uid, "🆓 Prévia gratuita (2 sinais):\n\n" + preview + "\n\n💡 Assine para receber todos!")
        except Exception:
            logging.exception(f"Erro ao enviar preview para free user {uid}")

    bot.reply_to(msg, "✅ Sinais processados e enviados.")


# ---------- Configuração do Webhook Flask ----------

# Rota principal para verificar se o bot está vivo
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'OK', 200

# Rota que o Telegram vai chamar com as atualizações
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '!', 200
    else:
        flask.abort(403) # Proíbe acesso direto

# ---------- Inicialização ----------
if __name__ == '__main__':
    carregar_assinantes()

    if BOT_TOKEN is None or WEBHOOK_URL_BASE is None:
        logging.error("As variáveis de ambiente BOT_TOKEN e WEBHOOK_URL_BASE DEVEM ser definidas.")
        print("INICIANDO EM MODO LONG POLLING (APENAS PARA TESTE LOCAL). Para Render, defina WEBHOOK_URL_BASE.")
        # Se as variáveis de webhook não estiverem definidas, volta para polling para teste local
        bot.remove_webhook()
        bot.infinity_polling()

    else:
        # Configuração do Webhook para o Render
        logging.info(f"Tentando configurar o webhook para: {WEBHOOK_URL_BASE}/{BOT_TOKEN}")
        
        # 1. Remove qualquer webhook antigo
        bot.remove_webhook()
        
        # 2. Configura o novo webhook
        bot.set_webhook(url=f"{WEBHOOK_URL_BASE}/{BOT_TOKEN}")
        
        # 3. Inicia o servidor web Flask (Render usará 'gunicorn')
        print(f"Bot iniciado em modo Webhook na porta {PORT}...")
        
        # No ambiente Render, o 'gunicorn' será usado. 
        # Para teste local, descomente as duas linhas abaixo:
        # threading.Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()
        pass
