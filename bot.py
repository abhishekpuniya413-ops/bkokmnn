# Telegram Promotional Bot - Unified Version
import asyncio
import json
import logging
import os
import random
import time
from typing import Set, Dict
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# CONFIGURATION
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
PROMO_BOT = os.getenv('PROMO_BOT', 't.me/InstantTalkBot')
SESSION_NAME = os.getenv('SESSION_NAME', 'onAnonBot')
SESSION_STRING = os.getenv('SESSION_STRING', '')
PORT = int(os.getenv('PORT', 10000))

# TARGET BOTS SETUP
TARGET_BOTS = {}
env_targets = os.getenv('TARGET_BOTS', '')
if env_targets:
    for bot in env_targets.split(","):
        TARGET_BOTS[bot.strip()] = {'min_delay': 5.0, 'max_delay': 12.0}

MATCH_KEYWORDS = ["It's a match!", "Jenis kelamin", "Ketertarikan:", "Match found", "A partner has been found!"]

# UTILITY FUNCTIONS
def is_match_message(message_text: str) -> bool:
    return any(keyword.lower() in message_text.lower() for keyword in MATCH_KEYWORDS)

def generate_random_message(bot_username: str) -> str:
    templates = ["Cari InstantTalkBot di Telegram buat ngobrol random ♟️", "Gabut? Cari InstantTalkBot di Telegram 🃏"]
    return random.choice(templates).format(bot=PROMO_BOT)

# BOT CLASS
class MultiTargetTelegramPromoBot:
    def __init__(self):
        self.client = TelegramClient(StringSession(SESSION_STRING) if SESSION_STRING else SESSION_NAME, API_ID, API_HASH)
        self.target_bot_entities: Dict[str, any] = {}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self.cached_stickers = []
        self.bot2_next_limit_reached = False

    async def load_stickers(self):
        async for message in self.client.iter_messages('me', limit=30):
            if message.sticker:
                self.cached_stickers.append(message.document)
            if len(self.cached_stickers) >= 2: break

    async def start(self):
        await self.client.start(phone=PHONE_NUMBER if PHONE_NUMBER else None)
        await self.load_stickers()
        
        for bot_username in TARGET_BOTS.keys():
            try:
                self.target_bot_entities[bot_username] = await self.client.get_entity(bot_username)
            except Exception as e:
                logger.error(f"Failed to find {bot_username}: {e}")

        @self.client.on(events.NewMessage(chats=list(self.target_bot_entities.values())))
        async def handle_new_message(event):
            await self.process_message(event)
            
        await self.start_health_server()
        await self.client.run_until_disconnected()

    async def process_message(self, event):
        """Correctly indented process_message function"""
        try:
            message_text = event.message.text or ""
            sender_bot = next((name for name, ent in self.target_bot_entities.items() if event.chat_id == ent.id), None)
            
            if not sender_bot: return

            # --- PRIORITY 1: STICKER BOT (Mutual Bot) ---
            if 'Partner found' in message_text:
                logger.info(f"🚨 Sticker Task for {sender_bot}")
                if self.cached_stickers:
                    await self.client.send_file(event.chat_id, self.cached_stickers[0])
                await asyncio.sleep(2)
                await event.respond('/stop' if self.bot2_next_limit_reached else '/next')
                return

            # --- PRIORITY 2: PROMO BOT ---
            if is_match_message(message_text):
                await self.client.send_message(event.chat_id, generate_random_message(sender_bot))
                await asyncio.sleep(8)
                await self.client.send_message(event.chat_id, "/next")
                
        except Exception as e:
            logger.error(f"Error: {e}")

    async def start_health_server(self):
        from aiohttp import web
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text='Running'))
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, '0.0.0.0', PORT).start()

if __name__ == "__main__":
    bot = MultiTargetTelegramPromoBot()
    asyncio.run(bot.start())
