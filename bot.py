# Telegram Promotional Bot - Render Deployment Version (Multi-Target)
# Requirements: telethon aiohttp

import asyncio
import json
import logging
import os
import random
import time
from typing import Set, Dict
from telethon import TelegramClient, events

# LOGGING (Configured early to prevent startup parsing errors)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CONFIGURATION - Use environment variables for security
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
PROMO_BOT = os.getenv('PROMO_BOT', 't.me/InstantTalkBot')
SESSION_NAME = os.getenv('SESSION_NAME', 'onAnonBot')

# Add port for Render (required for web services)
PORT = int(os.getenv('PORT', 10000))

# Multiple target bots with individual delay settings - configurable via environment
DEFAULT_TARGET_BOTS = {
    '@chatus': {'min_delay': 2.0, 'max_delay': 2.0},
    '': {'min_delay': 5.0, 'max_delay': 12.0},
    '@random_pacar_bot': {'min_delay': 9.0, 'max_delay': 13.0},
}

# Parse TARGET_BOTS from environment variable or use default
try:
    TARGET_BOTS = json.loads(os.getenv('TARGET_BOTS', '{}'))
    if not TARGET_BOTS:
        TARGET_BOTS = DEFAULT_TARGET_BOTS
except (json.JSONDecodeError, TypeError):
    logger.warning("⚠️ Invalid TARGET_BOTS format, using defaults")
    TARGET_BOTS = DEFAULT_TARGET_BOTS

# Bot 2: Target bots (e.g. @TasterChatBot, comma-separated via TARGET_BOT env var)
TARGET_BOT_ENV = os.getenv('TARGET_BOT', '@TasterChatBot')
BOT2_TARGET_BOTS = [bot.strip() for bot in TARGET_BOT_ENV.split(',') if bot.strip()]

# GLOBALS
message_counters: Dict[str, int] = {}  # Counter per bot
used_messages: Set[str] = set()

# Primary Match Indicators for Bot 1
MATCH_KEYWORDS = [
    "Нашёл собеседника!",
    "💎 PREMIUM Собеседник!",
    "It's a match!",
    "Jenis kelamin",
    "Ketertarikan:",
    "Pasangan telah ditemukan!",
    "Match found",
    "A partner has been found!"
]

# Only trigger on partner disconnects for Bot 1
DISCONNECT_KEYWORDS = [
    "Собеседник завершил",
    "Your partner has stopped"
]

FALLBACK_TEMPLATES = [
"Cari InstantTalkBot di Telegram buat ngobrol random sambil main catur atau UNO ♟️🎮",
"Gabut parah? Cari InstantTalkBot di Telegram dan mabar UNO bareng orang random! 🃏",
"Cari temen ngobrol dari luar negeri? Cari InstantTalkBot di Telegram 🌍✨",
"Main catur sambil curhat santai? Cari InstantTalkBot di Telegram 😎",
"Daripada bengong, cari InstantTalkBot di Telegram dan main game gratis 🎲",
"Lagi nyari temen ngobrol yang nyambung? Cari InstantTalkBot di Telegram 🤝",
"Bosan chat yang itu-itu aja? Cari InstantTalkBot di Telegram, ada game serunya! 🎯"
]

SHORT_PROMOS = [
    "Anon chat simple & seru 👉 instanttalkb0t"
]

# UTILITY FUNCTIONS
def is_match_message(message_text: str) -> bool:
    if not message_text:
        return False
    text_lower = message_text.lower()
    for keyword in MATCH_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    if "комната:" in text_lower and ("собеседник" in text_lower or "реакции:" in text_lower or "match" in text_lower):
        return True
    return False

def generate_random_message(bot_username: str) -> str:
    if bot_username == '@chatus':
        return "@ gta347943"
    if bot_username not in message_counters:
        message_counters[bot_username] = 0
    message_counters[bot_username] += 1

    template = random.choice(SHORT_PROMOS) if random.random() < 0.3 else random.choice(FALLBACK_TEMPLATES)
    message = template.format(bot=PROMO_BOT)
    message_key = f"{bot_username}:{message}"
    
    if message_key in used_messages:
        variations = [f"{message} ✨", f"{message} 🔥", f"{message} 💯", f"{message} ({message_counters[bot_username]})"]
        message = random.choice(variations)

    used_messages.add(message_key)
    return message

def validate_config():
    required_vars = ['API_ID', 'API_HASH', 'PHONE_NUMBER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    if API_ID == 0:
        logger.error("❌ API_ID must be a valid integer")
        return False
    return True

# STATISTICS CLASS
class BotStatistics:
    def __init__(self):
        self.stats = {bot: {'matches': 0, 'messages_sent': 0, 'errors': 0} for bot in TARGET_BOTS.keys()}
        self.start_time = time.time()

    def record_match(self, bot_username: str):
        if bot_username in self.stats: self.stats[bot_username]['matches'] += 1

    def record_message_sent(self, bot_username: str):
        if bot_username in self.stats: self.stats[bot_username]['messages_sent'] += 1

    def record_error(self, bot_username: str):
        if bot_username in self.stats: self.stats[bot_username]['errors'] += 1

    def get_stats(self):
        uptime = time.time() - self.start_time
        return {
            'uptime_hours': round(uptime / 3600, 2),
            'bot_stats': self.stats,
            'total_matches': sum(bot['matches'] for bot in self.stats.values()),
            'total_messages': sum(bot['messages_sent'] for bot in self.stats.values()),
            'total_errors': sum(bot['errors'] for bot in self.stats.values())
        }

# MAIN BOT CLASS
class MultiTargetTelegramPromoBot:
    def __init__(self):
        from telethon.sessions import StringSession
        session_string = os.getenv('SESSION_STRING', '')
        
        if session_string:
            self.client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        self.target_bot_entities: Dict[str, any] = {}
        self.bot2_entities = []
        self.is_running = True
        self.statistics = BotStatistics()
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self.chat_states: Dict[str, str] = {}
        self.bot2_next_limit_reached = False

    async def start(self):
        try:
            if not validate_config():
                raise ValueError("Invalid configuration")

            await self.client.start(phone=PHONE_NUMBER)
            logger.info("✅ Telegram client started successfully")

            if not os.getenv('SESSION_STRING'):
                session_string = self.client.session.save()
                logger.info(f"📝 Session string (save this as SESSION_STRING env var): {session_string}")

            # Resolve Bot 1 Targets
            for bot_username in TARGET_BOTS.keys():
                if not bot_username: continue
                try:
                    entity = await self.client.get_entity(bot_username)
                    self.target_bot_entities[bot_username] = entity
                except Exception as e:
                    logger.error(f"❌ Failed to find bot {bot_username}: {str(e)}")

            if self.target_bot_entities:
                @self.client.on(events.NewMessage(chats=list(self.target_bot_entities.values())))
                async def handle_new_message(event):
                    await self.process_message(event)

            # Resolve Bot 2 Targets (Crucial fix: Resolving @TasterChatBot before listening)
            if BOT2_TARGET_BOTS:
                for b in BOT2_TARGET_BOTS:
                    if not b: continue
                    try:
                        ent = await self.client.get_entity(b)
                        self.bot2_entities.append(ent)
                        logger.info(f"✅ Found Bot 2 target: {b}")
                    except Exception as e:
                        logger.error(f"❌ Failed to find Bot 2 target {b}: {e}")

                if self.bot2_entities:
                    @self.client.on(events.NewMessage(chats=self.bot2_entities))
                    async def handle_bot2_message(event):
                        await self.process_bot2_message(event)
            else:
                logger.info("ℹ️ No TARGET_BOT env var set — Bot 2 handler skipped")

            logger.info("🤖 Started monitoring bots for matches...")
            await self.start_health_server()
            await self.client.run_until_disconnected()

        except Exception as e:
            logger.error(f"❌ Failed to start bot: {str(e)}")
            raise

    async def process_message(self, event):
        """Process incoming messages from Bot 1 targets"""
        try:
            message_text = event.message.text or ""
            sender_bot = None
            for bot_username, entity in self.target_bot_entities.items():
                if event.chat_id == entity.id:
                    sender_bot = bot_username
                    break

            if not sender_bot: return
            if sender_bot not in self.chat_states:
                self.chat_states[sender_bot] = 'SEARCHING'

            if is_match_message(message_text):
                if self.chat_states[sender_bot] == 'MATCHED': return
                self.cancel_timeout_task(sender_bot)
                self.chat_states[sender_bot] = 'MATCHED'
                self.statistics.record_match(sender_bot)
                
                await asyncio.sleep(0.1)
                if self.chat_states[sender_bot] == 'MATCHED':
                    await self.send_promotional_message(sender_bot)
                    await asyncio.sleep(2.0)
                    if self.chat_states[sender_bot] == 'MATCHED':
                        self.chat_states[sender_bot] = 'SEARCHING'
                        await self.send_next_command(sender_bot)

            elif any(keyword.lower() in message_text.lower() for keyword in DISCONNECT_KEYWORDS):
                if self.chat_states[sender_bot] == 'SEARCHING': return
                self.cancel_timeout_task(sender_bot)
                self.chat_states[sender_bot] = 'SEARCHING'
                await self.send_next_command(sender_bot)
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")

    async def process_bot2_message(self, event):
        """Process incoming messages from Bot 2 / @TasterChatBot targets"""
        try:
            # Force string to lowercase for bulletproof matching
            text = (event.raw_text or "").lower()

            if 'partner found' in text or 'ми знайшли вам когось' in text:
                logger.info("Bot 2 / TasterChatBot: Match found! Fetching most recent sticker...")
                await asyncio.sleep(1)

                sticker = await self.get_latest_sticker()
                if sticker:
                    await self.client.send_file(event.chat_id, sticker)
                    logger.info("✅ Sent the most recent sticker from Saved Messages!")
                else:
                    logger.warning("⚠️ No sticker found in Saved Messages!")

                await asyncio.sleep(2)
                if self.bot2_next_limit_reached:
                    await event.respond('/stop')
                else:
                    if 'ми знайшли вам когось' in text:
                        # Send exact menu text command to skip to next chat
                        await event.respond('🔎 | шукати далі')
                        logger.info("✅ Skipped to next partner (Sent '🔎 | шукати далі')")
                    else:
                        await event.respond('/next')

            elif any(phrase in text for phrase in [
                'you stopped the chat',
                'your partner has stopped the chat',
                'type /search to find a new partner',
                'діалог буде завершено',
                'шукати наступного',
                'співрозмовник завершив',
                'діалог завершено'
            ]):
                logger.info("Bot 2 / TasterChatBot: Dialogue ended. Starting new search...")
                await asyncio.sleep(1)
                if any(k in text for k in ['діалог', 'шукати', 'співрозмовник']):
                    # When partner disconnects early, the bot provides a reply keyboard. 
                    await event.respond('Так, шукати далі')
                    logger.info("✅ Pressed 'Так, шукати далі' on reply keyboard.")
                else:
                    await event.respond('/search')

            elif "daily /next limit" in text:
                self.bot2_next_limit_reached = True
                await asyncio.sleep(1)
                await event.respond('/stop')

        except Exception as e:
            logger.error(f"❌ Bot 2 / TasterChatBot error processing message: {str(e)}")

    async def get_latest_sticker(self):
        """Fetch the single most recent sticker saved in Saved Messages ('me')"""
        try:
            async for message in self.client.iter_messages('me', limit=50):
                if message.sticker:
                    return message.media
        except Exception as e:
            logger.error(f"Error fetching latest sticker from Saved Messages: {e}")
        return None

    async def send_promotional_message(self, bot_username: str):
        try:
            if bot_username not in self.target_bot_entities: return
            promo_message = generate_random_message(bot_username)
            await self.client.send_message(self.target_bot_entities[bot_username], promo_message)
            self.statistics.record_message_sent(bot_username)
        except Exception as e:
            logger.error(f"❌ Failed to send promo message to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def send_next_command(self, bot_username: str):
        try:
            if bot_username not in self.target_bot_entities: return
            self.cancel_timeout_task(bot_username)
            await self.client.send_message(self.target_bot_entities[bot_username], "/next")
            self.timeout_tasks[bot_username] = asyncio.create_task(self.monitor_bot_timeout(bot_username))
        except Exception as e:
            logger.error(f"❌ Failed to send /next to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def monitor_bot_timeout(self, bot_username: str):
        try:
            while True:
                await asyncio.sleep(25)
                await self.client.send_message(self.target_bot_entities[bot_username], "/next")
        except asyncio.CancelledError:
            pass

    def cancel_timeout_task(self, bot_username: str):
        task = self.timeout_tasks.get(bot_username)
        if task and not task.done() and task != asyncio.current_task():
            task.cancel()
        self.timeout_tasks[bot_username] = None

    async def start_health_server(self):
        from aiohttp import web
        async def health_check(request):
            return web.Response(text='Multi-Target Telegram Bot is running!', status=200)
        async def stats_endpoint(request):
            return web.json_response(self.statistics.get_stats())
        
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/stats', stats_endpoint)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logger.info(f"🌐 Health server started on port {PORT}")

# MAIN FUNCTION
async def main():
    print("🚀 Starting Multi-Target Telegram Promotional Bot for Render...")
    bot = MultiTargetTelegramPromoBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {str(e)}")
        await asyncio.sleep(60)
    finally:
        try:
            await bot.client.disconnect()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
