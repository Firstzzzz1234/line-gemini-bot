from flask import Flask, request
import google.generativeai as genai
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3 import WebhookHandler

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "tPgzxYVdx/cmxC3Oo3E3eibNqBi6DnPTbXmlcnzMR7fH83HNfmSItd672Gw4bmkj/JpdP0jEdElQGtmHQ1q5NE02fyWlXMaosEwOJUWif1RyH3ZLQd4ij3cFi47SM+tC0i3ZUEKPKq5c1iukLQ+VwAdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "17d7bc70c1a4140d10ba432638509fb8"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

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
    text = event.message.text

    if not text.startswith("@AI"):
        return

    prompt = text[3:].strip()

    model = genai.GenerativeModel("gemini-1.5-flash")
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
