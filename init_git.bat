@echo off
echo Initializing Git repository...

git init
git add .
git commit -m "Initial commit: Telegram bot for spaced repetition learning

Features:
- SM-2 algorithm for spaced repetition
- Queue management for overdue cards  
- Daily learning goals
- Progress tracking
- Telegram bot interface

Ready for deployment on Railway/Render"

echo.
echo Git repository initialized!
echo.
echo Next steps:
echo 1. Create repository on GitHub/GitLab
echo 2. git remote add origin [your-repo-url]
echo 3. git push -u origin main
echo.
echo For Railway deployment:
echo 1. Go to railway.app
echo 2. Connect your repository
echo 3. Set BOT_TOKEN environment variable
echo 4. Deploy!

pause