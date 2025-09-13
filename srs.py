import time
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class SRSCalculator:
    """Classic SM-2 algorithm with daily intervals"""
    
    MIN_EF = 1.3
    INITIAL_EF = 2.5
    SECONDS_PER_DAY = 86400
    
    @staticmethod
    def calculate_next_review(current_progress: Dict, grade: int) -> Tuple[Dict, int]:
        """
        Calculate next review time based on SM-2 algorithm with grade (0-5)
        Returns: (updated_progress, next_interval_days)
        """
        ef = current_progress.get('ef', SRSCalculator.INITIAL_EF)
        repetition = current_progress.get('repetition', 0)
        # For backward compatibility, ignore old interval_sec field
        current_time = int(time.time())
        
        # Update EF based on grade using SM-2 formula
        ef = ef + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
        
        # Ensure EF doesn't go below minimum
        ef = max(ef, SRSCalculator.MIN_EF)
        
        # Calculate next interval based on SM-2 algorithm
        if grade < 3:
            # Poor grade - reset to beginning
            repetition = 0
            interval_days = 1
            status = 'learning'
        else:
            # Good grade - progress forward
            repetition += 1
            
            if repetition == 1:
                interval_days = 1
                status = 'learning'
            elif repetition == 2:
                interval_days = 6
                status = 'learning'
            else:
                # repetition >= 3: use EF-based calculation
                previous_interval_days = current_progress.get('interval_days', 6)
                interval_days = round(previous_interval_days * ef)
                status = 'review'
        
        # Calculate next review timestamp (convert days to seconds)
        interval_seconds = interval_days * SRSCalculator.SECONDS_PER_DAY
        next_review_ts = current_time + interval_seconds
        
        # Update progress with new fields
        updated_progress = {
            'ef': round(ef, 2),
            'repetition': repetition,
            'interval_days': interval_days,
            'next_review_ts': next_review_ts,
            'last_grade': grade,
            'last_review_ts': current_time,
            'status': status
        }
        
        logger.info(f"SM-2 Update: grade={grade}, rep={repetition}, interval={interval_days}d, ef={ef:.2f}")
        
        return updated_progress, interval_days
    
    @staticmethod
    def is_due(word_progress: Dict) -> bool:
        """Check if word is due for review"""
        next_review_ts = word_progress.get('next_review_ts', 0)
        current_time = int(time.time())
        return current_time >= next_review_ts
    
    @staticmethod
    def get_due_words(user_progress: Dict) -> list:
        """Get list of word IDs that are due for review"""
        words_progress = user_progress.get('words', {})
        due_words = []
        
        current_time = int(time.time())
        
        for word_id, progress in words_progress.items():
            next_review_ts = progress.get('next_review_ts', 0)
            if current_time >= next_review_ts:
                due_words.append(word_id)
        
        logger.info(f"Found {len(due_words)} due words")
        return due_words
    
    @staticmethod
    def get_new_words(user_progress: Dict, limit: int = 5) -> list:
        """Get list of new word IDs (not yet studied)"""
        words_progress = user_progress.get('words', {})
        new_words = []
        
        for word_id, progress in words_progress.items():
            if progress.get('status') == 'new':
                new_words.append(word_id)
                if len(new_words) >= limit:
                    break
        
        logger.info(f"Found {len(new_words)} new words (limit: {limit})")
        return new_words
    
    @staticmethod
    def format_interval(days: int) -> str:
        """Format interval in human-readable form"""
        if days == 1:
            return "1 день"
        elif days < 7:
            return f"{days} дней"
        elif days < 30:
            weeks = days // 7
            remaining_days = days % 7
            if remaining_days == 0:
                return f"{weeks} нед."
            else:
                return f"{weeks} нед. {remaining_days} дн."
        elif days < 365:
            months = days // 30
            remaining_days = days % 30
            if remaining_days == 0:
                return f"{months} мес."
            else:
                return f"{months} мес. {remaining_days} дн."
        else:
            years = days // 365
            remaining_days = days % 365
            if remaining_days == 0:
                return f"{years} г."
            else:
                return f"{years} г. {remaining_days} дн."
    
    @staticmethod
    def get_stats(user_progress: Dict) -> Dict:
        """Get learning statistics for user"""
        words_progress = user_progress.get('words', {})
        
        stats = {
            'total': len(words_progress),
            'new': 0,
            'learning': 0,
            'review': 0,
            'due': 0
        }
        
        current_time = int(time.time())
        
        for progress in words_progress.values():
            status = progress.get('status', 'new')
            stats[status] = stats.get(status, 0) + 1
            
            if current_time >= progress.get('next_review_ts', 0):
                stats['due'] += 1
        
        return stats