# Telegram Promo Bot for Chatify AnonBot
# Requirements: telethon

import asyncio
import logging
import os
import random
import re
import time
from typing import Set
from telethon import TelegramClient, events

# CONFIGURATION - Use environment variables for security
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
TARGET_BOT = os.getenv('TARGET_BOT', '@ChatifyAnonBot') 
PROMO_BOT = os.getenv('PROMO_BOT', 'GlobalChatBot')
SESSION_NAME = os.getenv('SESSION_NAME', 'onAnonBot')

PORT = int(os.getenv('PORT', 10000))

message_counter = 0
used_messages: Set[str] = set()

EMOJI_LIST = [
    "✨", "🔥", "💯", "🎯", "🚀", "💡", "🌟", "💫", "⚡️", "🎉", 
    "🎊", "🎈", "😎", "🤩", "✌️", "👌", "👍", "🙌", "👋", "👀"
]

# English Promotional Templates
FALLBACK_TEMPLATES = [
    "Bored? 🥹 Meet new random people with {bot} 👇🏻\nJust search its username in Telegram!",
    "Looking for a better anonymous chat? 😎 Try {bot}!\nLots of new people waiting for you there\n\nUsername: {bot}",
    "Is it quiet here? 🥲\nCome to {bot}, it's full of online people you can chat with 💬\nSearch {bot}",
    "Want to meet cool new people? 🤩\n{bot} is the best place for anonymous chat!\nSearch it on Telegram right now",
    "Want fast anonymous chat with no interruptions? 🚀\nJust {bot}!\nSearch the bot username and start 👇🏻\n{bot}",
]

SHORT_PROMOS = [
    "I use {bot} more often for anonymous chat these days 👀\nSearch {bot} in Telegram 🤖",
    "Come chat on {bot}, it's getting boring here 🥱",
    "The best anonymous chat bot right now is {bot}, you must try it!",
    "Bored? Come to {bot}, it has plenty of online people",
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
        self.last_search_time = 0
        self.chat_session_id = 0 # Prevents old async timers from firing in new chats

    async def watchdog(self):
        """Monitors the bot state and unsticks it if it hangs."""
        while True:
            await asyncio.sleep(5)
            time_since_activity = time.time() - self.last_activity_time
            
            if self.state in ["idle", "searching"] and time_since_activity > 25.0:
                logger.warning("⚠️ Bot seems stuck or inactive. Resending /search...")
                await self.request_search()
                
            elif self.state == "chatting" and time_since_activity > 60.0:
                logger.warning("⚠️ Bot seems stuck in a chat. Forcing /next...")
                await self.client.send_message(TARGET_BOT, "/next")
                self.last_activity_time = time.time()

    async def request_search(self):
        """Helper to send /search safely with cooldown."""
        current_time = time.time()
        if current_time - self.last_search_time > 4.0:
            self.state = "searching"
            await asyncio.sleep(1.0)
            await self.client.send_message(TARGET_BOT, "/search")
            self.last_search_time = current_time
            self.last_activity_time = current_time
            logger.info("✅ Sent /search command.")

    async def start(self):
        if not os.getenv('API_ID'):
            logger.error("❌ Missing required API_ID")
            return

        await self.client.start(phone=PHONE_NUMBER)
        logger.info("✅ Telegram client started successfully")

        self.client.loop.create_task(self.watchdog())

        @self.client.on(events.NewMessage(chats=TARGET_BOT, incoming=True))
        async def handle_new_message(event):
            await self.process_message(event)

        logger.info(f"🤖 Monitoring {TARGET_BOT} for messages...")
        await asyncio.sleep(2) 
        try:
            self.state = "idle"
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
            
            self.last_activity_time = time.time()
            
            # STEP 0: Handle Chatify's Anti-Spam / Skip Cooldown
            if "Please wait" in message_text and "before ending the chat" in message_text:
                match = re.search(r'wait\s+(\d+)\s+more\s+seconds', message_text)
                if match:
                    wait_time = int(match.group(1))
                    logger.warning(f"⏳ Hit skip cooldown! Waiting {wait_time}s before retrying /next...")
                    current_session = self.chat_session_id
                    
                    await asyncio.sleep(wait_time + 1.0)
                    
                    # Only retry if we haven't already moved to a new chat
                    if self.state == "chatting" and self.chat_session_id == current_session:
                        await self.client.send_message(TARGET_BOT, "/next")
                        logger.info("✅ Retried /next command.")
                return

            # STEP 1: Handle Anti-Bot Verification (CAPTCHA)
            if "Anti-Bot Verification" in message_text or "=" in message_text:
                logger.info("🤖 CAPTCHA detected! Solving math puzzle...")
                await asyncio.sleep(0.5)
                msg = await self.client.get_messages(TARGET_BOT, ids=event.message.id)
                
                match = re.search(r'(\d+)\s*([\+\-\*x×/])\s*(\d+)', message_text)
                if match:
                    n1, op, n2 = match.groups()
                    op = op.replace('x', '*').replace('×', '*')
                    expr = f"{n1} {op} {n2}"
                    try:
                        correct_answer = int(eval(expr))
                        logger.info(f"🧮 Math solved: {expr} = {correct_answer}")
                        
                        if msg and msg.buttons:
                            for row in msg.buttons:
                                for button in row:
                                    if button.text.strip() == str(correct_answer):
                                        await button.click()
                                        logger.info(f"✅ Clicked correct CAPTCHA button: {correct_answer}")
                                        self.state = "searching"
                                        return
                    except Exception as ex:
                        logger.error(f"❌ Error solving captcha math: {ex}")

            # STEP 2: Searching state or successful verification
            if any(word in message_text for word in ["Searching", "searching", "stop to cancel", "Verification Successful"]):
                self.state = "searching"
                logger.info("🔎 Bot is searching for partner...")
                return

            # STEP 3: Partner Found
            elif "Partner found" in message_text or "Start chatting" in message_text:
                self.state = "chatting"
                self.chat_session_id += 1 
                current_session = self.chat_session_id
                
                logger.info("🎯 PARTNER FOUND! Starting promo sequence...")
                
                # Wait before sending promo
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
                if self.state != "chatting" or self.chat_session_id != current_session:
                    return

                promo = generate_random_message()
                await self.client.send_message(TARGET_BOT, promo)
                logger.info("✅ Promo sent!")
                
                # Wait before skipping
                delay = random.uniform(7.0, 10.0)
                logger.info(f"⏳ Waiting {delay:.1f}s before skipping to next...")
                await asyncio.sleep(delay)
                
                if self.state == "chatting" and self.chat_session_id == current_session:
                    await self.client.send_message(TARGET_BOT, "/next")
                    logger.info("✅ Sent /next command.")

            # STEP 4: Partner Ended Chat
            elif any(word in message_text for word in ["Partner ended chat", "Chat ended", "Reopen"]):
                self.state = "idle"
                logger.info("⚠️ Chat ended. Finding a new partner...")
                await self.request_search()

            # STEP 5: Main Menu or Start prompt
            elif "Welcome" in message_text or "choose" in message_text or "/search" in message_text:
                if self.state == "idle":
                    await self.request_search()

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
                    
