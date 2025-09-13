import asyncio
import logging
import time
from datetime import datetime, timedelta
import pytz
from os import getenv
from typing import Dict, List

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from storage import JSONStorage
from srs import SRSCalculator
from keyboards import *
from states import AddWordStates, SessionStates
from queue_manager import DueCardQueue
from daily_manager import DailyLearningManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Debug: Print all environment variables (without values)
import os
logger.info("Available environment variables: " + ", ".join(sorted(os.environ.keys())))

# Bot configuration
BOT_TOKEN = getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    logger.error("Available env vars: " + str(list(os.environ.keys())))
    raise ValueError("BOT_TOKEN not found in environment variables")

# Timezone for Asia/Tashkent
TIMEZONE = pytz.timezone('Asia/Tashkent')

# Initialize components
storage = JSONStorage()
srs = SRSCalculator()
queue_manager = DueCardQueue(storage)
daily_manager = DailyLearningManager(storage, TIMEZONE)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# APScheduler with memory job store
jobstores = {
    'default': MemoryJobStore()
}
scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=TIMEZONE)

# In-memory session locks
active_sessions = set()

async def is_session_active(user_id: int) -> bool:
    """Check if user has active session"""
    user_progress = storage.get_user_progress(user_id)
    session_info = user_progress.get('session', {})
    return session_info.get('active', False) or user_id in active_sessions

async def set_session_active(user_id: int, active: bool, mode: str = None):
    """Set session active status"""
    user_progress = storage.get_user_progress(user_id)
    if 'session' not in user_progress:
        user_progress['session'] = {}
    
    user_progress['session']['active'] = active
    if mode:
        user_progress['session']['mode'] = mode
    
    storage.update_user_progress(user_id, user_progress)
    
    if active:
        active_sessions.add(user_id)
    else:
        active_sessions.discard(user_id)

async def initialize_user_words(user_id: int):
    """Initialize progress for all words for new user"""
    words = storage.load_words()
    for word in words:
        storage.init_word_progress(user_id, word['id'])
    logger.info(f"Initialized {len(words)} words for user {user_id}")

async def reschedule_due_reviews(user_id: int):
    """Reschedule all due reviews when bot starts"""
    try:
        user_progress = storage.get_user_progress(user_id)
        words_progress = user_progress.get('words', {})
        current_time = int(time.time())
        
        # Reset user state on startup - they're not busy anymore
        user_session = user_progress.get('session', {})
        user_session['waiting_for_answer'] = False
        user_session['active'] = False
        user_progress['session'] = user_session
        storage.update_user_progress(user_id, user_progress)
        logger.info(f"Reset user {user_id} session state on startup")
        
        # Clear existing queue on restart
        queue_manager.clear_queue(user_id)
        
        scheduled_count = 0
        due_count = 0
        first_due_word = None
        
        for word_id, progress in words_progress.items():
            next_review_ts = progress.get('next_review_ts', 0)
            if next_review_ts > 0:
                if next_review_ts <= current_time:  # Already due
                    if first_due_word is None:
                        first_due_word = word_id  # Send first one immediately
                    else:
                        # Force add rest to queue
                        queue_manager.force_add_to_queue(user_id, word_id)
                    due_count += 1
                else:  # Future review
                    review_time = datetime.fromtimestamp(next_review_ts, tz=TIMEZONE)
                    schedule_word_review(user_id, word_id, review_time)
                    scheduled_count += 1
        
        # Send first due card immediately if any
        if first_due_word:
            await send_card_to_user(user_id, first_due_word)
            logger.info(f"Sent first overdue card {first_due_word} to user {user_id}")
        
        if scheduled_count > 0:
            logger.info(f"Rescheduled {scheduled_count} future reviews for user {user_id}")
        if due_count > 0:
            logger.info(f"Found {due_count} overdue cards for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error rescheduling reviews for user {user_id}: {e}")

@dp.message(CommandStart())
async def start_handler(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    # Initialize user if first time
    user_progress = storage.get_user_progress(user_id)
    if not user_progress or 'words' not in user_progress:
        await initialize_user_words(user_id)
        await message.answer(
            "🎉 Добро пожаловать в систему интервального повторения слов!\n\n"
            "📚 Я помогу вам эффективно изучать новые слова.\n"
            "🎯 Система автоматически определит оптимальные интервалы повторения.\n"
            "⏰ Карточки будут приходить точно в срок для повторения!",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Reschedule reviews for returning user
        await reschedule_due_reviews(user_id)
        
        stats = srs.get_stats(user_progress)
        daily_stats = daily_manager.get_daily_stats(user_id)
        
        # Daily progress indicator
        progress_bar = "🟩" * daily_stats['learned_today'] + "⬜" * daily_stats['remaining_today']
        if daily_stats['goal_reached']:
            daily_text = f"✅ Дневная цель выполнена! ({daily_stats['learned_today']}/{daily_stats['daily_goal']})"
        else:
            daily_text = f"📈 Сегодня изучено: {daily_stats['learned_today']}/{daily_stats['daily_goal']}\n{progress_bar}"
        
        await message.answer(
            f"👋 С возвращением!\n\n"
            f"📊 Общая статистика:\n"
            f"📚 Всего слов: {stats['total']}\n"
            f"🆕 Новых: {stats['new']}\n"
            f"📖 Изучается: {stats['learning']}\n"
            f"🔁 На повторении: {stats['review']}\n"
            f"⏰ К повторению: {stats['due']}\n\n"
            f"🎯 {daily_text}\n\n"
            f"🔔 Запланированные карточки придут автоматически!",
            reply_markup=get_main_menu_keyboard()
        )

@dp.message(F.text == "📚 Продолжить")
async def continue_review(message: Message, state: FSMContext):
    """Continue reviewing due words"""
    user_id = message.from_user.id
    
    if await is_session_active(user_id):
        await message.answer("⚠️ У вас уже есть активная сессия. Завершите её сначала.")
        return
    
    user_progress = storage.get_user_progress(user_id)
    due_words = srs.get_due_words(user_progress)
    
    if not due_words:
        await message.answer(
            "✅ Отлично! Нет слов для повторения.\n"
            "🎯 Попробуйте изучить новые слова или добавить свои.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Clear any pending cards from automatic notifications
    queue_manager.clear_queue(user_id)
    
    # Start review session
    await set_session_active(user_id, True, 'review')
    await state.set_state(SessionStates.reviewing)
    await state.update_data(due_words=due_words, current_index=0)
    
    await message.answer(
        f"🎯 Начинаем повторение!\n"
        f"📚 Слов к повторению: {len(due_words)}",
        reply_markup=get_stop_session_keyboard()
    )
    
    # Start first word
    await show_next_word(user_id, state, message)

@dp.message(F.text == "➕ Внести слова")
async def add_word_start(message: Message, state: FSMContext):
    """Start adding new word"""
    user_id = message.from_user.id
    
    if await is_session_active(user_id):
        await message.answer("⚠️ Завершите текущую сессию перед добавлением слов.")
        return
    
    await state.set_state(AddWordStates.waiting_for_word)
    await message.answer(
        "📝 Введите новое слово:",
        reply_markup=get_skip_keyboard()
    )

@dp.message(F.text == "🎓 Готов к обучению")
async def ready_to_learn(message: Message, state: FSMContext):
    """Start learning new words with daily limit"""
    user_id = message.from_user.id
    
    if await is_session_active(user_id):
        await message.answer("⚠️ У вас уже есть активная сессия.")
        return
    
    # Check daily progress
    daily_stats = daily_manager.get_daily_stats(user_id)
    
    if daily_stats['goal_reached']:
        await message.answer(
            f"🎉 Отлично! Вы уже выполнили дневную норму!\n\n"
            f"✅ Изучено сегодня: {daily_stats['learned_today']}/{daily_stats['daily_goal']}\n"
            f"📚 Доступно для повторения: много слов\n\n"
            f"💡 Можете повторять изученные слова или отдохнуть до завтра!",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    if not daily_stats['can_learn_more']:
        await message.answer(
            f"📚 Новые слова закончились!\n\n"
            f"🎯 Изучено сегодня: {daily_stats['learned_today']}/{daily_stats['daily_goal']}\n"
            f"📖 Всего доступно: {daily_stats['total_new_available']} слов\n\n"
            f"➕ Добавьте новые слова в базу или повторяйте изученные!",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Get words for today's session
    remaining_today = daily_stats['remaining_today']
    new_words = daily_manager.get_new_words_for_today(user_id, remaining_today)
    
    if not new_words:
        await message.answer(
            "🎉 Поздравляю! Вы изучили все доступные слова.\n"
            "➕ Добавьте новые слова для продолжения обучения.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Clear any pending cards from automatic notifications
    queue_manager.clear_queue(user_id)
    
    # Start learning session
    await set_session_active(user_id, True, 'learning')
    await state.set_state(SessionStates.learning_new)
    await state.update_data(
        new_words=new_words, 
        current_index=0,
        batch_size=5,
        learned_in_session=[]
    )
    
    await message.answer(
        f"🎓 Начинаем изучение новых слов!\n"
        f"📚 Слов в этой сессии: {len(new_words)}\n"
        f"🎯 Осталось до цели: {remaining_today} слов",
        reply_markup=get_stop_session_keyboard()
    )
    
    # Start first word
    await show_next_word(user_id, state, message)

async def show_next_word(user_id: int, state: FSMContext, message: Message):
    """Show next word in current session"""
    data = await state.get_data()
    
    # Determine word list and index based on session mode
    if 'due_words' in data:
        words = data['due_words']
        current_index = data['current_index']
        mode = 'review'
    elif 'new_words' in data:
        words = data['new_words']
        current_index = data['current_index']
        mode = 'learning'
    else:
        await end_session(user_id, state, message)
        return
    
    # Check if session is complete
    if current_index >= len(words):
        if mode == 'learning':
            # Schedule next batch if available
            await schedule_next_learning_batch(user_id, state, message)
        else:
            await end_session(user_id, state, message)
        return
    
    word_id = words[current_index]
    word_data = storage.get_word_by_id(word_id)
    
    if not word_data:
        # Skip invalid word
        await state.update_data(current_index=current_index + 1)
        await show_next_word(user_id, state, message)
        return
    
    # Show word for checking
    await state.update_data(current_word=word_id)
    await state.set_state(SessionStates.waiting_for_check)
    
    # Add soft pause
    await asyncio.sleep(1)
    
    await message.answer(
        f"💭 **{word_data['word']}**\n\n"
        f"🤔 Как переводится это слово?",
        reply_markup=get_check_word_keyboard(word_id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("check_"))
async def check_word(callback: CallbackQuery, state: FSMContext):
    """Show word translation and grading options"""
    word_id = callback.data.split("_", 1)[1]
    word_data = storage.get_word_by_id(word_id)
    
    if not word_data:
        await callback.answer("❌ Слово не найдено")
        return
    
    await state.set_state(SessionStates.waiting_for_grade)
    
    await callback.message.edit_text(
        f"💭 **{word_data['word']}**\n"
        f"🔍 **{word_data['translation']}**\n\n"
        f"❓ Насколько легко вам было вспомнить перевод?",
        reply_markup=get_grade_keyboard(word_id),
        parse_mode="Markdown"
    )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("grade_"))
async def grade_word(callback: CallbackQuery, state: FSMContext):
    """Process word grading and continue session"""
    _, word_id, grade_str = callback.data.split("_")
    grade = int(grade_str)
    user_id = callback.from_user.id
    
    # Get current word progress
    word_progress = storage.get_word_progress(user_id, word_id)
    
    # Calculate new progress
    updated_progress, interval = srs.calculate_next_review(word_progress, grade)
    
    # Update storage
    storage.update_word_progress(user_id, word_id, updated_progress)
    
    # Mark word as learned today if it was new
    word_progress_before = storage.get_word_progress(user_id, word_id)
    if word_progress_before.get('status') == 'new' and grade >= 3:
        daily_manager.mark_word_learned_today(user_id)
    
    # Schedule next review if word needs it
    next_review_ts = updated_progress.get('next_review_ts', 0)
    if next_review_ts > 0:
        review_time = datetime.fromtimestamp(next_review_ts, tz=TIMEZONE)
        schedule_word_review(user_id, word_id, review_time)
    
    # Process next card from queue
    await process_next_card(user_id)
    
    # Provide feedback
    feedback_messages = {
        2: "😰 Не переживайте, повторим скоро!",
        3: "😐 Неплохо, но есть над чем поработать.",
        4: "😊 Хорошо! Видим прогресс.",
        5: "🎉 Отлично! Вы освоили это слово!"
    }
    
    interval_text = srs.format_interval(interval)
    
    await callback.message.edit_text(
        f"✅ Оценка: {grade}/5\n"
        f"{feedback_messages.get(grade, '👍 Спасибо за оценку!')}\n\n"
        f"⏰ Следующее повторение: через {interval_text}",
        reply_markup=get_continue_stop_keyboard()
    )
    
    # Update session data
    data = await state.get_data()
    current_index = data.get('current_index', 0)
    await state.update_data(current_index=current_index + 1)
    
    await callback.answer()

@dp.callback_query(F.data == "continue_session")
async def continue_session(callback: CallbackQuery, state: FSMContext):
    """Continue to next word in session"""
    user_id = callback.from_user.id
    await show_next_word(user_id, state, callback.message)
    await callback.answer()

@dp.callback_query(F.data == "stop_session")
async def stop_session_callback(callback: CallbackQuery, state: FSMContext):
    """Stop current session"""
    user_id = callback.from_user.id
    await end_session(user_id, state, callback.message)
    await callback.answer("⏹️ Сессия завершена")

async def end_session(user_id: int, state: FSMContext, message: Message):
    """End current learning session"""
    await set_session_active(user_id, False)
    await state.clear()
    
    # Show updated stats and queue info
    user_progress = storage.get_user_progress(user_id)
    stats = srs.get_stats(user_progress)
    daily_stats = daily_manager.get_daily_stats(user_id)
    queue_size = queue_manager.get_queue_size(user_id)
    
    queue_info = f"\n🔄 В очереди: {queue_size} карточек" if queue_size > 0 else ""
    
    # Daily progress
    progress_bar = "🟩" * daily_stats['learned_today'] + "⬜" * daily_stats['remaining_today']
    if daily_stats['goal_reached']:
        daily_text = f"🎉 Дневная цель выполнена! ({daily_stats['learned_today']}/{daily_stats['daily_goal']})"
    else:
        daily_text = f"📈 Сегодня: {daily_stats['learned_today']}/{daily_stats['daily_goal']}\n{progress_bar}"
    
    await message.answer(
        f"✅ Сессия завершена!\n\n"
        f"🎯 {daily_text}\n\n"
        f"📊 Общая статистика:\n"
        f"📚 Всего слов: {stats['total']}\n"
        f"🆕 Новых: {stats['new']}\n"
        f"📖 Изучается: {stats['learning']}\n"
        f"🔁 На повторении: {stats['review']}\n"
        f"⏰ К повторению: {stats['due']}{queue_info}",
        reply_markup=get_main_menu_keyboard()
    )
    
    # Process next card if any in queue
    if queue_size > 0:
        await asyncio.sleep(3)  # Give user time to see stats
        await process_next_card(user_id)

async def schedule_next_learning_batch(user_id: int, state: FSMContext, message: Message):
    """Schedule next batch of 5 new words after 120 seconds"""
    user_progress = storage.get_user_progress(user_id)
    remaining_new_words = srs.get_new_words(user_progress, limit=5)
    
    if not remaining_new_words:
        await message.answer(
            "🎉 Поздравляем! Все новые слова изучены!\n"
            "📚 Теперь можете повторять изученные слова.",
            reply_markup=get_learning_complete_keyboard()
        )
        await end_session(user_id, state, message)
        return
    
    # Schedule next batch
    run_time = datetime.now(TIMEZONE) + timedelta(seconds=120)
    
    scheduler.add_job(
        send_next_learning_batch,
        'date',
        run_date=run_time,
        args=[user_id],
        id=f"learning_batch_{user_id}_{int(time.time())}"
    )
    
    await message.answer(
        f"✅ Отличная работа!\n\n"
        f"📚 Следующая партия из {len(remaining_new_words)} слов\n"
        f"⏰ будет доступна через 2 минуты\n\n"
        f"💡 Пока можете повторить изученные слова!",
        reply_markup=get_learning_complete_keyboard()
    )
    
    await end_session(user_id, state, message)

async def send_next_learning_batch(user_id: int):
    """Send notification about next learning batch"""
    try:
        user_progress = storage.get_user_progress(user_id)
        new_words = srs.get_new_words(user_progress, limit=5)
        
        if new_words:
            await bot.send_message(
                user_id,
                f"🔔 Готова новая партия слов для изучения!\n"
                f"📚 Слов доступно: {len(new_words)}\n\n"
                f"Нажмите '🎓 Готов к обучению' для начала.",
                reply_markup=get_main_menu_keyboard()
            )
    except Exception as e:
        logger.error(f"Error sending learning batch notification to {user_id}: {e}")

async def send_due_card_notification(user_id: int, word_id: str):
    """Send notification when a card is due for review (with queue management)"""
    try:
        # Check if user can receive card now or should queue it
        can_send_now = queue_manager.add_to_queue(user_id, word_id)
        
        if not can_send_now:
            logger.info(f"User {user_id} busy, queued card {word_id}")
            return
        
        # Send the card
        await send_card_to_user(user_id, word_id)
        
    except Exception as e:
        logger.error(f"Error in due card notification for {user_id}: {e}")

async def send_card_to_user(user_id: int, word_id: str):
    """Actually send card to user"""
    try:
        word_data = storage.get_word_by_id(word_id)
        if not word_data:
            logger.error(f"Word {word_id} not found")
            return
        
        user_progress = storage.get_user_progress(user_id)
        stats = srs.get_stats(user_progress)
        queue_size = queue_manager.get_queue_size(user_id)
        
        # Mark user as busy and set current word
        session = user_progress.get('session', {})
        session['waiting_for_answer'] = True
        session['current_word'] = word_id
        user_progress['session'] = session
        storage.update_user_progress(user_id, user_progress)
        
        queue_text = f"\n🔄 В очереди: {queue_size} карточек" if queue_size > 0 else ""
        
        await bot.send_message(
            user_id,
            f"⏰ Время повторения!\n\n"
            f"💭 **{word_data['word']}**\n"
            f"🤔 Помните перевод?\n\n"
            f"📚 К повторению: {stats['due']} слов{queue_text}",
            reply_markup=get_check_word_keyboard(word_id),
            parse_mode="Markdown"
        )
        
        logger.info(f"Sent card {word_id} to user {user_id} (marked as busy)")
        
    except Exception as e:
        logger.error(f"Error sending card to user {user_id}: {e}")

async def process_next_card(user_id: int):
    """Process next card from queue after user answered"""
    try:
        next_word_id = queue_manager.mark_answered(user_id)
        
        if next_word_id:
            # Small delay before next card
            await asyncio.sleep(2)
            await send_card_to_user(user_id, next_word_id)
        
    except Exception as e:
        logger.error(f"Error processing next card for user {user_id}: {e}")

def schedule_word_review(user_id: int, word_id: str, review_time: datetime):
    """Schedule a word for review at specific time"""
    try:
        job_id = f"review_{user_id}_{word_id}_{int(review_time.timestamp())}"
        
        # Remove any existing job for this word
        try:
            scheduler.remove_job(job_id)
        except:
            pass
        
        scheduler.add_job(
            send_due_card_notification,
            'date',
            run_date=review_time,
            args=[user_id, word_id],
            id=job_id,
            replace_existing=True
        )
        
        logger.info(f"Scheduled review for {word_id} at {review_time} (job: {job_id})")
        
    except Exception as e:
        logger.error(f"Error scheduling review for {word_id}: {e}")

# FSM Handlers for adding words
@dp.message(AddWordStates.waiting_for_word)
async def process_new_word(message: Message, state: FSMContext):
    """Process new word input"""
    if message.text in ["⏭️ Пропустить", "🔙 Назад в меню"]:
        await state.clear()
        await message.answer(
            "🔙 Возвращаемся в главное меню",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    word = message.text.strip()
    if not word:
        await message.answer("❌ Пожалуйста, введите корректное слово:")
        return
    
    await state.update_data(word=word)
    await state.set_state(AddWordStates.waiting_for_translation)
    await message.answer(
        f"📝 Слово: **{word}**\n"
        f"🔤 Теперь введите перевод:",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )

@dp.message(AddWordStates.waiting_for_translation)
async def process_translation(message: Message, state: FSMContext):
    """Process translation input and save word"""
    if message.text in ["⏭️ Пропустить", "🔙 Назад в меню"]:
        await state.clear()
        await message.answer(
            "🔙 Возвращаемся в главное меню",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    translation = message.text.strip()
    if not translation:
        await message.answer("❌ Пожалуйста, введите корректный перевод:")
        return
    
    data = await state.get_data()
    word = data['word']
    user_id = message.from_user.id
    
    # Add word to storage
    word_id = storage.add_word(word, translation)
    
    # Initialize progress for this user
    storage.init_word_progress(user_id, word_id)
    
    # Initialize progress for all existing users
    progress_data = storage.load_progress()
    for existing_user_id in progress_data.keys():
        storage.init_word_progress(int(existing_user_id), word_id)
    
    await state.clear()
    await message.answer(
        f"✅ Слово добавлено!\n\n"
        f"📝 **{word}** — {translation}\n"
        f"🆔 ID: {word_id}\n\n"
        f"🎯 Теперь это слово доступно для изучения!",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

async def startup():
    """Initialize bot on startup"""
    logger.info("🚀 Starting Spaced Repetition Bot")
    
    # Start scheduler
    scheduler.start()
    logger.info("📅 APScheduler started")
    
    # Reschedule existing reviews for all users
    try:
        progress_data = storage.load_progress()
        total_users = len(progress_data)
        logger.info(f"🔄 Rescheduling reviews for {total_users} users...")
        
        for user_id_str in progress_data.keys():
            user_id = int(user_id_str)
            await reschedule_due_reviews(user_id)
    except Exception as e:
        logger.error(f"Error rescheduling reviews on startup: {e}")
    
    logger.info("✅ Bot initialization completed")

async def main():
    """Main function to start the bot"""
    await startup()
    
    try:
        # Start polling
        await dp.start_polling(bot)
    finally:
        # Cleanup
        scheduler.shutdown()
        await bot.session.close()
        logger.info("🛑 Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())