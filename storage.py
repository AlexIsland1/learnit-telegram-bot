import json
import os
import tempfile
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class JSONStorage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.words_file = os.path.join(data_dir, "words.json")
        self.progress_file = os.path.join(data_dir, "progress.json")
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize files if they don't exist
        self._init_files()
    
    def _init_files(self):
        """Initialize JSON files with default structure"""
        if not os.path.exists(self.words_file):
            self._write_json(self.words_file, [])
            logger.info(f"Initialized empty words file: {self.words_file}")
        
        if not os.path.exists(self.progress_file):
            self._write_json(self.progress_file, {})
            logger.info(f"Initialized empty progress file: {self.progress_file}")
    
    def _read_json(self, filepath: str) -> Any:
        """Safely read JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading {filepath}: {e}")
            return [] if 'words' in filepath else {}
    
    def _write_json(self, filepath: str, data: Any):
        """Atomically write JSON file using temporary file and rename"""
        try:
            # Create temporary file in same directory
            temp_dir = os.path.dirname(filepath)
            with tempfile.NamedTemporaryFile(
                mode='w', 
                encoding='utf-8', 
                dir=temp_dir, 
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                json.dump(data, tmp_file, ensure_ascii=False, indent=2)
                temp_path = tmp_file.name
            
            # Atomic rename
            if os.name == 'nt':  # Windows
                if os.path.exists(filepath):
                    os.remove(filepath)
            os.rename(temp_path, filepath)
            
            logger.debug(f"Successfully wrote {filepath}")
            
        except Exception as e:
            logger.error(f"Error writing {filepath}: {e}")
            # Cleanup temp file if exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise
    
    def load_words(self) -> List[Dict]:
        """Load all words"""
        return self._read_json(self.words_file)
    
    def save_words(self, words: List[Dict]):
        """Save words list"""
        self._write_json(self.words_file, words)
    
    def add_word(self, word: str, translation: str) -> str:
        """Add new word and return generated ID"""
        words = self.load_words()
        
        # Generate new ID
        existing_ids = [w.get('id', '') for w in words]
        new_id = f"w{len(words) + 1}"
        while new_id in existing_ids:
            new_id = f"w{len(words) + len(existing_ids) + 1}"
        
        new_word = {
            "id": new_id,
            "word": word,
            "translation": translation
        }
        
        words.append(new_word)
        self.save_words(words)
        
        logger.info(f"Added new word: {new_id} - {word}: {translation}")
        return new_id
    
    def get_word_by_id(self, word_id: str) -> Dict | None:
        """Get word by ID"""
        words = self.load_words()
        for word in words:
            if word.get('id') == word_id:
                return word
        return None
    
    def load_progress(self) -> Dict:
        """Load user progress data"""
        return self._read_json(self.progress_file)
    
    def save_progress(self, progress: Dict):
        """Save progress data"""
        self._write_json(self.progress_file, progress)
    
    def get_user_progress(self, user_id: int) -> Dict:
        """Get progress for specific user"""
        progress = self.load_progress()
        user_key = str(user_id)
        return progress.get(user_key, {})
    
    def update_user_progress(self, user_id: int, user_data: Dict):
        """Update progress for specific user"""
        progress = self.load_progress()
        user_key = str(user_id)
        progress[user_key] = user_data
        self.save_progress(progress)
    
    def init_word_progress(self, user_id: int, word_id: str):
        """Initialize progress for a new word"""
        user_progress = self.get_user_progress(user_id)
        
        if 'words' not in user_progress:
            user_progress['words'] = {}
        
        if word_id not in user_progress['words']:
            user_progress['words'][word_id] = {
                'ef': 2.5,
                'repetition': 0,
                'interval_days': 1,
                'next_review_ts': 0,
                'last_grade': 0,
                'last_review_ts': 0,
                'status': 'new'
            }
        
        # Initialize session state if not exists
        if 'session' not in user_progress:
            user_progress['session'] = {
                'active': False,
                'current_word': None,
                'mode': None,
                'waiting_for_answer': False,
                'due_queue': []
            }
        
        # Initialize daily learning state
        if 'daily_learning' not in user_progress:
            user_progress['daily_learning'] = {
                'last_date': '',
                'words_learned_today': 0,
                'daily_goal': 5
            }
        
        self.update_user_progress(user_id, user_progress)
        logger.info(f"Initialized progress for user {user_id}, word {word_id}")
    
    def get_word_progress(self, user_id: int, word_id: str) -> Dict:
        """Get progress for specific word"""
        user_progress = self.get_user_progress(user_id)
        return user_progress.get('words', {}).get(word_id, {})
    
    def update_word_progress(self, user_id: int, word_id: str, word_data: Dict):
        """Update progress for specific word"""
        user_progress = self.get_user_progress(user_id)
        
        if 'words' not in user_progress:
            user_progress['words'] = {}
        
        user_progress['words'][word_id] = word_data
        self.update_user_progress(user_id, user_progress)