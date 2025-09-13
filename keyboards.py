from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard with three options"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📚 Продолжить"),
        KeyboardButton(text="➕ Внести слова")
    )
    builder.row(
        KeyboardButton(text="🎓 Готов к обучению")
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=False)

def get_check_word_keyboard(word_id: str) -> InlineKeyboardMarkup:
    """Keyboard for checking word translation"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔍 Проверить", 
        callback_data=f"check_{word_id}"
    )
    return builder.as_markup()

def get_grade_keyboard(word_id: str) -> InlineKeyboardMarkup:
    """Keyboard for grading word difficulty"""
    builder = InlineKeyboardBuilder()
    
    # First row - grades 2 and 3
    builder.row(
        InlineKeyboardButton(text="😰 Трудно (2)", callback_data=f"grade_{word_id}_2"),
        InlineKeyboardButton(text="😐 Сложно (3)", callback_data=f"grade_{word_id}_3")
    )
    
    # Second row - grades 4 and 5
    builder.row(
        InlineKeyboardButton(text="😊 Хорошо (4)", callback_data=f"grade_{word_id}_4"),
        InlineKeyboardButton(text="🎉 Легко (5)", callback_data=f"grade_{word_id}_5")
    )
    
    return builder.as_markup()

def get_stop_session_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with stop session button"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⏹️ Стоп", 
        callback_data="stop_session"
    )
    return builder.as_markup()

def get_continue_stop_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with continue and stop options"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_session"),
        InlineKeyboardButton(text="⏹️ Стоп", callback_data="stop_session")
    )
    return builder.as_markup()

def get_confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """Generic confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")
    )
    return builder.as_markup()

def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Skip keyboard for FSM states"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="⏭️ Пропустить")
    builder.button(text="🔙 Назад в меню")
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def remove_keyboard() -> ReplyKeyboardMarkup:
    """Remove keyboard"""
    return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)

def get_session_info_keyboard(stats: dict) -> InlineKeyboardMarkup:
    """Keyboard for session information display"""
    builder = InlineKeyboardBuilder()
    
    if stats.get('due', 0) > 0:
        builder.button(
            text=f"📚 Продолжить ({stats['due']} слов)", 
            callback_data="continue_review"
        )
    
    if stats.get('new', 0) > 0:
        builder.button(
            text=f"🎓 Новые слова ({stats['new']} слов)", 
            callback_data="start_learning"
        )
    
    builder.button(
        text="➕ Добавить слово", 
        callback_data="add_word"
    )
    
    builder.button(
        text="📊 Статистика", 
        callback_data="show_stats"
    )
    
    # Arrange buttons in rows
    builder.adjust(1)  # One button per row
    
    return builder.as_markup()

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for statistics screen"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 Главное меню", 
        callback_data="main_menu"
    )
    return builder.as_markup()

def get_learning_complete_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when learning session is complete"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 Повторить", callback_data="continue_review"),
        InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")
    )
    return builder.as_markup()