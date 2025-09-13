from aiogram.fsm.state import State, StatesGroup

class AddWordStates(StatesGroup):
    """States for adding new words"""
    waiting_for_word = State()
    waiting_for_translation = State()
    
class SessionStates(StatesGroup):
    """States for learning sessions"""
    reviewing = State()
    learning_new = State()
    waiting_for_check = State()
    waiting_for_grade = State()
    session_paused = State()