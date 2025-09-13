# LearnIt - Telegram Bot for Learning Words

A Telegram bot for spaced repetition learning using SM-2 algorithm (like Anki).

## Features

- 📚 Spaced repetition learning with SM-2 algorithm
- 🎯 Daily learning goals
- 📊 Progress tracking and statistics
- ⏰ Automatic review scheduling
- 🔄 Queue management for overdue cards
- 📱 User-friendly Telegram interface

## Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your bot token
4. Run: `python main.py`

## Deployment

### Railway (Recommended - Free)

1. Push code to GitHub/GitLab
2. Go to [Railway.app](https://railway.app)
3. Connect your repository
4. Add environment variable: `BOT_TOKEN=your_bot_token`
5. Deploy automatically

### Render (Free)

1. Push code to GitHub
2. Go to [Render.com](https://render.com) 
3. Create new Web Service
4. Connect repository
5. Set environment: `BOT_TOKEN=your_bot_token`
6. Deploy

### Heroku (Free tier discontinued)

Use Railway or Render instead.

## Environment Variables

- `BOT_TOKEN` - Your Telegram bot token from @BotFather

## File Structure

- `main.py` - Main bot logic
- `srs.py` - SM-2 spaced repetition algorithm  
- `storage.py` - Data persistence
- `queue_manager.py` - Card queue management
- `keyboards.py` - Telegram keyboards
- `states.py` - FSM states
- `data/` - JSON data files (created automatically)

## Algorithm

Uses the SM-2 spaced repetition algorithm:
- First review: 1 day
- Second review: 6 days  
- Subsequent reviews: previous_interval × ease_factor
- Ease factor adjusts based on answer quality (0-5)