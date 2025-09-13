import logging
from datetime import datetime, timedelta
from typing import List, Optional
import pytz
from storage import JSONStorage

logger = logging.getLogger(__name__)

class DailyLearningManager:
    """Manages daily learning goals and progress"""
    
    def __init__(self, storage: JSONStorage, timezone=pytz.timezone('Asia/Tashkent')):
        self.storage = storage
        self.timezone = timezone
    
    def get_today_date(self) -> str:
        """Get today's date in YYYY-MM-DD format"""
        return datetime.now(self.timezone).strftime('%Y-%m-%d')
    
    def get_daily_progress(self, user_id: int) -> dict:
        """Get user's daily learning progress"""
        user_progress = self.storage.get_user_progress(user_id)
        daily_data = user_progress.get('daily_learning', {})
        
        today = self.get_today_date()
        last_date = daily_data.get('last_date', '')
        
        # Reset counter if new day
        if last_date != today:
            daily_data = {
                'last_date': today,
                'words_learned_today': 0,
                'daily_goal': daily_data.get('daily_goal', 5)
            }
            user_progress['daily_learning'] = daily_data
            self.storage.update_user_progress(user_id, user_progress)
            logger.info(f"Reset daily progress for user {user_id} (new day: {today})")
        
        return daily_data
    
    def get_new_words_for_today(self, user_id: int, limit: int = 5) -> List[str]:
        """Get list of new words that user should learn today"""
        try:
            # Get all words from database
            all_words = self.storage.load_words()
            user_progress = self.storage.get_user_progress(user_id)
            user_words = user_progress.get('words', {})
            
            # Find words that user hasn't started learning yet
            available_new_words = []
            for word in all_words:
                word_id = word['id']
                if word_id not in user_words or user_words[word_id].get('status') == 'new':
                    available_new_words.append(word_id)
            
            # Return up to limit words
            return available_new_words[:limit]
            
        except Exception as e:
            logger.error(f"Error getting new words for user {user_id}: {e}")
            return []
    
    def mark_word_learned_today(self, user_id: int):
        """Mark that user learned one word today"""
        try:
            daily_data = self.get_daily_progress(user_id)
            daily_data['words_learned_today'] += 1
            
            user_progress = self.storage.get_user_progress(user_id)
            user_progress['daily_learning'] = daily_data
            self.storage.update_user_progress(user_id, user_progress)
            
            learned = daily_data['words_learned_today']
            goal = daily_data['daily_goal']
            
            logger.info(f"User {user_id} learned word {learned}/{goal} today")
            
        except Exception as e:
            logger.error(f"Error marking word learned for user {user_id}: {e}")
    
    def is_daily_goal_reached(self, user_id: int) -> bool:
        """Check if user reached daily goal"""
        daily_data = self.get_daily_progress(user_id)
        return daily_data['words_learned_today'] >= daily_data['daily_goal']
    
    def get_daily_stats(self, user_id: int) -> dict:
        """Get comprehensive daily statistics"""
        try:
            daily_data = self.get_daily_progress(user_id)
            new_words_available = self.get_new_words_for_today(user_id, 50)  # Check more for total count
            
            learned_today = daily_data['words_learned_today']
            daily_goal = daily_data['daily_goal']
            remaining_today = max(0, daily_goal - learned_today)
            total_new_available = len(new_words_available)
            
            return {
                'learned_today': learned_today,
                'daily_goal': daily_goal,
                'remaining_today': remaining_today,
                'total_new_available': total_new_available,
                'goal_reached': learned_today >= daily_goal,
                'can_learn_more': total_new_available > 0 and learned_today < daily_goal
            }
            
        except Exception as e:
            logger.error(f"Error getting daily stats for user {user_id}: {e}")
            return {
                'learned_today': 0,
                'daily_goal': 5,
                'remaining_today': 5,
                'total_new_available': 0,
                'goal_reached': False,
                'can_learn_more': False
            }
    
    def schedule_daily_reminder(self, user_id: int, scheduler) -> bool:
        """Schedule daily reminder for tomorrow"""
        try:
            # Schedule for 9 AM tomorrow
            tomorrow = datetime.now(self.timezone) + timedelta(days=1)
            reminder_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            
            job_id = f"daily_reminder_{user_id}"
            
            # Remove existing job
            try:
                scheduler.remove_job(job_id)
            except:
                pass
            
            scheduler.add_job(
                self._send_daily_reminder,
                'date',
                run_date=reminder_time,
                args=[user_id],
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"Scheduled daily reminder for user {user_id} at {reminder_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling daily reminder for user {user_id}: {e}")
            return False
    
    async def _send_daily_reminder(self, user_id: int, bot):
        """Send daily learning reminder"""
        try:
            from keyboards import get_main_menu_keyboard
            
            stats = self.get_daily_stats(user_id)
            
            if stats['total_new_available'] > 0:
                await bot.send_message(
                    user_id,
                    f"🌅 Доброе утро!\n\n"
                    f"📚 Сегодня ваш план: {stats['daily_goal']} новых слов\n"
                    f"🎯 Доступно для изучения: {stats['total_new_available']} слов\n\n"
                    f"Нажмите '🎓 Готов к обучению' для начала!",
                    reply_markup=get_main_menu_keyboard()
                )
            
        except Exception as e:
            logger.error(f"Error sending daily reminder to user {user_id}: {e}")