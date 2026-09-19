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

# Bot 2: Mutual Anonymous Chat target bots (comma-separated via TARGET_BOT env var)
BOT2_TARGET_BOTS = [bot.strip() for bot in os.getenv('TARGET_BOT', '').split(',') if bot.strip()]

# GLOBALS
message_counters: Dict[str, int] = {}  # Counter per bot
used_messages: Set[str] = set()
MATCH_KEYWORDS = [
    "It's a match!",
    "Jenis kelamin",
    "Ketertarikan:",
    "Pasangan telah ditemukan!",
    "Match found",
    "A partner has been found!"
]

# Expanded fallback templates
FALLBACK_TEMPLATES = [
"Cari InstantTalkBot di Telegram buat ngobrol random sambil main catur atau UNO ♟️🎮",
"Gabut parah? Cari InstantTalkBot di Telegram dan mabar UNO bareng orang random! 🃏",
"Cari temen ngobrol dari luar negeri? Cari InstantTalkBot di Telegram 🌍✨",
"Main catur sambil curhat santai? Cari InstantTalkBot di Telegram 😎",
"Daripada bengong, cari InstantTalkBot di Telegram dan main game gratis 🎲",
"Lagi nyari temen ngobrol yang nyambung? Cari InstantTalkBot di Telegram 🤝",
"Bosan chat yang itu-itu aja? Cari InstantTalkBot di Telegram, ada game serunya! 🎯",
"Ngobrol anonim tapi bisa sambil main UNO? Cari InstantTalkBot di Telegram 🃏🔥",
"Lagi nyari lawan catur yang seru? Cari InstantTalkBot di Telegram ♟️",
"Pengen lancar bahasa Inggris? Cari temen chat global di InstantTalkBot lewat Telegram 🗣️",
"Chatting anti garing? Cari InstantTalkBot di Telegram 😌",
"Scroll mulu? Cari InstantTalkBot di Telegram dan kenalan sama orang baru 💀",
"Bukan sekadar anon chat biasa, cari InstantTalkBot di Telegram dan rasain sendiri keseruannya ✅",
"Mabar UNO atau catur gratis tanpa download aplikasi? Cari InstantTalkBot di Telegram 📱",
"Nyari temen curhat yang asik dan gak ribet? Cari InstantTalkBot di Telegram 🙌",
"Vibes-nya adem, no mesum-mesum club 😤 Cari InstantTalkBot di Telegram",
"Stress ngerjain tugas? Refreshing bentar, cari InstantTalkBot di Telegram 😭",
"Chat random cepat dan aman? Cari InstantTalkBot di Telegram ⚡",
"Gabut malam-malam? Cari InstantTalkBot di Telegram, selalu ada yang online 🌙",
"Main game bareng stranger dari mana aja? Cari InstantTalkBot di Telegram 👾",
"Bikin hari gabutmu jadi seru lewat game & chat di InstantTalkBot 💥",
"Bebas skip sampai nemu yang beneran cocok! Cari InstantTalkBot di Telegram 😌",
"Temen lagi sibuk semua? Cari temen baru di InstantTalkBot lewat Telegram 😏",
"Komunitas chat random paling asik, cari InstantTalkBot di Telegram 🚀",
"Mau skip atau lanjut? Kendali penuh di tanganmu 🎮 Cari InstantTalkBot di Telegram"
]

SHORT_PROMOS = [
    "Anon chat simple & seru 👉 instanttalkb0t"
]

# UTILITY FUNCTIONS
def is_match_message(message_text: str) -> bool:
    """Check if message indicates a match"""
    if not message_text:
        return False
    return any(keyword.lower() in message_text.lower() for keyword in MATCH_KEYWORDS)

def get_random_delay(bot_username: str = None) -> float:
    """Get random delay based on bot-specific settings or default range"""
    if bot_username and bot_username in TARGET_BOTS:
        bot_config = TARGET_BOTS[bot_username]
        min_delay = bot_config['min_delay']
        max_delay = bot_config['max_delay']
        return random.uniform(min_delay, max_delay)
    return random.uniform(5.0, 12.0)

def generate_random_message(bot_username: str) -> str:
    """Generate a random promotional message"""
    if bot_username not in message_counters:
        message_counters[bot_username] = 0
    message_counters[bot_username] += 1

    if random.random() < 0.3:
        template = random.choice(SHORT_PROMOS)
    else:
        template = random.choice(FALLBACK_TEMPLATES)

    message = template.format(bot=PROMO_BOT)
    message_key = f"{bot_username}:{message}"
    
    if message_key in used_messages:
        variations = [
            f"{message} ✨", f"{message} 🔥", f"{message} 💯", f"{message} ({message_counters[bot_username]})"
        ]
        message = random.choice(variations)

    used_messages.add(message_key)
    logger.info(f"Generated message #{message_counters[bot_username]} for {bot_username}: {message[:50]}...")
    return message

def validate_config():
    """Validate required environment variables"""
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
        self.is_running = True
        self.statistics = BotStatistics()
        self.timeout_tasks: Dict[str, asyncio.Task] = {}  # Tracks individual bot 60s timeout tasks

        # Bot 2 state
        self.bot2_next_limit_reached = False

    async def start(self):
        """Start the bot"""
        try:
            if not validate_config():
                raise ValueError("Invalid configuration")

            await self.client.start(phone=PHONE_NUMBER)
            logger.info("✅ Telegram client started successfully")

            if not os.getenv('SESSION_STRING'):
                session_string = self.client.session.save()
                logger.info(f"📝 Session string (save this as SESSION_STRING env var): {session_string}")

            for bot_username in TARGET_BOTS.keys():
                try:
                    entity = await self.client.get_entity(bot_username)
                    self.target_bot_entities[bot_username] = entity
                    logger.info(f"✅ Found target bot: {bot_username}")
                except Exception as e:
                    logger.error(f"❌ Failed to find bot {bot_username}: {str(e)}")
                    continue

            if not self.target_bot_entities:
                logger.error("❌ No target bots found! Exiting...")
                return

            # Handler for Bot 1 (promo bots)
            @self.client.on(events.NewMessage(chats=list(self.target_bot_entities.values())))
            async def handle_new_message(event):
                await self.process_message(event)

            # Handler for Bot 2 (Mutual Anonymous Chat) — only registered if targets are configured
            if BOT2_TARGET_BOTS:
                logger.info(f"🤖 Bot 2 targets: {BOT2_TARGET_BOTS}")

                @self.client.on(events.NewMessage(chats=BOT2_TARGET_BOTS))
                async def handle_bot2_message(event):
                    await self.process_bot2_message(event)
            else:
                logger.info("ℹ️ No TARGET_BOT env var set — Bot 2 handler skipped")

            logger.info(f"🤖 Started monitoring {len(self.target_bot_entities)} bots for matches...")
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

            if not sender_bot:
                return

            # Cancel timeout watcher because the target bot actively sent a message
            self.cancel_timeout_task(sender_bot)

            logger.debug(f"📨 Received from {sender_bot}: {message_text[:50]}...")

            if is_match_message(message_text):
                logger.info(f"🎯 Match detected from {sender_bot}! Sending promo message...")
                self.statistics.record_match(sender_bot)
                await self.send_promotional_message(sender_bot)

                delay = get_random_delay(sender_bot)
                logger.info(f"⏳ Waiting {delay:.1f}s before /next to {sender_bot}...")
                await asyncio.sleep(delay)
                await self.send_next_command(sender_bot)

        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            if 'sender_bot' in locals() and sender_bot:
                self.statistics.record_error(sender_bot)

    async def process_bot2_message(self, event):
        """Process incoming messages from Bot 2 (Mutual Anonymous Chat) targets"""
        try:
            text = event.raw_text

            if 'Partner found 😺' in text:
                logger.info("Bot 2: Partner found.")
                await asyncio.sleep(1)

                stickers = await self.get_stickers()
                # Use sticker index 1 for Bot 2
                if len(stickers) >= 2:
                    await self.client.send_file(event.chat_id, stickers[1])
                elif len(stickers) >= 1:
                    await self.client.send_file(event.chat_id, stickers[0])

                await asyncio.sleep(2)
                if self.bot2_next_limit_reached:
                    await event.respond('/stop')
                else:
                    await event.respond('/next')

            elif any(phrase in text for phrase in [
                'You stopped the chat',
                'Your partner has stopped the chat',
                'Type /search to find a new partner'
            ]):
                logger.info("Bot 2: Chat ended properly. Searching...")
                await asyncio.sleep(1)
                await event.respond('/search')

            elif "daily /next limit" in text:
                self.bot2_next_limit_reached = True
                await asyncio.sleep(1)
                await event.respond('/stop')

        except Exception as e:
            logger.error(f"❌ Bot 2 error processing message: {str(e)}")

    async def get_stickers(self):
        """Fetch stickers from saved messages (Bot 2 helper)"""
        stickers = []
        try:
            async for message in self.client.iter_messages('me', limit=30):
                if message.sticker:
                    stickers.append(message.document)
                if len(stickers) >= 2:
                    break
        except Exception as e:
            logger.error(f"Error fetching stickers: {e}")
        return stickers

    async def send_promotional_message(self, bot_username: str):
        """Send a promotional message to specific bot"""
        try:
            if bot_username not in self.target_bot_entities:
                return
            promo_message = generate_random_message(bot_username)
            await self.client.send_message(self.target_bot_entities[bot_username], promo_message)
            logger.info(f"✅ Promotional message sent to {bot_username}!")
            self.statistics.record_message_sent(bot_username)
        except Exception as e:
            logger.error(f"❌ Failed to send promo message to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def send_next_command(self, bot_username: str):
        """Send /next command to specific bot and start response guard"""
        try:
            if bot_username not in self.target_bot_entities:
                return

            # Ensure any previous tracking task is cleared before executing next action
            self.cancel_timeout_task(bot_username)

            await self.client.send_message(self.target_bot_entities[bot_username], "/next")
            logger.info(f"✅ Sent /next command to {bot_username}")

            # Fire up a 60-second response monitor task
            self.timeout_tasks[bot_username] = asyncio.create_task(
                self.monitor_bot_timeout(bot_username)
            )
        except Exception as e:
            logger.error(f"❌ Failed to send /next to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def monitor_bot_timeout(self, bot_username: str):
        """Asynchronously waits 60 seconds; triggers retry if target bot goes silent"""
        try:
            await asyncio.sleep(60)
            logger.warning(f"⏰ No response from {bot_username} for 60s after /next. Sending /next again...")
            await self.send_next_command(bot_username)
        except asyncio.CancelledError:
            # Task was cleared cleanly because the bot responded in time
            pass

    def cancel_timeout_task(self, bot_username: str):
        """Safely stops and discards a running timeout watcher"""
        task = self.timeout_tasks.get(bot_username)
        if task and not task.done():
            task.cancel()
        self.timeout_tasks[bot_username] = None

    async def start_health_server(self):
        """Start a simple HTTP server for Render health checks with statistics"""
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text='Multi-Target Telegram Bot is running!', status=200)
        
        async def stats_endpoint(request):
            return web.json_response(self.statistics.get_stats())
        
        async def config_endpoint(request):
            return web.json_response({
                'target_bots': list(TARGET_BOTS.keys()),
                'bot_configs': TARGET_BOTS,
                'promo_bot': PROMO_BOT,
                'connected_bots': len(self.target_bot_entities),
                'bot2_targets': BOT2_TARGET_BOTS,
                'bot2_next_limit_reached': self.bot2_next_limit_reached,
            })
        
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/stats', stats_endpoint)
        app.router.add_get('/config', config_endpoint)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logger.info(f"🌐 Health server started on port {PORT}")

# MAIN FUNCTION
async def main():
    print("🚀 Starting Multi-Target Telegram Promotional Bot for Render...")
    print("=" * 50)
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
            logger.info("🔌 Bot disconnected cleanly")
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(60)
