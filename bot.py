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

# Add port for Render (required for web services)
PORT = int(os.getenv('PORT', 10000))

# GLOBALS
message_counter = 0
used_messages: Set[str] = set()

# Extensive emoji list to ensure uniqueness
EMOJI_LIST = [
    "✨", "🔥", "💯", "🎯", "🚀", "💡", "🌟", "💫", "⚡️", "🎉", 
    "🎊", "🎈", "😎", "🤩", "✌️", "👌", "👍", "🙌", "👋", "👀", 
    "💥", "🪐", "🌈", "☀️", "💎", "🔮", "🪄", "💌", "💣", "🧸",
    "🧊", "🎲", "🧩", "🎭", "🎨", "🎬", "🎤", "🎧", "🎷", "🎸",
    "🛸", "🚁", "⛵️", "🏝", "🌋", "🏕", "🎡", "🎢", "🎠", "⛲️"
]

MATCH_KEYWORDS = [
    "شروع شد! بهش سلام کن", 
    "شروع شد!", 
    "چت با",
    "بهش سلام کن"
]

FALLBACK_TEMPLATES = [
    "حوصلت سر رفته؟ 🥹\nبا {bot} با آدمای جدید و تصادفی آشنا شو 👇🏻\nفقط اسمشو توی سرچ تلگرام بزن",
    "دنبال یه چت ناشناس باحال‌تر می‌گردی؟ 😎\nربات {bot} رو امتحان کن!\nکلی آدم جدید اونجان منتظر تو\n\nآیدی: {bot}",
    "اینجا خلوته؟ 🥲\nبیا تو {bot}، پر از آدمای آنلاینه که می‌تونی باهاشون چت کنی 💬\nسرچ کن {bot}",
    "می‌خوای با آدمای جدید و باحال آشنا بشی؟ 🤩\nربات {bot} بهترین جاست برای چت ناشناس!\nهمین الان تو تلگرام سرچش کن",
    "چت ناشناس بدون قطعی و سریع می‌خوای؟ 🚀\nفقط {bot}!\nآیدی بات رو سرچ کن و استارت بزن 👇🏻\n{bot}",
    "محیط امن و خفن برای پیدا کردن دوستای جدید 😍\nهمین الان بیا تو {bot} و شانستو امتحان کن!\n\nسرچ کن: {bot}",
    "خسته شدی از ربات‌های تکراری؟ 🥱\nیه سر به {bot} بزن، سرعتش عالیه و کلی کاربر داره\n\nآیدی ربات: {bot}"
]

SHORT_PROMOS = [
    "بیا {bot} چت کنیم، اینجا خسته کننده‌س 🥱",
    "بهترین ربات چت ناشناس الان {bot} هست، حتما امتحانش کن",
    "حوصلت سر رفته؟ بیا {bot} کلی آدم آنلاین داره",
    "ربات {bot} خیلی سریع‌تر و بهتره، سرچش کن",
    "دوستای جدید پیدا کن تو {bot} 👇🏻",
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

def get_random_delay() -> float:
    """Get random delay between 5-12 seconds"""
    return random.uniform(5.0, 12.0)

def generate_random_message() -> str:
    """Generate a random promotional message with random emojis appended every time"""
    global message_counter
    message_counter += 1

    # 30% chance for short message, 70% for long message
    if random.random() < 0.3:
        template = random.choice(SHORT_PROMOS)
    else:
        template = random.choice(FALLBACK_TEMPLATES)

    # Format the base message
    base_message = template.format(bot=PROMO_BOT)

    # Pick 2-3 random emojis to append every single time to ensure variation
    random_emojis = "".join(random.sample(EMOJI_LIST, k=random.randint(2, 3)))
    
    # Construct final message
    message = f"{base_message} {random_emojis}"

    # Absolute fallback to prevent duplicate API errors if the exact combo is rolled twice
    if message in used_messages:
        message = f"{message} ({message_counter})"

    used_messages.add(message)
    logger.info(f"Generated message #{message_counter}: {message[:50]}...")
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

# MAIN BOT CLASS
class TelegramPromoBot:
    def __init__(self):
        # Use StringSession for cloud deployment
        from telethon.sessions import StringSession
        session_string = os.getenv('SESSION_STRING', '')
        
        if session_string:
            self.client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        self.target_bot_entity = None
        self.is_running = True

    async def start(self):
        """Start the bot"""
        try:
            # Validate configuration
            if not validate_config():
                raise ValueError("Invalid configuration")

            await self.client.start(phone=PHONE_NUMBER)
            logger.info("✅ Telegram client started successfully")

            # Print session string for first-time setup
            session_string = self.client.session.save()
            logger.info(f"📝 Session string (save this as SESSION_STRING env var): {session_string}")

            # Get target bot entity
            self.target_bot_entity = await self.client.get_entity(TARGET_BOT)
            logger.info(f"✅ Found target bot: {TARGET_BOT}")

            # Set up message handler
            @self.client.on(events.NewMessage(chats=self.target_bot_entity))
            async def handle_new_message(event):
                await self.process_message(event)

            logger.info(f"🤖 Started monitoring {TARGET_BOT} for matches...")
            logger.info("📱 Bot is now running...")

            # Start health check server for Render
            await self.start_health_server()

            # Keep the bot running
            await self.client.run_until_disconnected()

        except Exception as e:
            logger.error(f"❌ Failed to start bot: {str(e)}")
            raise

    async def process_message(self, event):
        """Process incoming messages"""
        try:
            message_text = event.message.text or ""
            logger.debug(f"📨 Received: {message_text[:50]}...")

            if is_match_message(message_text):
                logger.info("🎯 Match detected! Sending promo message...")
                
                # Small human-like delay before sending
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await self.send_promotional_message()

                # Wait before skipping to next
                delay = get_random_delay()
                logger.info(f"⏳ Waiting {delay:.1f}s before skipping to next...")
                await asyncio.sleep(delay)
                await self.send_next_command()

        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")

    async def send_promotional_message(self):
        """Send a promotional message"""
        try:
            promo_message = generate_random_message()
            await self.client.send_message(self.target_bot_entity, promo_message)
            logger.info("✅ Promotional message sent!")
        except Exception as e:
            logger.error(f"❌ Failed to send promo message: {str(e)}")

    async def send_next_command(self):
        """Send exact button texts to skip to the next user"""
        try:
            # Click "End Chat" button
            await self.client.send_message(self.target_bot_entity, "🔚 پایان چت")
            logger.info("✅ Sent 'End Chat' command")
            
            await asyncio.sleep(1.5)
            
            # Click "Random Search" button
            await self.client.send_message(self.target_bot_entity, "🎲 جستجوی شانسی")
            logger.info("✅ Sent 'Random Search' command")
        except Exception as e:
            logger.error(f"❌ Failed to skip to next: {str(e)}")

    async def start_health_server(self):
        """Start a simple HTTP server for Render health checks"""
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text='Bot is running!', status=200)
        
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logger.info(f"🌐 Health server started on port {PORT}")

# MAIN FUNCTION
async def main():
    """Main entry point"""
    print("🚀 Starting Telegram Promotional Bot for Render...")
    print("📋 Configuration:")
    print(f"   Target Bot: {TARGET_BOT}")
    print(f"   Promo Bot: {PROMO_BOT}")
    print(f"   Phone: {PHONE_NUMBER}")
    print(f"   Port: {PORT}")
    print("=" * 50)

    bot = TelegramPromoBot()

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
