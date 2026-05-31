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


def send_reply(reply_token, text):

    with ApiClient(configuration) as api_client:

        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    TextMessage(text=text[:5000])
                ]
            )
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):

    user_id = event.source.user_id
    text = event.message.text.strip()

    print("USER =", user_id)

    # เฉพาะเจ้าของ
    if user_id != OWNER_ID:
        return

    # ตรวจสอบกลุ่ม
    group_id = None

    if hasattr(event.source, "group_id"):

        group_id = event.source.group_id

        print("GROUP =", group_id)

        # อนุญาตกลุ่ม
        if text == "@AI อนุญาตกลุ่มนี้":

            supabase.table(
                "allowed_groups"
            ).upsert({
                "group_id": group_id
            }).execute()

            send_reply(
                event.reply_token,
                "อนุญาตกลุ่มนี้แล้ว"
            )

            return

        # ยกเลิกกลุ่ม
        if text == "@AI ยกเลิกกลุ่มนี้":

            supabase.table(
                "allowed_groups"
            ).delete().eq(
                "group_id",
                group_id
            ).execute()

            send_reply(
                event.reply_token,
                "ยกเลิกกลุ่มนี้แล้ว"
            )

            return

        # ตรวจว่ากลุ่มได้รับอนุญาตหรือยัง
        allowed = (
            supabase.table("allowed_groups")
            .select("*")
            .eq("group_id", group_id)
            .execute()
        )

        if not allowed.data:
            return

    if not text.startswith("@AI"):
        return

    user_text = text[3:].strip()

    # จำข้อมูลถาวร
    if user_text.startswith("จำไว้ว่า"):

        memory = user_text.replace(
            "จำไว้ว่า",
            ""
        ).strip()

        if "=" in memory:

            key, value = memory.split("=", 1)

            supabase.table(
                "user_profile"
            ).upsert({
                "user_id": user_id,
                "key": key.strip(),
                "value": value.strip()
            }).execute()

            send_reply(
                event.reply_token,
                f"จำแล้ว: {key.strip()}"
            )

            return

            send_reply(
                event.reply_token,
                "รูปแบบ: @AI จำไว้ว่า ชื่อ=เฟิส"
            )

            return

    # ดูความจำ
    if user_text == "จำอะไรเกี่ยวกับฉันบ้าง":

        result = (
            supabase.table("user_profile")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:

            send_reply(
                event.reply_token,
                "ยังไม่มีข้อมูลที่จำไว้"
            )

            return

        text_out = ""

        for row in result.data:

            text_out += (
                f"{row['key']} : "
                f"{row['value']}\n"
            )

        send_reply(
            event.reply_token,
            text_out
        )

        return

    # ลืมข้อมูล
    if user_text.startswith("ลืม"):

        key = user_text.replace(
            "ลืม",
            ""
        ).strip()

        supabase.table(
            "user_profile"
        ).delete().eq(
            "user_id",
            user_id
        ).eq(
            "key",
            key
        ).execute()

        send_reply(
            event.reply_token,
            f"ลืม {key} แล้ว"
        )

        return
    
    # ล้างความจำ
    if user_text == "ล้างความจำ":

        supabase.table(
            "chat_memory"
        ).delete().eq(
            "user_id",
            user_id
        ).execute()

        send_reply(
            event.reply_token,
            "ล้างความจำเรียบร้อย"
        )

        return

    # โหลดความจำ
    history = (
        supabase.table("chat_memory")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .limit(15)
        .execute()
    )

    memory_text = ""

    profile = (
        supabase.table("user_profile")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    profile_text = ""

    for row in profile.data:

        profile_text += (
            f"{row['key']} = "
            f"{row['value']}\n"
        )
        
    for row in history.data:

        memory_text += (
            f"{row['role']}: "
            f"{row['content']}\n"
        )

    prompt = f"""
คุณคือ AI ผู้ช่วยส่วนตัวของเฟิส

ข้อมูลผู้ใช้:

{profile_text}

ประวัติการสนทนา:

{memory_text}

กฎ:
- ตอบภาษาไทย
- ตอบสั้น
- ตรงประเด็น
- ไม่เกิน 5 บรรทัด
- ใช้ข้อมูลผู้ใช้และประวัติสนทนาได้

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

    # บันทึกความจำ
    supabase.table(
        "chat_memory"
    ).insert({
        "user_id": user_id,
        "role": "user",
        "content": user_text
    }).execute()

    supabase.table(
        "chat_memory"
    ).insert({
        "user_id": user_id,
        "role": "assistant",
        "content": answer
    }).execute()

    send_reply(
        event.reply_token,
        answer
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
