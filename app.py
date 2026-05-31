from flask import Flask, request
import google.generativeai as genai

from linebot.v3.messaging import (
    MessagingApi,
    Configuration,
    ApiClient,
    ReplyMessageRequest,
    TextMessage
)

from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

from linebot.v3 import WebhookHandler

from supabase import create_client

import os

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OWNER_ID = os.getenv(
    "OWNER_ID",
    "U8ef199c624323ece6fb023faca74d59f"
)

ALLOWED_GROUP_ID = "Cc8cda1772dbd378254a51f4371c5985d"

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

genai.configure(api_key=GEMINI_API_KEY)

configuration = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN
)

handler = WebhookHandler(
    LINE_CHANNEL_SECRET
)


@app.route("/webhook", methods=["POST"])
def webhook():

    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    handler.handle(body, signature)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    user_id = event.source.user_id

    print("USER =", user_id)

    if user_id != OWNER_ID:
        return

    if hasattr(event.source, "group_id"):

        group_id = event.source.group_id

        print("GROUP =", group_id)

        if group_id != ALLOWED_GROUP_ID:
            return

    text = event.message.text.strip()

    if not text.startswith("@AI"):
        return

    user_text = text[3:].strip()

    if user_text == "ล้างความจำ":

        supabase.table("chat_memory")\
            .delete()\
            .eq("user_id", user_id)\
            .execute()

        reply_text = "ล้างความจำเรียบร้อย"

        send_reply(
            event.reply_token,
            reply_text
        )

        return

    history = supabase.table("chat_memory")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at")\
        .limit(20)\
        .execute()

    memory_text = ""

    for row in history.data:

        memory_text += (
            f"{row['role']}: "
            f"{row['content']}\n"
        )

    prompt = f"""
คุณคือ AI ผู้ช่วยภาษาไทย

ตอบสั้น
ตรงประเด็น
ไม่เกิน 5 บรรทัด

ประวัติสนทนา:

{memory_text}

ผู้ใช้:
{user_text}
"""

    model = genai.GenerativeModel(
        "gemini-3.5-flash"
    )

    response = model.generate_content(
        prompt
    )

    answer = response.text

    supabase.table("chat_memory")\
        .insert({
            "user_id": user_id,
            "role": "user",
            "content": user_text
        })\
        .execute()

    supabase.table("chat_memory")\
        .insert({
            "user_id": user_id,
            "role": "assistant",
            "content": answer
        })\
        .execute()

    send_reply(
        event.reply_token,
        answer[:5000]
    )


def send_reply(reply_token, text):

    with ApiClient(configuration) as api_client:

        line_bot_api = MessagingApi(
            api_client
        )

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    TextMessage(
                        text=text
                    )
                ]
            )
        )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
