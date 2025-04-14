import requests

# ⚠️ 請將下方兩行替換成你自己的資訊
BOT_TOKEN = "你的_Telegram_Bot_Token"
CHAT_ID = "你的_Telegram_Chat_ID"

def send_telegram_alert(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print("⚠️ 推播失敗:", response.text)
    else:
        print("✅ 已推播至 Telegram")
    return response.status_code
