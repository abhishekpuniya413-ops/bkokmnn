# Telegram Promotional Bot - Render Deployment Version (Multi-Target)
# Requirements: telethon aiohttp

import asyncio
import json
import logging
import os
import random
import time
from typing import Set, Dict
from telethon import TelegramClient, events, functions

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

# Bot 2: Mutual Anonymous Chat target bots (comma-separated via TARGET_BOT env var)
BOT2_TARGET_BOTS = [bot.strip() for bot in os.getenv('TARGET_BOT', '').split(',') if bot.strip()]

# Special target: Anonity anonymous-chat bot
ANONITY_BOT = '@AnonityChatBot'
ANONITY_MATCH_PHRASE = 'Partner found 😺'
ANONITY_SEARCH_COMMAND = '/search'
ANONITY_NEXT_COMMAND = '/next'
ANONITY_STOP_PHRASE = 'Type /search to find a new partner'
ANONITY_PROMO_TEXT = 'search globalchatbot for fast and real chats 🚀'

# Special target: DefiantChatBot (text-only promotion)
DEFIANT_BOT = '@DefiantChatBot'
DEFIANT_MATCH_PHRASE = '✨ Partner found! ✨'
DEFIANT_STOP_PHRASE = 'Type /search to start a new conversation'
DEFIANT_SEARCH_COMMAND = '/search'
DEFIANT_NEXT_COMMAND = '/next'
DEFIANT_PROMO_TEXT = 'hey ,try @GlobalChatbot for chat faster'

# Special target: ChatIncognitoBot (button-driven anonymous chat)
CHAT_INCOGNITO_BOT = '@ChatIncognitoBot'
CHAT_INCOGNITO_MATCH_PHRASE = 'You have been matched with another user.'
CHAT_INCOGNITO_CHAT_OVER_PHRASE = '⬆️CHAT OVER⬆️'
CHAT_INCOGNITO_OPEN_BUTTONS = (
    '🔓🔑 Open again this chat',
    'Open again this chat',
)
CHAT_INCOGNITO_PROMO_TEXT = 'search globalchatbot for fast and real chats 🚀'

# Special target: MeChat anonymous-chat bot
MECHAT_BOT = '@mechat'
MECHAT_NEW_CHAT_BUTTONS = ('New Anonymous Chat!', 'New Anonymous Chat')
MECHAT_RANDOM_BUTTONS = ('Random(Free)', 'Random (Free)', 'Random')
MECHAT_PROFILE_BUTTONS = ('Contact Profile', 'View Profile', 'View profile')
MECHAT_END_BUTTONS = ('End Chat', 'End chat')
MECHAT_CONFIRM_END_BUTTONS = ('End Chat', 'End chat')
MECHAT_PARTNER_LEFT_PHRASES = (
    'has left the chat.',
    'left the chat.',
    'Your chat partner has left',
    'partner has left',
)
MECHAT_FOUND_PHRASES = ('found partner for you!', 'Say hi 👋🗣')
MECHAT_HI_PROBABILITY = 0.30
MECHAT_HI_MESSAGES = ('hi', 'hey', 'hello', 'hi 👋', 'hey, how are you?')

# Special target: MeloGap anonymous-chat bot
MELOGAP_BOT = '@melogap'
MELOGAP_CONNECT_TEXT = 'به یه ناشناس وصل کن!'
MELOGAP_SEARCH_BUTTONS = ('جستجوی شانسی🎲', 'جستجوی شانسی 🎲', 'جستجوی شانسی')
MELOGAP_PROFILE_TEXT = '◻👤 پروفایل مخاطب'
MELOGAP_END_TEXT = 'پایان چت'
MELOGAP_CONFIRM_END_BUTTONS = ('اتمام چت❌', 'اتمام چت ❌', 'اتمام چت')
MELOGAP_MATCH_PHRASES = ('پیدا کردم و وصل‌تون کردم!', 'پیدا کردم و وصلتون کردم!', 'پیدا کردم و وصل تون کردم!', 'پیدا کردم و وصل‌تون کردم')
MELOGAP_SEARCH_MENU_PHRASES = ('پیدا کنم', 'جستجوی شانسی', 'به یه ناشناس وصلت کنم', 'به یه ناشناس وصل کن')
MELOGAP_CHAT_END_PHRASES = ('بسته شد', 'ایشون', 'توسط شما قطع شد')
# Optional small-talk sent to the matched stranger only sometimes.
MELOGAP_GREETING_PROBABILITY = 0.30
MELOGAP_GREETING_MESSAGES = (
    'hi',
    'hey',
    'hello',
    'how are you?',
    'hey, how are you?',
    'hi, how are you?',
)


# GLOBALS
message_counters: Dict[str, int] = {}  # Counter per bot
used_messages: Set[str] = set()

# Primary Match Indicators
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

# Only trigger on partner disconnects. Do NOT add "Вы завершили" here or it will double-skip.
DISCONNECT_KEYWORDS = [
    "Собеседник завершил",
    "Your partner has stopped"
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
    """Check if message indicates a match (supporting regular and premium)"""
    if not message_text:
        return False
    
    # Convert text to lowercase for reliable matching
    text_lower = message_text.lower()
    
    # Check against the standard MATCH_KEYWORDS list
    for keyword in MATCH_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
            
    # Additional robust check for premium chat UI elements (e.g., room and reaction counters)
    if "комната:" in text_lower and ("собеседник" in text_lower or "реакции:" in text_lower or "match" in text_lower):
        return True
        
    return False
    

def generate_random_message(bot_username: str) -> str:
    """Generate a random promotional message"""
    if bot_username == '@chatus':
        return "@ gta347943"
        
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
        self.timeout_tasks: Dict[str, asyncio.Task] = {}
        self.chat_states: Dict[str, str] = {}

        # Bot 2 state
        self.bot2_next_limit_reached = False
        self.anonity_bot_entity = None
        self.anonity_waiting_for_match = False
        self.defiant_bot_entity = None
        self.defiant_waiting_for_match = False

        # ChatIncognitoBot state
        self.chat_incognito_bot_entity = None
        self.chat_incognito_waiting_for_match = False
        self.chat_incognito_action_lock = asyncio.Lock()

        # MeChat state
        self.mechat_bot_entity = None
        self.mechat_state = 'IDLE'
        self.mechat_action_lock = asyncio.Lock()
        self.mechat_end_task = None

        # MeloGap state
        self.melogap_bot_entity = None
        self.melogap_state = 'IDLE'
        self.melogap_action_lock = asyncio.Lock()

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

            # Handler for Bot 2 (Mutual Anonymous Chat)
            if BOT2_TARGET_BOTS:
                logger.info(f"🤖 Bot 2 targets: {BOT2_TARGET_BOTS}")

                @self.client.on(events.NewMessage(chats=BOT2_TARGET_BOTS))
                async def handle_bot2_message(event):
                    await self.process_bot2_message(event)
            else:
                logger.info("ℹ️ No TARGET_BOT env var set — Bot 2 handler skipped")

            # Special handler for @AnonityChatBot
            try:
                self.anonity_bot_entity = await self.client.get_entity(ANONITY_BOT)
                logger.info(f"✅ Found special target bot: {ANONITY_BOT}")

                @self.client.on(events.NewMessage(chats=self.anonity_bot_entity))
                async def handle_taster_message(event):
                    await self.process_anonity_message(event)

                # Start the Anonity search loop: /search -> wait for Partner found
                await self.start_anonity_search()

            except Exception as e:
                logger.error(f"❌ Failed to initialize {ANONITY_BOT}: {str(e)}")

            # Special handler for @DefiantChatBot (text-only)
            try:
                self.defiant_bot_entity = await self.client.get_entity(DEFIANT_BOT)
                logger.info(f"✅ Found special target bot: {DEFIANT_BOT}")

                @self.client.on(events.NewMessage(chats=self.defiant_bot_entity))
                async def handle_defiant_message(event):
                    await self.process_defiant_message(event)

                # Start Defiant search loop: /search -> wait for Partner found
                await self.start_defiant_search()

            except Exception as e:
                logger.error(f"❌ Failed to initialize {DEFIANT_BOT}: {str(e)}")

            # Special handler for @ChatIncognitoBot
            try:
                self.chat_incognito_bot_entity = await self.client.get_entity(CHAT_INCOGNITO_BOT)
                logger.info(f"✅ Found special target bot: {CHAT_INCOGNITO_BOT}")

                @self.client.on(events.NewMessage(chats=self.chat_incognito_bot_entity))
                async def handle_chat_incognito_message(event):
                    await self.process_chat_incognito_message(event)

                # Start the ChatIncognito search cycle.
                await self.start_chat_incognito_search()

            except Exception as e:
                logger.error(f"❌ Failed to initialize {CHAT_INCOGNITO_BOT}: {str(e)}")

            # Special handler for @mechat (button-driven anonymous chat)
            try:
                self.mechat_bot_entity = await self.client.get_entity(MECHAT_BOT)
                logger.info(f"✅ Found special target bot: {MECHAT_BOT}")

                @self.client.on(events.NewMessage(chats=self.mechat_bot_entity))
                async def handle_mechat_message(event):
                    await self.process_mechat_message(event)

                await self.start_mechat_search()

            except Exception as e:
                logger.error(f"❌ Failed to initialize {MECHAT_BOT}: {str(e)}")

            # Special handler for @melogap (button-driven anonymous chat)
            try:
                self.melogap_bot_entity = await self.client.get_entity(MELOGAP_BOT)
                logger.info(f"✅ Found special target bot: {MELOGAP_BOT}")

                @self.client.on(events.NewMessage(chats=self.melogap_bot_entity))
                async def handle_melogap_message(event):
                    await self.process_melogap_message(event)

                # Start the MeloGap cycle: send connect text -> click "جستجوی شانسی".
                await self.start_melogap_search()

            except Exception as e:
                logger.error(f"❌ Failed to initialize {MELOGAP_BOT}: {str(e)}")

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

            if sender_bot not in self.chat_states:
                self.chat_states[sender_bot] = 'SEARCHING'

            logger.debug(f"📨 Received from {sender_bot}: {message_text[:50]}...")

            # 1. Did we find a match?
            if is_match_message(message_text):
                # Lock state to prevent race conditions from multi-part messages
                if self.chat_states[sender_bot] == 'MATCHED':
                    return
                
                self.cancel_timeout_task(sender_bot)
                self.chat_states[sender_bot] = 'MATCHED'
                
                logger.info(f"🎯 Match detected from {sender_bot}!")
                self.statistics.record_match(sender_bot)
                
                # Wait 2.0s before sending text
                logger.info(f"⏳ Waiting 2.0s before sending promo text to {sender_bot}...")
                await asyncio.sleep(0.1)
                
                if self.chat_states[sender_bot] == 'MATCHED':
                    await self.send_promotional_message(sender_bot)
                    
                    # Wait 2.0s before sending /next
                    logger.info(f"⏳ Waiting 2.0s before sending /next to {sender_bot}...")
                    await asyncio.sleep(2.0)
                    
                    if self.chat_states[sender_bot] == 'MATCHED':
                        self.chat_states[sender_bot] = 'SEARCHING'
                        await self.send_next_command(sender_bot)

            # 2. Did the partner disconnect early?
            elif any(keyword.lower() in message_text.lower() for keyword in DISCONNECT_KEYWORDS):
                if self.chat_states[sender_bot] == 'SEARCHING':
                    return
                    
                self.cancel_timeout_task(sender_bot)
                self.chat_states[sender_bot] = 'SEARCHING'
                logger.info(f"⚠️ Partner left early in {sender_bot}. Instantly forcing /next...")
                await self.send_next_command(sender_bot)
                
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            if 'sender_bot' in locals() and sender_bot:
                self.statistics.record_error(sender_bot)

    async def start_anonity_search(self):
        """Start the Anonity search loop."""
        if not self.anonity_bot_entity:
            return

        try:
            self.anonity_waiting_for_match = True

            await self.client.send_message(self.anonity_bot_entity, ANONITY_SEARCH_COMMAND)

            logger.info(f"🔎 {ANONITY_BOT}: started search loop")
        except Exception as e:
            logger.error(f"❌ Failed to start {ANONITY_BOT} search: {e}")

    async def process_anonity_message(self, event):
        """Handle Anonity partner matches and chat-ended messages."""
        try:
            text = event.raw_text or ''

            # A partner was found: send the newest Saved Messages sticker.
            if ANONITY_MATCH_PHRASE in text:
                if not self.anonity_waiting_for_match:
                    return

                self.anonity_waiting_for_match = False
                logger.info(f"🎯 {ANONITY_BOT}: partner found")

                await self.client.send_message(
                    self.anonity_bot_entity,
                    ANONITY_PROMO_TEXT
                )
                logger.info(f"💬 {ANONITY_BOT}: sent text promo")

                # Wait 2 seconds, then find another partner.
                await asyncio.sleep(2)
                await self.client.send_message(self.anonity_bot_entity, ANONITY_NEXT_COMMAND)
                self.anonity_waiting_for_match = True
                logger.info(f"🔎 {ANONITY_BOT}: sent /next")

            # Partner stopped the chat: restart searching.
            elif ANONITY_STOP_PHRASE in text:
                self.anonity_waiting_for_match = True
                logger.info(f"🔎 {ANONITY_BOT}: partner stopped chat, sending /search")
                await asyncio.sleep(1)
                await self.client.send_message(self.anonity_bot_entity, ANONITY_SEARCH_COMMAND)

        except Exception as e:
            logger.error(f"❌ {ANONITY_BOT} error processing message: {e}")

    async def start_defiant_search(self):
        """Start searching for a partner on DefiantChatBot."""
        try:
            await self.client.send_message(self.defiant_bot_entity, DEFIANT_SEARCH_COMMAND)
            self.defiant_waiting_for_match = True
            logger.info(f"🔎 {DEFIANT_BOT}: sent /search")
        except Exception as e:
            logger.error(f"❌ Failed to start {DEFIANT_BOT} search: {e}")

    async def process_defiant_message(self, event):
        """Handle DefiantChatBot matches using text only."""
        try:
            text = event.raw_text or ''

            if DEFIANT_MATCH_PHRASE in text:
                if not self.defiant_waiting_for_match:
                    return

                self.defiant_waiting_for_match = False
                logger.info(f"🎯 {DEFIANT_BOT}: partner found")

                # Text only: no sticker/media is sent.
                await self.client.send_message(self.defiant_bot_entity, DEFIANT_PROMO_TEXT)
                logger.info(f"💬 {DEFIANT_BOT}: sent text promo")

                await asyncio.sleep(2)
                await self.client.send_message(self.defiant_bot_entity, DEFIANT_NEXT_COMMAND)
                self.defiant_waiting_for_match = True
                logger.info(f"🔎 {DEFIANT_BOT}: sent /next")

            elif DEFIANT_STOP_PHRASE in text:
                self.defiant_waiting_for_match = True
                logger.info(f"🔎 {DEFIANT_BOT}: partner stopped chat, sending /search")
                await asyncio.sleep(1)
                await self.client.send_message(self.defiant_bot_entity, DEFIANT_SEARCH_COMMAND)

        except Exception as e:
            logger.error(f"❌ {DEFIANT_BOT} error processing message: {e}")

    async def start_chat_incognito_search(self):
        """Start ChatIncognitoBot by using its available 'open again' flow."""
        if not self.chat_incognito_bot_entity:
            return

        # ChatIncognito normally begins searching automatically after a chat is
        # reopened. There is no documented /search command in the observed UI.
        self.chat_incognito_waiting_for_match = True
        logger.info(f"🔎 {CHAT_INCOGNITO_BOT}: ready and waiting for a match")

    async def _chat_incognito_click_open_button(self, message=None):
        """Click ChatIncognito's 'Open again this chat' button safely."""
        if not self.chat_incognito_bot_entity:
            return False

        messages = []
        if message is not None:
            messages.append(message)

        # Re-fetch recent messages because Telegram may attach inline buttons
        # after the original NewMessage event arrives.
        try:
            async for msg in self.client.iter_messages(
                self.chat_incognito_bot_entity, limit=8
            ):
                if not any(existing.id == msg.id for existing in messages):
                    messages.append(msg)
        except Exception as e:
            logger.warning(f"⚠️ {CHAT_INCOGNITO_BOT}: failed to refresh messages: {e}")

        for msg in messages:
            buttons = getattr(msg, 'buttons', None)
            if not buttons:
                continue

            for row_index, row in enumerate(buttons):
                for col_index, button in enumerate(row):
                    label = str(getattr(button, 'text', '') or '').strip()
                    if not label:
                        continue

                    matched = (
                        label in CHAT_INCOGNITO_OPEN_BUTTONS
                        or any(candidate in label or label in candidate
                               for candidate in CHAT_INCOGNITO_OPEN_BUTTONS)
                    )
                    if not matched:
                        continue

                    try:
                        await button.click()
                        logger.info(
                            f"🖱️ {CHAT_INCOGNITO_BOT}: clicked '{label}' directly"
                        )
                        return True
                    except Exception as direct_error:
                        logger.warning(
                            f"⚠️ {CHAT_INCOGNITO_BOT}: direct click failed for "
                            f"'{label}': {direct_error}"
                        )

                    try:
                        await msg.click(i=row_index, j=col_index)
                        logger.info(
                            f"🖱️ {CHAT_INCOGNITO_BOT}: clicked '{label}' "
                            f"through message coordinates"
                        )
                        return True
                    except Exception as coordinate_error:
                        logger.warning(
                            f"⚠️ {CHAT_INCOGNITO_BOT}: coordinate click failed "
                            f"for '{label}': {coordinate_error}"
                        )

        return False

    async def process_chat_incognito_message(self, event):
        """Handle ChatIncognitoBot's match and chat-over UI."""
        try:
            text = (event.raw_text or '').strip()
            if not text:
                return

            # New partner found.
            if CHAT_INCOGNITO_MATCH_PHRASE in text:
                async with self.chat_incognito_action_lock:
                    if not self.chat_incognito_waiting_for_match:
                        return

                    self.chat_incognito_waiting_for_match = False
                    logger.info(f"🎯 {CHAT_INCOGNITO_BOT}: partner found")

                    await asyncio.sleep(0.5)
                    await self.client.send_message(
                        self.chat_incognito_bot_entity,
                        CHAT_INCOGNITO_PROMO_TEXT
                    )
                    logger.info(
                        f"✅ {CHAT_INCOGNITO_BOT}: sent promotional message"
                    )
                return

            # Chat ended. Try the bot's own "Open again this chat" button.
            if CHAT_INCOGNITO_CHAT_OVER_PHRASE in text:
                async with self.chat_incognito_action_lock:
                    await asyncio.sleep(0.5)

                    clicked = await self._chat_incognito_click_open_button(
                        event.message
                    )

                    if clicked:
                        self.chat_incognito_waiting_for_match = True
                        logger.info(
                            f"🔓 {CHAT_INCOGNITO_BOT}: reopened chat; "
                            f"waiting for next match"
                        )
                    else:
                        logger.info(
                            f"ℹ️ {CHAT_INCOGNITO_BOT}: chat ended, but no "
                            f"'Open again this chat' button was available"
                        )
                return

        except Exception as e:
            logger.error(
                f"❌ {CHAT_INCOGNITO_BOT} error processing message: {e}"
            )
            self.chat_incognito_waiting_for_match = True

    async def _mechat_click_button(self, message, candidates):
        """Click a MeChat inline/reply button by visible text, refreshing if needed."""
        if not self.mechat_bot_entity:
            return False

        messages = []
        if message is not None:
            messages.append(message)

        try:
            async for msg in self.client.iter_messages(self.mechat_bot_entity, limit=10):
                if not any(existing.id == msg.id for existing in messages):
                    messages.append(msg)
        except Exception as e:
            logger.warning(f"⚠️ {MECHAT_BOT}: failed to refresh messages: {e}")

        wanted = tuple(str(x).strip().lower() for x in candidates)
        for msg in messages:
            buttons = getattr(msg, 'buttons', None)
            if not buttons:
                continue
            for row_index, row in enumerate(buttons):
                for col_index, button in enumerate(row):
                    label = str(getattr(button, 'text', '') or '').strip()
                    if not label:
                        continue
                    label_lower = label.lower()
                    if not any(x == label_lower or x in label_lower or label_lower in x for x in wanted):
                        continue
                    try:
                        await button.click()
                        logger.info(f"🖱️ {MECHAT_BOT}: clicked '{label}' directly")
                        return True
                    except Exception as e:
                        logger.warning(f"⚠️ {MECHAT_BOT}: direct click failed for '{label}': {e}")
                    try:
                        await msg.click(i=row_index, j=col_index)
                        logger.info(f"🖱️ {MECHAT_BOT}: clicked '{label}' by coordinates")
                        return True
                    except Exception as e:
                        logger.warning(f"⚠️ {MECHAT_BOT}: coordinate click failed for '{label}': {e}")
        return False

    async def start_mechat_search(self):
        """Start MeChat by clicking New Anonymous Chat, then Random."""
        if not self.mechat_bot_entity:
            return
        async with self.mechat_action_lock:
            try:
                self.mechat_state = 'STARTING'
                clicked = await self._mechat_click_button(None, MECHAT_NEW_CHAT_BUTTONS)
                if clicked:
                    await asyncio.sleep(0.5)
                    if self.mechat_state == 'STARTING':
                        clicked_random = await self._mechat_click_button(None, MECHAT_RANDOM_BUTTONS)
                        self.mechat_state = 'SEARCHING' if clicked_random else 'WAITING_MENU'
                        logger.info(f"🔎 {MECHAT_BOT}: started random search")
                else:
                    self.mechat_state = 'WAITING_MENU'
                    logger.warning(f"⚠️ {MECHAT_BOT}: could not find 'New Anonymous Chat!' button")
            except Exception as e:
                self.mechat_state = 'IDLE'
                logger.error(f"❌ Failed to start {MECHAT_BOT}: {e}")

    async def process_mechat_message(self, event):
        """MeChat: New Anonymous Chat -> Random -> partner -> profile -> wait 3s -> end -> confirm."""
        try:
            text = (event.raw_text or '').strip()
            lower = text.lower()

            # If partner leaves before our planned end, cancel the end sequence.
            # IMPORTANT: do not click Random automatically after an early partner leave.
            if any(phrase.lower() in lower for phrase in MECHAT_PARTNER_LEFT_PHRASES):
                if self.mechat_end_task and not self.mechat_end_task.done():
                    self.mechat_end_task.cancel()
                self.mechat_state = 'PARTNER_LEFT'
                logger.info(f"🚪 {MECHAT_BOT}: partner left early; NOT starting another random chat")
                return

            # Menu/button messages: click Random only while we are explicitly starting a chat.
            if self.mechat_state in ('WAITING_MENU', 'STARTING'):
                if getattr(event.message, 'buttons', None):
                    if await self._mechat_click_button(event.message, MECHAT_RANDOM_BUTTONS):
                        self.mechat_state = 'SEARCHING'
                        logger.info(f"🎲 {MECHAT_BOT}: clicked Random")
                        return

            # Partner found: view profile, then wait 3 seconds and end the chat.
            if any(phrase.lower() in lower for phrase in MECHAT_FOUND_PHRASES):
                if self.mechat_state not in ('SEARCHING', 'WAITING_MENU'):
                    return
                self.mechat_state = 'MATCHED'
                logger.info(f"🎯 {MECHAT_BOT}: partner found")

                await asyncio.sleep(0.5)
                if self.mechat_state != 'MATCHED':
                    return
                clicked = await self._mechat_click_button(event.message, MECHAT_PROFILE_BUTTONS)
                if not clicked:
                    logger.warning(f"⚠️ {MECHAT_BOT}: could not click Contact Profile")
                    return
                self.mechat_state = 'PROFILE_VIEWED'

                # Sometimes send a short greeting after viewing the partner profile.
                # This is intentionally randomized so it does not happen every chat.
                if random.random() < MECHAT_HI_PROBABILITY and self.mechat_state == 'PROFILE_VIEWED':
                    hi_message = random.choice(MECHAT_HI_MESSAGES)
                    try:
                        await self.client.send_message(self.mechat_bot_entity, hi_message)
                        logger.info(f"👋 {MECHAT_BOT}: sent optional greeting: {hi_message!r}")
                    except Exception as hi_error:
                        logger.warning(f"⚠️ {MECHAT_BOT}: failed to send optional greeting: {hi_error}")

                async def end_after_delay():
                    try:
                        await asyncio.sleep(3)
                        if self.mechat_state != 'PROFILE_VIEWED':
                            return
                        clicked_end = await self._mechat_click_button(None, MECHAT_END_BUTTONS)
                        if clicked_end:
                            self.mechat_state = 'ENDING_CONFIRMATION'
                            logger.info(f"🚪 {MECHAT_BOT}: clicked End Chat; waiting for confirmation")
                        else:
                            logger.warning(f"⚠️ {MECHAT_BOT}: could not click End Chat")
                    except asyncio.CancelledError:
                        logger.info(f"🛑 {MECHAT_BOT}: scheduled end cancelled")

                self.mechat_end_task = asyncio.create_task(end_after_delay())
                return

            # Confirmation screen: click the explicit End Chat button.
            if self.mechat_state == 'ENDING_CONFIRMATION' and ('sure' in lower or 'close this chat' in lower or 'are you sure' in lower):
                clicked = await self._mechat_click_button(event.message, MECHAT_CONFIRM_END_BUTTONS)
                if clicked:
                    self.mechat_state = 'ENDED'
                    logger.info(f"✅ {MECHAT_BOT}: chat ended and confirmed")
                    # Start the next cycle only after a deliberate successful end.
                    await asyncio.sleep(1)
                    await self.start_mechat_search()
                return

            # Some MeChat versions show the confirmation text simply as "Are you sure...".
            if self.mechat_state == 'ENDING_CONFIRMATION' and 'end chat' in lower:
                clicked = await self._mechat_click_button(event.message, MECHAT_CONFIRM_END_BUTTONS)
                if clicked:
                    self.mechat_state = 'ENDED'
                    await asyncio.sleep(1)
                    await self.start_mechat_search()

        except Exception as e:
            logger.error(f"❌ {MECHAT_BOT} error processing message: {e}")

    async def _melogap_click_button(self, message, candidates):
        """Robustly click a MeloGap inline button by its visible Persian label."""
        if not message or not getattr(message, 'buttons', None):
            logger.warning(f"⚠️ {MELOGAP_BOT}: message has no clickable buttons")
            return False

        normalized = [str(candidate).strip() for candidate in candidates]

        for row_index, row in enumerate(message.buttons):
            for col_index, button in enumerate(row):
                label = str(getattr(button, 'text', '') or '').strip()
                if not label:
                    continue
                matched = label in normalized or any(
                    candidate in label or label in candidate for candidate in normalized
                )
                if not matched:
                    continue

                # Method 1: click the actual Telethon MessageButton.
                try:
                    await button.click()
                    logger.info(
                        f"🖱️ {MELOGAP_BOT}: clicked '{label}' directly "
                        f"(row={row_index}, col={col_index})"
                    )
                    return True
                except Exception as direct_error:
                    logger.warning(
                        f"⚠️ {MELOGAP_BOT}: direct button click failed for '{label}': "
                        f"{direct_error}"
                    )

                # Method 2: click the button through the message coordinates.
                try:
                    await message.click(i=row_index, j=col_index)
                    logger.info(
                        f"🖱️ {MELOGAP_BOT}: clicked '{label}' through message "
                        f"coordinates"
                    )
                    return True
                except Exception as coordinate_error:
                    logger.warning(
                        f"⚠️ {MELOGAP_BOT}: coordinate click failed for '{label}': "
                        f"{coordinate_error}"
                    )

        return False

    async def _melogap_click_latest_button(self, candidates, limit=8):
        """Find the newest MeloGap message containing one of the requested buttons."""
        if not self.melogap_bot_entity:
            return False
        async for message in self.client.iter_messages(self.melogap_bot_entity, limit=limit):
            if await self._melogap_click_button(message, candidates):
                return True
        return False

    async def start_melogap_search(self):
        """Start MeloGap: send the connect request, then click random search."""
        if not self.melogap_bot_entity:
            return

        async with self.melogap_action_lock:
            try:
                self.melogap_state = 'REQUESTING'
                await self.client.send_message(self.melogap_bot_entity, MELOGAP_CONNECT_TEXT)
                logger.info(f"📨 {MELOGAP_BOT}: sent initial connect request")
            except Exception as e:
                self.melogap_state = 'IDLE'
                logger.error(f"❌ Failed to start {MELOGAP_BOT}: {e}")

    async def process_melogap_message(self, event):
        """MeloGap cycle: connect -> random search -> match -> profile -> end -> confirm -> repeat."""
        try:
            text = (event.raw_text or '').strip()
            logger.debug(f"📨 {MELOGAP_BOT}: {text[:100]}...")

            # After the connect request, MeloGap shows a menu containing
            # "جستجوی شانسی🎲". Do not depend on the surrounding message text:
            # the screenshot shows that the useful signal is the button itself.
            if self.melogap_state == 'REQUESTING':
                has_search_button = False
                if getattr(event.message, 'buttons', None):
                    for row in event.message.buttons:
                        for button in row:
                            label = str(getattr(button, 'text', '') or '').strip()
                            if any(candidate in label or label in candidate for candidate in MELOGAP_SEARCH_BUTTONS):
                                has_search_button = True
                                break
                        if has_search_button:
                            break

                if has_search_button or any(phrase in text for phrase in MELOGAP_SEARCH_MENU_PHRASES):
                    async with self.melogap_action_lock:
                        if self.melogap_state != 'REQUESTING':
                            return
                        await asyncio.sleep(0.5)
                        clicked = await self._melogap_click_button(event.message, MELOGAP_SEARCH_BUTTONS)
                        if not clicked:
                            clicked = await self._melogap_click_latest_button(MELOGAP_SEARCH_BUTTONS, limit=10)
                        if clicked:
                            self.melogap_state = 'SEARCHING'
                            logger.info(f"🎲 {MELOGAP_BOT}: clicked random search")
                    return

            # Match found: wait 2s -> send profile -> wait 2s -> send end chat.
            # Match found: wait 4s -> send profile -> wait 6.5s (10.5s total) -> send end chat.
            if any(phrase in text for phrase in MELOGAP_MATCH_PHRASES):
                if self.melogap_state != 'SEARCHING':
                    return

                async with self.melogap_action_lock:
                    if self.melogap_state != 'SEARCHING':
                        return
                    self.melogap_state = 'MATCHED'
                    logger.info(f"🎯 {MELOGAP_BOT}: partner found")

                    # Wait 4.0 seconds after being connected
                    await asyncio.sleep(4.0)

                    # Optional greeting
                    if random.random() < MELOGAP_GREETING_PROBABILITY:
                        greeting = random.choice(MELOGAP_GREETING_MESSAGES)
                        await self.client.send_message(self.melogap_bot_entity, greeting)
                        logger.info(f"💬 {MELOGAP_BOT}: sent optional greeting: {greeting!r}")

                    await self.client.send_message(self.melogap_bot_entity, MELOGAP_PROFILE_TEXT)
                    logger.info(f"👤 {MELOGAP_BOT}: sent profile request")

                    # Wait 6.5 seconds so total elapsed time exceeds MeloGap's 10-second rule
                    await asyncio.sleep(6.5)
                    await self.client.send_message(self.melogap_bot_entity, MELOGAP_END_TEXT)
                    self.melogap_state = 'ENDING'
                    logger.info(f"🚪 {MELOGAP_BOT}: sent end-chat request")
                return

            # STEP 4: End Chat Confirmation
            # MeloGap sends an INLINE keyboard with two buttons:
            #   ادامه ی چت
            #   اتمام چت❌
            # Only click the explicit "اتمام چت" button. Never blindly click
            # the first button because that can choose "ادامه ی چت".
            elif self.melogap_state == 'ENDING' and "مطمئنی" in text:
                logger.info("📍 End chat confirmation detected. Clicking inline button...")
                async with self.melogap_action_lock:
                    if self.melogap_state != 'ENDING':
                        return

                    # Wait briefly for buttons to fully load onto the message
                    await asyncio.sleep(0.5)

                    # Re-fetch the message to guarantee the inline buttons are attached
                    msg = await self.client.get_messages(
                        self.melogap_bot_entity,
                        ids=event.message.id
                    )

                    if not msg or not getattr(msg, 'buttons', None):
                        logger.warning(f"⚠️ {MELOGAP_BOT}: confirmation message has no buttons")
                        return

                    # Use Telethon's built-in text search to click the inline button directly
                    try:
                        await msg.click(text='اتمام چت')
                        logger.info(f"✅ {MELOGAP_BOT}: Successfully clicked the inline end button")
                    except Exception as click_error:
                        logger.error(f"❌ {MELOGAP_BOT}: Failed to click inline button: {click_error}")
                        return

                    # Give the bot time to process the disconnection on its server
                    self.melogap_state = 'REQUESTING'
                    await asyncio.sleep(2.5) 
                    
                    await self.client.send_message(
                        self.melogap_bot_entity,
                        MELOGAP_CONNECT_TEXT
                    )
                    logger.info(f"🔄 {MELOGAP_BOT}: confirmation clicked; starting next cycle")
                return
                 
            # If the partner ends first, restart the same connect -> search cycle.
            if any(phrase in text for phrase in MELOGAP_CHAT_END_PHRASES):
                if self.melogap_state in ('REQUESTING', 'SEARCHING'):
                    return
                async with self.melogap_action_lock:
                    self.melogap_state = 'REQUESTING'
                    await asyncio.sleep(1.0)
                    await self.client.send_message(self.melogap_bot_entity, MELOGAP_CONNECT_TEXT)
                    logger.info(f"📨 {MELOGAP_BOT}: partner ended chat; restarted cycle")

        except Exception as e:
            logger.error(f"❌ {MELOGAP_BOT} error processing message: {e}")
            self.melogap_state = 'IDLE'

    async def get_latest_sticker(self):
        """Return the newest sticker in Saved Messages (Telegram 'me')."""
        try:
            async for message in self.client.iter_messages('me', limit=50):
                if message.sticker:
                    return message.document
        except Exception as e:
            logger.error(f"❌ Error fetching latest Saved Messages sticker: {e}")

        return None

    async def process_bot2_message(self, event):
        """Process incoming messages from Bot 2 (Mutual Anonymous Chat) targets"""
        try:
            text = event.raw_text

            if 'Partner found 😺' in text:
                logger.info("Bot 2: Partner found.")
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

            self.cancel_timeout_task(bot_username)

            await self.client.send_message(self.target_bot_entities[bot_username], "/next")
            logger.info(f"✅ Sent /next command to {bot_username}")

            # Fire up a repeating response monitor task
            self.timeout_tasks[bot_username] = asyncio.create_task(
                self.monitor_bot_timeout(bot_username)
            )
        except Exception as e:
            logger.error(f"❌ Failed to send /next to {bot_username}: {str(e)}")
            self.statistics.record_error(bot_username)

    async def monitor_bot_timeout(self, bot_username: str):
        """Continually checks if bot is stuck and forces /next if no valid response"""
        try:
            while True:
                await asyncio.sleep(25)  # Wait 25 seconds
                logger.warning(f"⏰ {bot_username} is stuck or ignoring us. Forcing /next...")
                await self.client.send_message(self.target_bot_entities[bot_username], "/next")
        except asyncio.CancelledError:
            pass

    def cancel_timeout_task(self, bot_username: str):
        """Safely stops and discards a running timeout watcher"""
        task = self.timeout_tasks.get(bot_username)
        if task and not task.done() and task != asyncio.current_task():
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
                'melogap_bot': MELOGAP_BOT,
                'melogap_state': self.melogap_state,
                'mechat_bot': MECHAT_BOT,
                'mechat_state': self.mechat_state,
                'chat_incognito_bot': CHAT_INCOGNITO_BOT,
                'chat_incognito_waiting_for_match': self.chat_incognito_waiting_for_match,
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
    
