@echo off
echo ========================================
echo   АВТОМАТИЧЕСКИЙ ДЕПЛОЙ LEARNIT BOT
echo ========================================
echo.

REM Проверяем есть ли git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git не найден! Установите Git: https://git-scm.com/
    pause
    exit /b 1
)

echo ✅ Git найден
echo.

REM Инициализируем git если нужно
if not exist .git (
    echo 📦 Инициализация Git репозитория...
    git init
    git add .
    git commit -m "Initial commit: Telegram bot for spaced repetition learning with SM-2 algorithm

Features:
- SM-2 spaced repetition algorithm like Anki
- Queue management for overdue cards
- Daily learning goals and progress tracking
- Automatic review scheduling
- Telegram bot interface
- JSON data persistence

Ready for deployment on Railway/Render/Fly.io"
    echo ✅ Git репозиторий создан
) else (
    echo ℹ️  Git репозиторий уже существует
)

echo.
echo 🚀 Следующие шаги для деплоя:
echo.
echo 1️⃣  Создайте репозиторий на GitHub:
echo     https://github.com/new
echo     Название: learnit-telegram-bot
echo.
echo 2️⃣  Выполните команды (замените YOUR_USERNAME):
echo     git remote add origin https://github.com/YOUR_USERNAME/learnit-telegram-bot.git
echo     git branch -M main
echo     git push -u origin main
echo.
echo 3️⃣  Деплой на Railway:
echo     https://railway.app
echo     → Start New Project → Deploy from GitHub
echo     → Выберите ваш репозиторий
echo     → Variables → добавьте BOT_TOKEN=ваш_токен
echo.
echo 4️⃣  Альтернативно - Render.com:
echo     https://render.com → New Web Service
echo     → Connect Repository → Environment: BOT_TOKEN
echo.
echo 📋 Подробная инструкция в файле DEPLOY_GUIDE.md
echo.
echo 🤖 Получить токен бота: https://t.me/BotFather
echo.

pause