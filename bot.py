# Telegram Promotional Bot - Render Deployment Version
# Requirements: telethon

import asyncio
import logging
import os
import random
import time
from typing import Set
from telethon import TelegramClient, events

# CONFIGURATION - Use environment variables for security
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
TARGET_BOT = os.getenv('TARGET_BOT', '@ChatOGeramBot') 
PROMO_BOT = os.getenv('PROMO_BOT', 'GlobalChatBot')
SESSION_NAME = os.getenv('SESSION_NAME', 'onAnonBot')

PORT = int(os.getenv('PORT', 10000))

message_counter = 0
used_messages: Set[str] = set()

EMOJI_LIST = [
    "✨", "🔥", "💯", "🎯", "🚀", "💡", "🌟", "💫", "⚡️", "🎉", 
    "🎊", "🎈", "😎", "🤩", "✌️", "👌", "👍", "🙌", "👋", "👀"
]

FALLBACK_TEMPLATES = [
    "حوصلت سر رفته؟ 🥹\nبا {bot} با آدمای جدید و تصادفی آشنا شو 👇🏻\nفقط اسمشو توی سرچ تلگرام بزن",
    "دنبال یه چت ناشناس باحال‌تر می‌گردی؟ 😎\nربات {bot} رو امتحان کن!\nکلی آدم جدید اونجان منتظر تو\n\nآیدی: {bot}",
    "اینجا خلوته؟ 🥲\nبیا تو {bot}، پر از آدمای آنلاینه که می‌تونی باهاشون چت کنی 💬\nسرچ کن {bot}",
    "می‌خوای با آدمای جدید و باحال آشنا بشی؟ 🤩\nربات {bot} بهترین جاست برای چت ناشناس!\nهمین الان تو تلگرام سرچش کن",
    "چت ناشناس بدون قطعی و سریع می‌خوای؟ 🚀\nفقط {bot}!\nآیدی بات رو سرچ کن و استارت بزن 👇🏻\n{bot}",
]

SHORT_PROMOS = [
    "این روزا برای چت ناشناس بیشتر از {bot} استفاده می‌کنم 👀\nتوی سرچ تلگرام بزن {bot} 🤖",
    "بیا {bot} چت کنیم، اینجا خسته کننده‌س 🥱",
    "بهترین ربات چت ناشناس الان {bot} هست، حتما امتحانش کن",
    "حوصلت سر رفته؟ بیا {bot} کلی آدم آنلاین داره",
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_random_message() -> str:
    global message_counter
    message_counter += 1

    template = random.choice(SHORT_PROMOS) if random.random() < 0.4 else random.choice(FALLBACK_TEMPLATES)
    base_message = template.format(bot=PROMO_BOT)
    random_emojis = "".join(random.sample(EMOJI_LIST, k=random.randint(2, 3)))
    message = f"{base_message} {random_emojis}"

    if message in used_messages:
        message = f"{message} ({message_counter})"

    used_messages.add(message)
    return message

class TelegramPromoBot:
    def __init__(self):
        from telethon.sessions import StringSession
        session_string = os.getenv('SESSION_STRING', '')
        
        if session_string:
            self.client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            
        self.state = "idle" # States: idle, searching, chatting
        self.last_activity_time = time.time()

    async def watchdog(self):
        """Monitors the bot state and unsticks it if it hangs."""
        while True:
            await asyncio.sleep(5)
            time_since_activity = time.time() - self.last_activity_time
            
            # If stuck searching for more than 20 seconds
            if self.state == "searching" and time_since_activity > 20.0:
                logger.warning("⚠️ Bot seems stuck on 'Searching...'. Forcing a new request to unstick it!")
                self.state = "idle"
                await self.client.send_message(TARGET_BOT, "به یه ناشناس وصلم کن!")
                self.last_activity_time = time.time()
                
            # If stuck inside a chat for more than 60 seconds (something failed)
            elif self.state == "chatting" and time_since_activity > 60.0:
                logger.warning("⚠️ Bot seems stuck in a chat. Forcing exit...")
                await self.client.send_message(TARGET_BOT, "پایان چت 🚫")
                self.last_activity_time = time.time()

    async def request_stranger(self):
        """Helper to request a new chat and update state."""
        self.state = "idle"
        await asyncio.sleep(1.5)
        await self.client.send_message(TARGET_BOT, "به یه ناشناس وصلم کن!")
        self.last_activity_time = time.time()
        logger.info("✅ Requested new stranger connection.")

    async def start(self):
        if not os.getenv('API_ID'):
            logger.error("❌ Missing required API_ID")
            return

        await self.client.start(phone=PHONE_NUMBER)
        logger.info("✅ Telegram client started successfully")

        # Start the anti-stuck watchdog in the background
        self.client.loop.create_task(self.watchdog())

        @self.client.on(events.NewMessage(chats=TARGET_BOT, incoming=True))
        async def handle_new_message(event):
            await self.process_message(event)

        logger.info(f"🤖 Monitoring {TARGET_BOT} for messages...")

        logger.info("🚀 Sending initial /start command to wake up the bot...")
        await asyncio.sleep(2) 
        try:
            await self.client.send_message(TARGET_BOT, "/start")
        except Exception as e:
            logger.error(f"❌ Could not send /start: {e}")

        await self.start_health_server()
        await self.client.run_until_disconnected()

    async def process_message(self, event):
        try:
            message_text = event.message.text or ""
            clean_text = message_text.replace('\n', ' ')
            logger.info(f"👀 Bot Saw: {clean_text[:80]}...")
            
            # Reset the watchdog timer on every received message
            self.last_activity_time = time.time()
            
            # STEP 0: Ignore History Deletion prompts
            if "delHistory" in message_text:
                logger.info("🧹 Bot offered to delete history. Ignoring safely.")
                return
                
            # Update state to searching
            elif "درحال جستجوی" in message_text:
                self.state = "searching"
                logger.info("🔎 Bot is searching... Watchdog timer started.")
                return

            # STEP 1: Main Menu 
            if "منوی" in message_text or "استارت" in message_text:
                logger.info("📍 Main Menu detected.")
                await self.request_stranger()

            # STEP 2: Search Type Menu 
            elif "پیدا کنم" in message_text:
                logger.info("📍 Search menu detected. Clicking Random Search...")
                await asyncio.sleep(1.5)
                if event.message.buttons:
                    for row in event.message.buttons:
                        for button in row:
                            if 'شانسی' in button.text: 
                                await button.click()
                                logger.info("✅ Clicked Random Search button!")
                                return

            # STEP 3: Match Found
            elif "چت با" in message_text and "شروع شد" in message_text:
                self.state = "chatting"
                logger.info("🎯 MATCH DETECTED! Executing promo sequence...")
                
                await asyncio.sleep(random.uniform(1.5, 3.0))
                promo = generate_random_message()
                await self.client.send_message(TARGET_BOT, promo)
                logger.info("✅ Promo sent!")
                
                delay = random.uniform(7.0, 10.0)
                logger.info(f"⏳ Waiting {delay:.1f}s before skipping...")
                await asyncio.sleep(delay)
                await self.client.send_message(TARGET_BOT, "پایان چت 🚫")
                logger.info("✅ Sent 'End Chat' command.")

            # STEP 3.5: The OTHER person ends the chat first
            elif "بسته شد" in message_text and "ایشون" in message_text:
                logger.info("⚠️ Other user closed the chat first. Finding a new one...")
                await self.request_stranger()

            # STEP 3.6: Cooldown / Anti-spam bypass
            elif "بستن چت" in message_text and "صبر کنید" in message_text:
                logger.warning("⏳ Hit the chat closing cooldown! Waiting 3 seconds and retrying...")
                await asyncio.sleep(3.0)
                await self.client.send_message(TARGET_BOT, "پایان چت 🚫")
                logger.info("✅ Retried 'End Chat' command.")

            # STEP 4: End Chat Confirmation 
            elif "مطمئنی" in message_text:
                logger.info("📍 End chat confirmation detected. Clicking 'Yes'...")
                await asyncio.sleep(1.0)
                if event.message.buttons:
                    for row in event.message.buttons:
                        for button in row:
                            if 'آره' in button.text:
                                await button.click()
                                logger.info("✅ Clicked Yes to close chat!")
                                await self.request_stranger()
                                return

        except Exception as e:
            logger.error(f"❌ Error during message processing: {e}")

    async def start_health_server(self):
        from aiohttp import web
        async def health_check(request):
            return web.Response(text='Running', status=200)
        app = web.Application()
        app.router.add_get('/', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()

async def main():
    bot = TelegramPromoBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("Stopped")
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
        
