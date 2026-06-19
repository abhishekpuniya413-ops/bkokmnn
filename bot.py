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

# CONFIGURATION - Use environment variables for security
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
PROMO_BOT = os.getenv('PROMO_BOT', 't.me/InstantTalkBot')
SESSION_NAME = os.getenv('SESSION_NAME', 'onAnonBot')

# Add port for Render (required for web services)
PORT = int(os.getenv('PORT', 10000))

# Multiple target bots with individual delay settings - configurable via environment
# Format: {"@BotName": {"min_delay": 5.0, "max_delay": 12.0}, ...}
DEFAULT_TARGET_BOTS = {
    '@AnonyMeetBot': {'min_delay': 5.0, 'max_delay': 12.0},
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

# GLOBALS
message_counters: Dict[str, int] = {}  # Counter per bot
used_messages: Set[str] = set()
MATCH_KEYWORDS = ["It's a match!", "Jenis kelamin", "Ketertarikan:", "Match found", "A partner has been found!"]

# Expanded fallback templates
FALLBACK_TEMPLATES = [
    "Mau ngobrol sambil main catur atau UNO? Cari aja ІиѕтaиtТаlkBот ♟️🎮",

    "Gabut parah? Mending mabar UNO di ÌñßtâñtTâlkBôt bareng orang random! 🃏",

    "Cari temen ngobrol dari luar negeri? Langsung ke ІnѕtаntTаlkBоt 🌍✨",

    "Main catur sambil curhat santai? Coba aja ΙnѕtаntΤаlkΒοt 😎",

    "Daripada bengong, gas main game gratis di I_n_s_t_a_n_t_T_a_l_k_B_o_t 🎲",

    "Tempatnya orang gabut nyari temen sefrekuensi 🤝 👉 ІñѕтäñтTälkBöт",

    "Bosan chat yang itu-itu aja? Klik ÌnѕtаntTаlkßot ada game serunya! 🎯",

    "Ngobrol anonim tapi bisa sambil main UNO? Cuma di ІnѕтantТаlkBот 🃏🔥",

    "Lagi nyari lawan catur yang seru? Temukan di ÌñstâñtTâlkBôt ♟️",

    "Pengen lancar bahasa Inggris? Cari temen chat global di ІnѕtаntTаlkBоt 🗣️",

    "Chatting anti garing, ada game pendamping 😌 👉 ΙnѕtаntΤаlkΒοt",

    "Scroll mulu kagak nemu jodoh? Coba peruntunganmu di I_n_s_t_a_n_t_T_a_l_k_B_o_t 💀",

    "Bukan sekadar anon chat biasa, cobain sendiri keseruannya ІñѕтäñтTälkBöт ✅",

    "Mabar UNO atau catur gratis tanpa download aplikasi? Ke ÌnѕtаntTаlkßot aja 📱",

    "Nyari temen curhat yang asik dan gak ribet? Langsung ІnѕтantТаlkBот 🙌",

    "Vibes-nya adem, no mesum-mesum club 😤 👉 ÌñßtâñtTâlkBôt",

    "Stress ngerjain tugas? Refreshing bentar di ІnѕtаntTаlkBоt 😭",

    "Chat random tercepat dan paling aman, klik ΙnѕtаntΤаlkΒοt ⚡",

    "Gabut malam-malam? Ada ribuan orang stand by di I_n_s_t_a_n_t_T_a_l_k_B_o_t 🌙",

    "Main game bareng stranger dari mana aja? Cek ІñѕтäñтTälkBöт 👾",

    "Bikin hari gabutmu jadi seru lewat game & chat di ÌnѕtаntTаlkßot 💥",

    "Bebas skip sampai nemu yang beneran cocok! 👉 ІnѕтantТаlkBот 😌",

    "Temen lagi sibuk semua? Cari temen baru di ÌñstâñtTâlkBôt 😏",

    "Komunitas chat random paling asik, buruan gabung ІnѕtаntTаlkBоt 🚀",

    "Mau skip atau lanjut? Kendali penuh di tanganmu 🎮 👉 ΙnѕtаntΤаlkΒοt"
]

# Short promo messages for variety
SHORT_PROMOS = [
    "Anon chat simple & seru 👉 instanttalkb0t"
]

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"⏰ Custom delay for {bot_username}: {delay:.1f}s (range: {min_delay}-{max_delay}s)")
        return delay
    else:
        # Default delay range if bot not found or no bot specified
        default_delay = random.uniform(5.0, 12.0)
        logger.debug(f"⏰ Default delay: {default_delay:.1f}s")
        return default_delay

def generate_random_message(bot_username: str) -> str:
    """Generate a random promotional message"""
    if bot_username not in message_counters:
        message_counters[bot_username] = 0
    message_counters[bot_username] += 1

    # 30% chance for short message, 70% for long message
    if random.random() < 0.3:
        template = random.choice(SHORT_PROMOS)
    else:
        template = random.choice(FALLBACK_TEMPLATES)

    # Format the message
    message = template.format(bot=PROMO_BOT)

    # Add variation to avoid exact duplicates
    message_key = f"{bot_username}:{message}"
    if message_key in used_messages:
        variations = [
            f"{message} ✨",
            f"{message} 🔥",
            f"{message} 💯",
            f"{message} ({message_counters[bot_username]})"
        ]
        message = random.choice(variations)

    used_messages.add(message_key)
    logger.info(f"Generated message #{message_counters[bot_username]} for {bot_username}: {message[:50]}...")
    return message

def validate_config():
    """Validate required environment variables"""
    required_vars = ['API_ID', 'API_HASH', 'PHONE_NUMBER']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
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
        if bot_username in self.stats:
            self.stats[bot_username]['matches'] += 1

    def record_message_sent(self, bot_username: str):
        if bot_username in self.stats:
            self.stats[bot_username]['messages_sent'] += 1

    def record_error(self, bot_username: str):
        if bot_username in self.stats:
            self.stats[bot_username]['errors'] += 1

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
        # Use StringSession for cloud deployment
        from telethon.sessions import StringSession
        session_string = os.getenv('SESSION_STRING', '')
        
        if session_string:
            self.client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        self.target_bot_entities: Dict[str, any] = {}
        self.is_running = True
        self.statistics = BotStatistics()

    async def start(self):
        """Start the bot"""
        try:
            # Validate configuration
            if not validate_config():
                raise ValueError("Invalid configuration")

            await self.client.start(phone=PHONE_NUMBER)
            logger.info("✅ Telegram client started successfully")

            # Print session string for first-time setup
            if not os.getenv('SESSION_STRING'):
                session_string = self.client.session.save()
                logger.info(f"📝 Session string (save this as SESSION_STRING env var): {session_string}")

            # Get all target bot entities
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

            # Set up message handler for all target bots
            @self.client.on(events.NewMessage(chats=list(self.target_bot_entities.values())))
            async def handle_new_message(event):
                await self.process_message(event)

            logger.info(f"🤖 Started monitoring {len(self.target_bot_entities)} bots for matches...")
            logger.info("📋 Monitoring bots:")
            for bot_username in self.target_bot_entities.keys():
                logger.info(f"   - {bot_username}")

            # Start health check server for Render
            await self.start_health_server()

            logger.info("📱 Bot is now running...")

            # Keep the bot running
            await self.client.run_until_disconnected()

        except Exception as e:
            logger.error(f"❌ Failed to start bot: {str(e)}")
            raise

    async def process_message(self, event):
        """Process incoming messages"""
        try:
            message_text = event.message.text or ""
            
            # Find which bot sent this message
            sender_bot = None
            for bot_username, entity in self.target_bot_entities.items():
                if event.chat_id == entity.id:
                    sender_bot = bot_username
                    break

            if not sender_bot:
                return

            logger.debug(f"📨 Received from {sender_bot}: {message_text[:50]}...")

            if is_match_message(message_text):
                logger.info(f"🎯 Match detected from {sender_bot}! Sending promo message...")
                self.statistics.record_match(sender_bot)
                await self.send_promotional_message(sender_bot)

                # Wait before sending /next with bot-specific delay
                delay = get_random_delay(sender_bot)
                logger.info(f"⏳ Waiting {delay:.1f}s before /next to {sender_bot}...")
                await asyncio.sleep(delay)
                await self.send_next_command(sender_bot)

        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            if 'sender_bot' in locals():
                self.statistics.record_error(sender_bot)

    async def send_promotional_message(self, bot_username: str):
        """Send a promotional message to specific bot"""
        try:
            if bot_username not in self.target_bot_entities:
                logger.error(f"❌ Bot {bot_username} not found in entities")
                return

            promo_message = generate_random_message(bot_username)
            await self.client.send_message(self.target_bot_entities[bot_username], promo_message)
            logger.info(f"✅ Promotional message sent to {bot_username}!")
            self.statistics.record_message_sent(bot_username)
        except Exception as e:
            logger.error(f"❌ Failed to send promo message to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def send_next_command(self, bot_username: str):
        """Send /next command to specific bot"""
        try:
            if bot_username not in self.target_bot_entities:
                logger.error(f"❌ Bot {bot_username} not found in entities")
                return

            await self.client.send_message(self.target_bot_entities[bot_username], "/next")
            logger.info(f"✅ Sent /next command to {bot_username}")
        except Exception as e:
            logger.error(f"❌ Failed to send /next to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def start_health_server(self):
        """Start a simple HTTP server for Render health checks with statistics"""
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text='Multi-Target Telegram Bot is running!', status=200)
        
        async def stats_endpoint(request):
            stats = self.statistics.get_stats()
            return web.json_response(stats)
        
        async def config_endpoint(request):
            config_info = {
                'target_bots': list(TARGET_BOTS.keys()),
                'bot_configs': TARGET_BOTS,
                'promo_bot': PROMO_BOT,
                'connected_bots': len(self.target_bot_entities)
            }
            return web.json_response(config_info)
        
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
        logger.info(f"📊 Statistics available at: http://localhost:{PORT}/stats")
        logger.info(f"⚙️ Configuration available at: http://localhost:{PORT}/config")

# MAIN FUNCTION
async def main():
    """Main entry point"""
    print("🚀 Starting Multi-Target Telegram Promotional Bot for Render...")
    print("📋 Configuration:")
    print(f"   Target Bots & Delays:")
    for bot_username, config in TARGET_BOTS.items():
        print(f"     - {bot_username}: {config['min_delay']}-{config['max_delay']}s delay")
    print(f"   Promo Bot: {PROMO_BOT}")
    print(f"   Phone: {PHONE_NUMBER}")
    print(f"   Port: {PORT}")
    print("=" * 50)

    bot = MultiTargetTelegramPromoBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {str(e)}")
        # Keep the process alive for debugging
        await asyncio.sleep(60)
    finally:
        try:
            await bot.client.disconnect()
            logger.info("🔌 Bot disconnected cleanly")
        except:
            pass

# RUN THE BOT
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        # Keep alive for debugging
        time.sleep(60)
