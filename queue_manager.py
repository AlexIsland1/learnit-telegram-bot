import logging
import time
from typing import List, Optional
from storage import JSONStorage

logger = logging.getLogger(__name__)

class DueCardQueue:
    """Manages queue of due cards for each user"""
    
    def __init__(self, storage: JSONStorage):
        self.storage = storage
    
    def add_to_queue(self, user_id: int, word_id: str) -> bool:
        """Add word to due queue if user is not busy"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            
            # Initialize queue if not exists
            if 'due_queue' not in session:
                session['due_queue'] = []
            
            # Check if user is waiting for answer
            if session.get('waiting_for_answer', False):
                # Add to queue
                if word_id not in session['due_queue']:
                    session['due_queue'].append(word_id)
                    user_progress['session'] = session
                    self.storage.update_user_progress(user_id, user_progress)
                    logger.info(f"Added {word_id} to queue for user {user_id} (queue size: {len(session['due_queue'])})")
                return False  # Don't send now
            else:
                # User is free, can send immediately
                session['waiting_for_answer'] = True
                user_progress['session'] = session
                self.storage.update_user_progress(user_id, user_progress)
                logger.info(f"Sending {word_id} immediately to user {user_id}")
                return True  # Send now
                
        except Exception as e:
            logger.error(f"Error adding to queue for user {user_id}: {e}")
            return True  # Fallback to sending

    def force_add_to_queue(self, user_id: int, word_id: str) -> None:
        """Force add word to queue regardless of user state"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            
            # Initialize queue if not exists
            if 'due_queue' not in session:
                session['due_queue'] = []
            
            # Add to queue if not already there
            if word_id not in session['due_queue']:
                session['due_queue'].append(word_id)
                user_progress['session'] = session
                self.storage.update_user_progress(user_id, user_progress)
                logger.info(f"Force added {word_id} to queue for user {user_id} (queue size: {len(session['due_queue'])})")
                
        except Exception as e:
            logger.error(f"Error force adding to queue for user {user_id}: {e}")
    
    def get_next_from_queue(self, user_id: int) -> Optional[str]:
        """Get next word from queue and remove it"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            due_queue = session.get('due_queue', [])
            
            if due_queue:
                next_word = due_queue.pop(0)  # FIFO
                session['due_queue'] = due_queue
                session['waiting_for_answer'] = True
                user_progress['session'] = session
                self.storage.update_user_progress(user_id, user_progress)
                
                logger.info(f"Retrieved {next_word} from queue for user {user_id} (remaining: {len(due_queue)})")
                return next_word
            else:
                # No more cards in queue
                session['waiting_for_answer'] = False
                user_progress['session'] = session
                self.storage.update_user_progress(user_id, user_progress)
                logger.info(f"Queue empty for user {user_id}, user is now free")
                return None
                
        except Exception as e:
            logger.error(f"Error getting next from queue for user {user_id}: {e}")
            return None
    
    def mark_answered(self, user_id: int) -> Optional[str]:
        """Mark current card as answered and get next from queue"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            
            # Get next card from queue
            next_word = self.get_next_from_queue(user_id)
            
            if next_word:
                logger.info(f"User {user_id} answered, sending next card: {next_word}")
                return next_word
            else:
                logger.info(f"User {user_id} answered, no more cards in queue")
                return None
                
        except Exception as e:
            logger.error(f"Error marking answered for user {user_id}: {e}")
            return None
    
    def clear_queue(self, user_id: int):
        """Clear user's queue (e.g., when they start a session)"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            
            cleared_count = len(session.get('due_queue', []))
            session['due_queue'] = []
            session['waiting_for_answer'] = False
            
            user_progress['session'] = session
            self.storage.update_user_progress(user_id, user_progress)
            
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} cards from queue for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error clearing queue for user {user_id}: {e}")
    
    def get_queue_size(self, user_id: int) -> int:
        """Get current queue size for user"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            return len(session.get('due_queue', []))
        except:
            return 0
    
    def is_user_busy(self, user_id: int) -> bool:
        """Check if user is waiting for answer"""
        try:
            user_progress = self.storage.get_user_progress(user_id)
            session = user_progress.get('session', {})
            return session.get('waiting_for_answer', False)
        except:
            return False