# Telegram Promotional Bot - Render Deployment Version (Multi-Target + Sticker Support)
# Requirements: telethon aiohttp

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
SESSION_STRING = os.getenv('SESSION_STRING', '')
PORT = int(os.getenv('PORT', 10000))

# Multiple target bots with individual delay settings - configurable via environment
DEFAULT_TARGET_BOTS = {
    '@AnonyMeetBot': {'min_delay': 5.0, 'max_delay': 12.0},
    '@random_pacar_bot': {'min_delay': 9.0, 'max_delay': 13.0},
}

# Parse TARGET_BOTS from environment variables (Supports both Script 1 JSON and Script 2 Comma-separated formats)
TARGET_BOTS = {}
env_target_bots = os.getenv('TARGET_BOTS', '')
env_target_bot = os.getenv('TARGET_BOT', '') # Script 2 fallback

try:
    if env_target_bots.strip().startswith('{'):
        TARGET_BOTS = json.loads(env_target_bots)
    elif env_target_bots:
        TARGET_BOTS = {bot.strip(): {'min_delay': 5.0, 'max_delay': 12.0} for bot in env_target_bots.split(",")}
        
    if not TARGET_BOTS:
        TARGET_BOTS = DEFAULT_TARGET_BOTS.copy()
except Exception as e:
    logger.warning("⚠️ Invalid TARGET_BOTS format, using defaults")
    TARGET_BOTS = DEFAULT_TARGET_BOTS.copy()

# Ensure Script 2's TARGET_BOT env is also included
if env_target_bot:
    for bot in env_target_bot.split(","):
        bot = bot.strip()
        if bot and bot not in TARGET_BOTS:
            TARGET_BOTS[bot] = {'min_delay': 5.0, 'max_delay': 12.0}

# GLOBALS
message_counters: Dict[str, int] = {}
used_messages: Set[str] = set()
MATCH_KEYWORDS = ["It's a match!", "Jenis kelamin", "Ketertarikan:", "Match found", "A partner has been found!"]

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
    if not message_text:
        return False
    return any(keyword.lower() in message_text.lower() for keyword in MATCH_KEYWORDS)

def get_random_delay(bot_username: str = None) -> float:
    if bot_username and bot_username in TARGET_BOTS:
        bot_config = TARGET_BOTS[bot_username]
        return random.uniform(bot_config['min_delay'], bot_config['max_delay'])
    return random.uniform(5.0, 12.0)

def generate_random_message(bot_username: str) -> str:
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
    return message

def validate_config():
    if not API_ID or not API_HASH:
        logger.error("❌ Missing API_ID or API_HASH")
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
        if SESSION_STRING:
            self.client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        self.target_bot_entities: Dict[str, any] = {}
        self.is_running = True
        self.statistics = BotStatistics()
        self.timeout_tasks: Dict[str, asyncio.Task] = {} 
        
        # Script 2 variables
        self.bot2_next_limit_reached = False

    async def get_stickers(self):
        """Fetches the most recent stickers from Saved Messages dynamically"""
        stickers = []
        try:
            async for message in self.client.iter_messages('me', limit=30):
                if message.sticker:
                    stickers.append(message.document)
                if len(stickers) >= 2: break
        except Exception as e:
            logger.error(f"Error fetching stickers: {e}")
        return stickers

    async def start(self):
        """Start the bot"""
        try:
            if not validate_config():
                raise ValueError("Invalid configuration")

            await self.client.start(phone=PHONE_NUMBER if PHONE_NUMBER else None)
            logger.info("✅ Telegram client started successfully")

            if not SESSION_STRING:
                new_session_string = self.client.session.save()
                logger.info(f"📝 Session string (save this as SESSION_STRING env var): {new_session_string}")

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

            @self.client.on(events.NewMessage(chats=list(self.target_bot_entities.values())))
            async def handle_new_message(event):
                await self.process_message(event)

            logger.info(f"🤖 Started monitoring {len(self.target_bot_entities)} bots...")
            await self.start_health_server()
            await self.client.run_until_disconnected()

        except Exception as e:
            logger.error(f"❌ Failed to start bot: {str(e)}")
            raise

    async def process_message(self, event):
        """Process incoming messages integrating Script 1 and Script 2 logic"""
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

            # ==========================================
            # INTEGRATED SCRIPT 2 LOGIC (Stickers & Limits)
            # ==========================================
            if 'Partner found 😺' in message_text:
                logger.info(f"{sender_bot}: Partner found. Sending sticker...")
                await asyncio.sleep(1) 
                
                stickers = await self.get_stickers()
                if len(stickers) >= 2:
                    await self.client.send_file(event.chat_id, stickers[1])
                elif len(stickers) >= 1:
                    await self.client.send_file(event.chat_id, stickers[0])
                
                await asyncio.sleep(2) 
                if self.bot2_next_limit_reached:
                    await event.respond('/stop')
                else:
                    await event.respond('/next') 
                return # Exit early so Script 1 logic doesn't trigger

            elif any(phrase in message_text for phrase in ['You stopped the chat', 'Your partner has stopped the chat', 'Type /search to find a new partner']):
                logger.info(f"{sender_bot}: Chat ended properly. Searching...")
                await asyncio.sleep(1)
                await event.respond('/search')
                return

            elif "daily /next limit" in message_text:
                logger.info(f"{sender_bot}: Daily limit reached. Switching to /stop mode.")
                self.bot2_next_limit_reached = True
                await asyncio.sleep(1)
                await event.respond('/stop')
                return

            # ==========================================
            # INTEGRATED SCRIPT 1 LOGIC (Promo Text & Timeouts)
            # ==========================================
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

    async def send_promotional_message(self, bot_username: str):
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
        try:
            if bot_username not in self.target_bot_entities:
                return
            self.cancel_timeout_task(bot_username)
            await self.client.send_message(self.target_bot_entities[bot_username], "/next")
            logger.info(f"✅ Sent /next command to {bot_username}")
            
            self.timeout_tasks[bot_username] = asyncio.create_task(
                self.monitor_bot_timeout(bot_username)
            )
        except Exception as e:
            logger.error(f"❌ Failed to send /next to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def monitor_bot_timeout(self, bot_username: str):
        try:
            await asyncio.sleep(60)
            logger.warning(f"⏰ No response from {bot_username} for 60s after /next. Sending /next again...")
            await self.send_next_command(bot_username)
        except asyncio.CancelledError:
            pass

    def cancel_timeout_task(self, bot_username: str):
        task = self.timeout_tasks.get(bot_username)
        if task and not task.done():
            task.cancel()
        self.timeout_tasks[bot_username] = None

    async def start_health_server(self):
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
                'connected_bots': len(self.target_bot_entities)
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

# MAIN ENTRY POINT
async def main():
    print("🚀 Starting Unified Telegram Promotional Bot for Render...")
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

