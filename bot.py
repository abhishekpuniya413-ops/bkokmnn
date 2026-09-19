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
PROMO_BOT = os.getenv('PROMO_BOT', '@GlobalChatBot')
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
        
        self.target_bot_entity = None

    async def start(self):
        if not os.getenv('API_ID'):
            logger.error("❌ Missing required API_ID")
            return

        await self.client.start(phone=PHONE_NUMBER)
        logger.info("✅ Telegram client started successfully")

        try:
            self.target_bot_entity = await self.client.get_entity(TARGET_BOT)
            logger.info(f"✅ Successfully locked onto target bot: {TARGET_BOT}")
        except Exception as e:
            logger.error(f"❌ Could not find {TARGET_BOT}. Error: {e}")
            return

        @self.client.on(events.NewMessage(chats=self.target_bot_entity, incoming=True))
        async def handle_new_message(event):
            await self.process_message(event)

        logger.info("🤖 Monitoring for messages...")

        # AUTO-START: Kick off the flow by sending /start
        logger.info("🚀 Sending initial /start command to wake up the bot...")
        await asyncio.sleep(2) 
        await self.client.send_message(self.target_bot_entity, "/start")

        await self.start_health_server()
        await self.client.run_until_disconnected()

    async def process_message(self, event):
        message_text = event.message.text or ""
        clean_text = message_text.replace('\n', ' ')
        logger.info(f"👀 Bot Saw: {clean_text[:80]}...")

        # ---------------------------------------------------------
        # THE EXACT FLOW RECREATED FROM YOUR IMAGES
        # ---------------------------------------------------------

        # STEP 1: Main Menu -> Send text to request stranger
        if "منوی اصلی" in message_text or "ربات استارت شد" in message_text:
            logger.info("📍 Main Menu detected. Requesting stranger connection...")
            await asyncio.sleep(1.5)
            await self.client.send_message(self.target_bot_entity, "به یه ناشناس وصلم کن!")

        # STEP 2: Search Type Menu -> Click Inline "Random Search" Button
        elif "کیو پیدا کنم برات؟" in message_text:
            logger.info("📍 Search menu detected. Clicking Random Search...")
            await asyncio.sleep(1.5)
            if event.message.buttons:
                for row in event.message.buttons:
                    for button in row:
                        if 'شانسی' in button.text:  # Looks for 'جستجوی شانسی 🎲'
                            await button.click()
                            logger.info("✅ Clicked Random Search button!")
                            return

        # STEP 3: Match Found -> Wait -> Promo -> End Chat
        elif "چت با (آشنایت)" in message_text:
            logger.info("🎯 MATCH DETECTED! Executing promo sequence...")
            
            # Wait 2 seconds before pasting promo
            await asyncio.sleep(random.uniform(1.5, 3.0))
            promo = generate_random_message()
            await self.client.send_message(self.target_bot_entity, promo)
            logger.info("✅ Promo sent!")
            
            # Wait 5 to 8 seconds, then send the exact "End Chat" text command
            delay = random.uniform(5.0, 8.0)
            logger.info(f"⏳ Waiting {delay:.1f}s before skipping...")
            await asyncio.sleep(delay)
            await self.client.send_message(self.target_bot_entity, "پایان چت 🚫")
            logger.info("✅ Sent 'End Chat' command.")

        # STEP 4: End Chat Confirmation -> Click Inline "Yes" Button
        elif "مطمئنی که میخوای گفتگو رو" in message_text:
            logger.info("📍 End chat confirmation detected. Clicking 'Yes'...")
            await asyncio.sleep(1.0)
            if event.message.buttons:
                for row in event.message.buttons:
                    for button in row:
                        if 'آره' in button.text:  # Looks for 'آره چت رو ببند ❌'
                            await button.click()
                            logger.info("✅ Clicked Yes to close chat!")
                            
                            # Loop restart: Request new stranger after closing
                            await asyncio.sleep(2)
                            await self.client.send_message(self.target_bot_entity, "به یه ناشناس وصلم کن!")
                            return

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
            
