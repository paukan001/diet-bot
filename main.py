import telebot
from telebot import types
import csv
import random
import os
from datetime import datetime
from openai import OpenAI

# ============================================================
# 1. НАСТРОЙКИ И ПРОВЕРКА ПЕРЕМЕННЫХ
# ============================================================

TOKEN = os.environ.get('BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

if not TOKEN:
    print("❌ ОШИБКА: Переменная окружения BOT_TOKEN не найдена!")
if not DEEPSEEK_API_KEY:
    print("❌ ОШИБКА: Переменная окружения DEEPSEEK_API_KEY не найдена!")

bot = telebot.TeleBot(TOKEN)
users_data = {}
user_states = {}

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ============================================================
# 2. КЛАВИАТУРА
# ============================================================
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📋 Меню на день"),
        types.KeyboardButton("📅 Меню на неделю")
    )
    markup.add(
        types.KeyboardButton("🔍 Случайный рецепт"),
        types.KeyboardButton("🛒 Список покупок")
    )
    markup.add(
        types.KeyboardButton("🤖 ИИ-помощник"),
        types.KeyboardButton("💪 Мотивация")
    )
    markup.add(
        types.KeyboardButton("📊 Мой прогресс"),
        types.KeyboardButton("ℹ️ О диете")
    )
    markup.add(
        types.KeyboardButton("🍳 Завтрак"),
        types.KeyboardButton("🍲 Обед")
    )
    markup.add(
        types.KeyboardButton("🌙 Ужин"),
        types.KeyboardButton("🍎 Перекус")
    )
    return markup

# ============================================================
# 3. ЗАГРУЗКА РЕЦЕПТОВ (UTF-8 для сервера)
# ============================================================
def load_recipes(filename='recipes.csv'):
    recipes = []
    try:
        # ВАЖНО: На серверах используется utf-8. Убедись, что твой CSV сохранен в UTF-8
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                clean_row = {k.strip().strip('"'): v.strip().strip('"') if v else '' for k, v in row.items()}
                recipes.append(clean_row)
        print(f"✅ Успешно загружено {len(recipes)} рецептов")
        return recipes
    except FileNotFoundError:
        print("⚠️ Файл recipes.csv не найден! Бот будет работать без базы рецептов.")
        return []
    except Exception as e:
        print(f"⚠️ Ошибка чтения CSV: {e}")
        return []

all_recipes = load_recipes()

# ============================================================
# 4. БАЗЫ ДАННЫХ И КОНСТАНТЫ
# ============================================================
MOTIVATION_PHRASES = [
    "💪 Каждый день на столе №5 — это вклад в твоё будущее.",
    "🌟 Через 2 недели на диете печень начинает активно восстанавливаться!",
    "🌱 Здоровое питание — это забота о себе. Ты выбираешь себя!",
    "Маленькие шаги каждый день приводят к большим результатам.",
    "Ты делаешь это для себя и тех, кто тебя любит. Ты важна!"
]

DIET_INFO = """
📋 *Стол №5 — что это такое?*
Диета для печени, желчного пузыря и поджелудочной.
✅ *Можно:* вареное, запеченное, на пару, нежирное мясо, рыбу, овощи, крупы.
❌ *Нельзя:* жареное, жирное, острое, копчёное, свежую выпечку, шоколад, кофе.
"""

# ============================================================
# 5. ФУНКЦИИ ИИ (DEEPSEEK)
# ============================================================
def ask_deepseek_for_recipe(ingredients_text):
    system_prompt = """Ты - опытный диетолог и шеф-повар, специализирующийся на лечебном "Столе №5".
    СТРОГИЕ ПРАВИЛА: НЕЛЬЗЯ жареное, жирное, острое, копченое, свежую выпечку, шоколад, кофе, бобовые, грибы.
    МОЖНО: вареное, запеченное без корочки, на пару. Нежирное мясо, рыба, овощи, крупы.
    Предложи 1 вкусный и простой рецепт из продуктов пользователя.
    Формат:
    🍲 *Название блюда*
    🛒 *Ингредиенты:* (с граммовкой)
    👨‍🍳 *Приготовление:* (пошагово)
    🔥 *Калорийность:* (примерно)
    Отвечай тепло и мотивирующе."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"У меня есть: {ingredients_text}. Что приготовить по Столу №5?"}
            ],
            temperature=0.7,
            timeout=30 # Защита от зависания запроса к API
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Ошибка ИИ: {e}. Проверь API ключ или попробуй позже."

# ============================================================
# 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def get_recipes_by_meal(meal_type):
    return [r for r in all_recipes if r.get('Прием пищи') == meal_type]

def format_recipe(recipe):
    if not recipe: return "Рецепт не найден."
    msg = f"🍽 *{recipe.get('Название', 'Без названия')}*\n\n"
    msg += f"🛒 *Ингредиенты:*\n{recipe.get('Ингредиенты', 'Не указаны')}\n\n"
    msg += f"👨‍🍳 *Приготовление:*\n{recipe.get('Инструкция', 'Не указано')}\n\n"
    msg += f"⏱ *Время:* {recipe.get('Время приготовления', '?')}\n"
    msg += f"🔥 *Калорийность:* {recipe.get('Калорийность (ккал)', '?')} ккал"
    return msg

def generate_daily_menu():
    meals = ['Завтрак', 'Обед', 'Ужин', 'Перекус']
    menu = {}
    for meal in meals:
        recipes = get_recipes_by_meal(meal)
        if recipes:
            menu[meal] = random.choice(recipes)
    return menu if len(menu) == 4 else None

def categorize_ingredient(ingredient):
    ing = ingredient.lower()
    if any(w in ing for w in ['огурец', 'помидор', 'морковь', 'лук', 'капуста', 'свекла', 'тыква', 'кабачок', 'перец', 'брокколи', 'шпинат', 'зелень']): return '🥦 Овощи и зелень'
    if any(w in ing for w in ['яблоко', 'банан', 'киви', 'груша', 'апельсин', 'ягоды']): return '🍎 Фрукты и ягоды'
    if any(w in ing for w in ['куриц', 'индейк', 'говядин', 'фарш', 'печень']): return '🍗 Мясо и птица'
    if any(w in ing for w in ['рыб', 'хек', 'треск', 'лосось', 'судак', 'форель', 'креветк']): return '🐟 Рыба и морепродукты'
    if any(w in ing for w in ['творог', 'молоко', 'кефир', 'йогурт', 'сыр', 'сливк', 'сметана']): return '🥛 Молочные продукты'
    if 'яйц' in ing or 'яйцо' in ing: return '🥚 Яйца'
    if any(w in ing for w in ['овсян', 'гречк', 'рис', 'булгур', 'пшен', 'вермишел', 'макарон']): return '🌾 Крупы и злаки'
    if any(w in ing for w in ['хлеб', 'тост', 'хлебец']): return '🍞 Хлеб и выпечка'
    if any(w in ing for w in ['масло', 'оливков', 'сливочн']): return '🫙 Масла и жиры'
    if any(w in ing for w in ['орех', 'миндаль', 'кешью', 'семен', 'чиа', 'лён', 'кунжут']): return '🥜 Орехи и семена'
    if any(w in ing for w in ['томат', 'соус', 'бульон', 'желатин', 'крахмал', 'мука', 'сахар', 'корица', 'соль', 'перец', 'лимон']): return '🧂 Бакалея и специи'
    return '📦 Другое'

def generate_weekly_shopping_list():
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    all_ingredients = []
    for day in days:
        menu = generate_daily_menu()
        if menu:
            for recipe in menu.values():
                if recipe and 'Ингредиенты' in recipe and recipe['Ингредиенты']:
                    all_ingredients.extend([i.strip() for i in recipe['Ингредиенты'].split(';') if i.strip()])

    if not all_ingredients: return None, None

    categorized = {}
    for ing in all_ingredients:
        cat = categorize_ingredient(ing)
        categorized.setdefault(cat, []).append(ing)

    shopping_list = "🛒 *СПИСОК ПОКУПОК НА НЕДЕЛЮ*\n\n"
    for cat in sorted(categorized.keys()):
        shopping_list += f"*{cat}:*\n"
        for ing in sorted(set(categorized[cat])):
            shopping_list += f"  • {ing}\n"
        shopping_list += "\n"
    return shopping_list, None # Упростил возврат, weekly_menu не использовался

def get_user_data(user_id):
    if user_id not in users_data:
        users_data[user_id] = {'name': None, 'start_date': None}
    return users_data[user_id]

# ============================================================
# 7. ОБРАБОТЧИКИ КОМАНД
# ============================================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data = get_user_data(message.from_user.id)
    user_name = message.from_user.first_name or "друг"
    user_data['name'] = user_name
    if not user_data['start_date']:
        user_data['start_date'] = datetime.now()

    text = f"Привет, {user_name}! 👋\n\nЯ твой диетический помощник по *столу №5*. Помогу питаться вкусно и правильно! 🥗\n\nИспользуй кнопки внизу экрана:"
    bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['info'])
def send_info(message):
    bot.send_message(message.chat.id, DIET_INFO, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['day'])
def send_daily_menu(message):
    menu = generate_daily_menu()
    if not menu:
        bot.reply_to(message, "⚠️ Не удалось сгенерировать меню. Проверь файл recipes.csv.", reply_markup=get_main_keyboard())
        return
    msg = "📋 *Меню на сегодня:*\n\n"
    total_cal = 0
    for meal, recipe in menu.items():
        cal_str = recipe.get('Калорийность (ккал)', '0')
        cal = int(''.join(filter(str.isdigit, cal_str))) if cal_str else 0
        total_cal += cal
        msg += f"*{meal}:* {recipe.get('Название', 'Блюдо')} ({cal} ккал)\n"
    msg += f"\n🔥 *Итого:* {total_cal} ккал"
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['week'])
def send_weekly_menu(message):
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    msg = "📅 *Меню на неделю:*\n\n"
    for day in days:
        menu = generate_daily_menu()
        if menu:
            msg += f"*{day}:*\n"
            for meal, recipe in menu.items():
                msg += f"  • {meal}: {recipe.get('Название', 'Блюдо')}\n"
            msg += "\n"
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['shopping'])
def send_shopping_list_only(message):
    bot.reply_to(message, "⏳ Собираю список покупок...", reply_markup=get_main_keyboard())
    shopping_list, _ = generate_weekly_shopping_list()
    if not shopping_list:
        bot.send_message(message.chat.id, "😕 Не удалось сформировать список. Проверь базу рецептов.", reply_markup=get_main_keyboard())
        return
    bot.send_message(message.chat.id, shopping_list, reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['recipe'])
def send_recipe_search(message):
    if not all_recipes:
        bot.reply_to(message, "😕 База рецептов пуста. Загрузи файл recipes.csv на сервер.", reply_markup=get_main_keyboard())
        return
    bot.send_message(message.chat.id, format_recipe(random.choice(all_recipes)), reply_markup=get_main_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['motivation'])
def send_motivation(message):
    bot.reply_to(message, random.choice(MOTIVATION_PHRASES), reply_markup=get_main_keyboard())

@bot.message_handler(commands=['progress'])
def send_progress(message):
    user_data = get_user_data(message.from_user.id)
    if user_data['start_date']:
        days = (datetime.now() - user_data['start_date']).days + 1
        msg = f"📊 *Твой прогресс:*\nТы на диете уже *{days} дн.*\n"
        if days < 7: msg += "💪 Первая неделя — самая важная!"
        elif days < 14: msg += "🔥 Отлично! Печень начинает восстанавливаться!"
        else: msg += "⭐ Ты уже в ритме! Так держать!"
    else:
        msg = "📊 Нажми /start, чтобы начать отсчет!"
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# ============================================================
# 8. ОБРАБОТЧИК ТЕКСТА
# ============================================================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip()
    user_id = message.from_user.id

    if user_states.get(user_id) == 'waiting_for_ingredients':
        bot.send_chat_action(message.chat.id, 'typing')
        ai_response = ask_deepseek_for_recipe(text)
        bot.send_message(message.chat.id, ai_response, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        user_states[user_id] = None
        return

    if text in ["📋 Меню на день", "Меню на день"]: send_daily_menu(message)
    elif text in ["📅 Меню на неделю", "Меню на неделю"]: send_weekly_menu(message)
    elif text in ["🔍 Случайный рецепт", "Случайный рецепт"]: send_recipe_search(message)
    elif text in ["🛒 Список покупок", "Список покупок"]: send_shopping_list_only(message)
    elif text in ["💪 Мотивация", "Мотивация"]: send_motivation(message)
    elif text in ["📊 Мой прогресс", "Мой прогресс"]: send_progress(message)
    elif text in ["ℹ️ О диете", "О диете"]: send_info(message)
    elif text in ["🍳 Завтрак", "Завтрак"]:
        recipes = get_recipes_by_meal('Завтрак')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🍲 Обед", "Обед"]:
        recipes = get_recipes_by_meal('Обед')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🌙 Ужин", "Ужин"]:
        recipes = get_recipes_by_meal('Ужин')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🍎 Перекус", "Перекус"]:
        recipes = get_recipes_by_meal('Перекус')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🤖 ИИ-помощник", "ИИ-помощник"]:
        user_states[user_id] = 'waiting_for_ingredients'
        bot.send_message(message.chat.id, "🤖 *ИИ-помощник активирован!*\n\nНапиши продукты (например: 'курица, кабачок, рис'), и я придумаю рецепт для Стола №5!", reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        found = [r for r in all_recipes if text.lower() in r.get('Название', '').lower()]
        if found:
            bot.send_message(message.chat.id, format_recipe(found[0]), reply_markup=get_main_keyboard(), parse_mode='Markdown')
        else:
            bot.reply_to(message, f"🤔 Не нашёл \"{text}\".\nПопробуй написать часть названия или нажми кнопку.", reply_markup=get_main_keyboard())

# ============================================================
# 9. ЗАПУСК
# ============================================================
if __name__ == '__main__':
    print("🚀 Бот запускается...")
    print(f"📚 Рецептов в базе: {len(all_recipes)}")
    if TOKEN and DEEPSEEK_API_KEY:
        print("✅ Ключи загружены. Подключаемся к Telegram и DeepSeek...")
        bot.infinity_polling(timeout=60) # timeout=60 критически важен для стабильности на сервере
    else:
        print("❌ Запуск прерван: отсутствуют переменные окружения.")
