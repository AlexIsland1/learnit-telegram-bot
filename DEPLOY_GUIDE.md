# 🚀 ПОЛНОЕ РУКОВОДСТВО ПО ДЕПЛОЮ

## Шаг 1: Инициализация Git (выполните в папке проекта)

```bash
git init
git add .
git commit -m "Initial commit: Telegram bot for spaced repetition learning"
```

## Шаг 2: Создание GitHub репозитория

1. Идите на https://github.com
2. Нажмите "New repository"
3. Название: `learnit-telegram-bot`
4. Описание: `Telegram bot for spaced repetition learning with SM-2 algorithm`
5. Public/Private - на ваш выбор
6. НЕ создавайте README, .gitignore, license (уже есть в проекте)
7. Нажмите "Create repository"

## Шаг 3: Загрузка кода на GitHub

Скопируйте команды которые GitHub покажет после создания репозитория:

```bash
git remote add origin https://github.com/YOUR_USERNAME/learnit-telegram-bot.git
git branch -M main
git push -u origin main
```

## Шаг 4: Деплой на Railway

1. Идите на https://railway.app
2. Нажмите "Start a New Project"
3. Выберите "Deploy from GitHub repo"
4. Найдите и выберите ваш репозиторий `learnit-telegram-bot`
5. Railway автоматически определит Python проект

## Шаг 5: Настройка переменных окружения

В Railway проекте:
1. Перейдите в "Variables" 
2. Добавьте переменную:
   - **Name**: `BOT_TOKEN`
   - **Value**: `ваш_токен_от_BotFather`

## Шаг 6: Деплой

Railway автоматически задеплоит после добавления переменной.
Статус можно отслеживать в разделе "Deployments".

## 🎉 ГОТОВО!

Ваш бот будет работать 24/7 на Railway!

## Альтернативные платформы:

### Render.com:
1. https://render.com → New Web Service
2. Connect GitHub repo
3. Add environment variable: `BOT_TOKEN`

### Fly.io:
```bash
flyctl launch
flyctl secrets set BOT_TOKEN=your_token
flyctl deploy
```

## Проверка работы:

После деплоя найдите вашего бота в Telegram и отправьте `/start`