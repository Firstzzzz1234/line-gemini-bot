from flask import Flask, request
import google.generativeai as genai
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3 import WebhookHandler

app = Flask(__name__)

import os

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OWNER_ID = "U8ef199c624323ece6fb023faca74d59f"

ALLOWED_GROUP_ID = "ใส่ group id ตรงนี้"

print("Gemini Key Loaded:", GEMINI_API_KEY[:10] if GEMINI_API_KEY else "NONE")
genai.configure(api_key=GEMINI_API_KEY)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    handler.handle(body, signature)
    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    print("USER ID =", event.source.user_id)

    if hasattr(event.source, "group_id"):
        print("GROUP ID =", event.source.group_id)

    text = event.message.text

    if event.source.user_id != OWNER_ID:
        return

    text = event.message.text

    if not text.startswith("@AI"):
        return

    prompt = text[3:].strip()

    model = genai.GenerativeModel("gemini-3.5-flash")
    response = model.generate_content(prompt)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response.text[:5000])]
            )
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
