import telebot
from telebot import types
import csv
import random
from datetime import datetime
from openai import OpenAI

# ============================================================
# 1. НАСТРОЙКИ БОТА
# ============================================================
import os

TOKEN = os.environ.get('BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

bot = telebot.TeleBot(TOKEN)
users_data = {}
user_states = {}  # Для отслеживания состояний (например, когда ждем продукты для ИИ)

# Настройка клиента DeepSeek (он совместим с OpenAI)
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
        types.KeyboardButton("🛒 Список покупок")  # ИСПРАВЛЕНО: добавлен эмодзи
    )
    markup.add(
        types.KeyboardButton("🤖 ИИ-помощник"),  # НОВАЯ КНОПКА
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
# 3. ЗАГРУЗКА РЕЦЕПТОВ
# ============================================================

def load_recipes(filename='recipes.csv'):
    recipes = []
    try:
        with open(filename, mode='r', encoding='cp1251') as file:
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                clean_row = {k.strip().strip('"'): v.strip().strip('"') if v else '' for k, v in row.items()}
                recipes.append(clean_row)
        print(f"✅ Загружено {len(recipes)} рецептов")
        return recipes
    except FileNotFoundError:
        print("⚠️ Файл recipes.csv не найден!")
        return []


all_recipes = load_recipes()

# ============================================================
# 4. БАЗЫ ДАННЫХ
# ============================================================

MOTIVATION_PHRASES = [
    "💪 Маша, ты уже делаешь огромный шаг к здоровью! Каждый день на столе №5 — это вклад в твоё будущее.",
    "🌟 Знаешь ли ты, что через 2 недели на диете печень начинает активно восстанавливаться? Ты на правильном пути!",
    "🌱 Здоровое питание — это не ограничение, а забота о себе. Ты выбираешь себя, и это прекрасно.",
    " Маленькие шаги каждый день приводят к большим результатам. Ты уже молодец!",
    " Ты делаешь это не только для себя, но и для тех, кто тебя любит. Ты важна!"
]

DIET_INFO = """
📋 *Стол №5 — что это такое?*
Это лечебная диета для печени, желчного пузыря и поджелудочной.
✅ *Можно:* вареное, запеченное, на пару, нежирное мясо, рыбу, овощи, крупы.
❌ *Нельзя:* жареное, жирное, острое, копчёное, свежую выпечку, шоколад, кофе.
️ *Важно:* перед началом диеты проконсультируйся с врачом!
"""


# ============================================================
# 5. ФУНКЦИИ ИИ (DEEPSEEK)
# ============================================================

def ask_deepseek_for_recipe(ingredients_text):
    """Отправляет запрос в DeepSeek для генерации рецепта"""
    system_prompt = """Ты - опытный диетолог и шеф-повар, специализирующийся на лечебном "Столе №5" (диета при заболеваниях печени, желчного пузыря и поджелудочной железы).
    СТРОГИЕ ПРАВИЛА СТОЛА №5: 
    - НЕЛЬЗЯ: жареное, жирное, острое, копченое, свежую выпечку, шоколад, кофе, бобовые, грибы, наваристые бульоны.
    - МОЖНО: вареное, запеченное без корочки, на пару. Нежирное мясо, рыба, овощи, крупы, молочные продукты низкой жирности.

    Пользователь написал, какие у него есть продукты. Предложи 1 вкусный и простой рецепт, который СТРОГО соответствует Столу №5.
    Формат ответа:
     *Название блюда*
     *Ингредиенты:* (с примерной граммовкой)
    👨‍ *Приготовление:* (пошагово, просто и понятно)
    🔥 *Калорийность:* (примерно)
    Отвечай на русском, тепло и мотивирующе."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",
                 "content": f"У меня есть следующие продукты: {ingredients_text}. Что можно приготовить по Столу №5?"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"️ Ошибка подключения к ИИ: {e}. Проверь API ключ или попробуй позже."


# ============================================================
# 6. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def get_recipes_by_meal(meal_type):
    return [r for r in all_recipes if r.get('Прием пищи') == meal_type]


def format_recipe(recipe):
    msg = f"🍽 *{recipe['Название']}*\n\n"
    msg += f"🛒 *Ингредиенты:*\n{recipe['Ингредиенты']}\n\n"
    msg += f"👨‍🍳 *Приготовление:*\n{recipe['Инструкция']}\n\n"
    msg += f"⏱ *Время:* {recipe['Время приготовления']}\n"
    msg += f"🔥 *Калорийность:* {recipe['Калорийность (ккал)']} ккал"
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
    if any(w in ing for w in
           ['огурец', 'помидор', 'морковь', 'лук', 'капуста', 'свекла', 'тыква', 'кабачок', 'перец', 'брокколи',
            'шпинат', 'зелень']): return ' Овощи и зелень'
    if any(w in ing for w in ['яблоко', 'банан', 'киви', 'груша', 'апельсин', 'ягоды']): return ' Фрукты и ягоды'
    if any(w in ing for w in ['куриц', 'индейк', 'говядин', 'фарш', 'печень']): return '🍗 Мясо и птица'
    if any(w in ing for w in
           ['рыб', 'хек', 'треск', 'лосось', 'судак', 'форель', 'креветк']): return '🐟 Рыба и морепродукты'
    if any(w in ing for w in
           ['творог', 'молоко', 'кефир', 'йогурт', 'сыр', 'сливк', 'сметана']): return '🥛 Молочные продукты'
    if 'яйц' in ing or 'яйцо' in ing: return '🥚 Яйца'
    if any(
        w in ing for w in ['овсян', 'гречк', 'рис', 'булгур', 'пшен', 'вермишел', 'макарон']): return ' Крупы и злаки'
    if any(w in ing for w in ['хлеб', 'тост', 'хлебец']): return '🍞 Хлеб и выпечка'
    if any(w in ing for w in ['масло', 'оливков', 'сливочн']): return '🫙 Масла и жиры'
    if any(w in ing for w in ['орех', 'миндаль', 'кешью', 'семен', 'чиа', 'лён', 'кунжут']): return ' Орехи и семена'
    if any(w in ing for w in
           ['томат', 'соус', 'бульон', 'желатин', 'крахмал', 'мука', 'сахар', 'корица', 'соль', 'перец',
            'лимон']): return '🧂 Бакалея и специи'
    return ' Другое'


def generate_weekly_shopping_list():
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    weekly_menu = {}
    all_ingredients = []

    for day in days:
        menu = generate_daily_menu()
        if menu:
            weekly_menu[day] = menu
            for recipe in menu.values():
                if recipe and 'Ингредиенты' in recipe:
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
    return shopping_list, weekly_menu


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
        bot.reply_to(message, " Не удалось сгенерировать меню.", reply_markup=get_main_keyboard())
        return
    msg = "📋 *Меню на сегодня:*\n\n"
    total_cal = 0
    for meal, recipe in menu.items():
        cal = int(recipe.get('Калорийность (ккал)', 0))
        total_cal += cal
        msg += f"*{meal}:* {recipe['Название']} ({cal} ккал)\n"
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
                msg += f"  • {meal}: {recipe['Название']}\n"
            msg += "\n"
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')


@bot.message_handler(commands=['shopping'])
def send_shopping_list_only(message):
    """Исправленная функция: выдает ТОЛЬКО список покупок"""
    bot.reply_to(message, "⏳ Собираю список покупок...", reply_markup=get_main_keyboard())
    shopping_list, _ = generate_weekly_shopping_list()
    if not shopping_list:
        bot.send_message(message.chat.id, "😕 Не удалось сформировать список", reply_markup=get_main_keyboard())
        return
    bot.send_message(message.chat.id, shopping_list, reply_markup=get_main_keyboard(), parse_mode='Markdown')


@bot.message_handler(commands=['recipe'])
def send_recipe_search(message):
    if not all_recipes:
        bot.reply_to(message, "😕 База пуста", reply_markup=get_main_keyboard())
        return
    bot.send_message(message.chat.id, format_recipe(random.choice(all_recipes)), reply_markup=get_main_keyboard(),
                     parse_mode='Markdown')


@bot.message_handler(commands=['motivation'])
def send_motivation(message):
    bot.reply_to(message, random.choice(MOTIVATION_PHRASES), reply_markup=get_main_keyboard())


@bot.message_handler(commands=['progress'])
def send_progress(message):
    user_data = get_user_data(message.from_user.id)
    if user_data['start_date']:
        days = (datetime.now() - user_data['start_date']).days + 1
        msg = f" *Твой прогресс:*\n Ты на диете уже *{days} дн.*\n"
        if days < 7:
            msg += "💪 Первая неделя — самая важная!"
        elif days < 14:
            msg += "🔥 Отлично! Печень начинает восстанавливаться!"
        else:
            msg += "⭐ Ты уже в ритме! Так держать!"
    else:
        msg = "📊 Нажми /start, чтобы начать отсчет!"
    bot.send_message(message.chat.id, msg, reply_markup=get_main_keyboard(), parse_mode='Markdown')


# ============================================================
# 8. ОБРАБОТЧИК ТЕКСТА (КНОПКИ + ИИ + ПОИСК)
# ============================================================

@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip()
    user_id = message.from_user.id

    # 1. ПРОВЕРКА СОСТОЯНИЯ ИИ (если мы ждем от пользователя список продуктов)
    if user_states.get(user_id) == 'waiting_for_ingredients':
        bot.send_chat_action(message.chat.id, 'typing')  # Показываем, что бот "думает"
        ai_response = ask_deepseek_for_recipe(text)
        bot.send_message(message.chat.id, ai_response, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        user_states[user_id] = None  # Сбрасываем состояние
        return

    # 2. ОБРАБОТКА КНОПОК
    if text in ["📋 Меню на день", "Меню на день"]:
        send_daily_menu(message)
    elif text in ["📅 Меню на неделю", "Меню на неделю"]:
        send_weekly_menu(message)
    elif text in ["🔍 Случайный рецепт", "Случайный рецепт"]:
        send_recipe_search(message)
    elif text in ["🛒 Список покупок", "Список покупок"]:
        send_shopping_list_only(message)  # ИСПРАВЛЕНО: теперь вызывает только список
    elif text in ["💪 Мотивация", "Мотивация"]:
        send_motivation(message)
    elif text in ["📊 Мой прогресс", "Мой прогресс"]:
        send_progress(message)
    elif text in ["ℹ️ О диете", "О диете"]:
        send_info(message)
    elif text in ["🍳 Завтрак", "Завтрак"]:
        recipes = get_recipes_by_meal('Завтрак')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов",
                         reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🍲 Обед", "Обед"]:
        recipes = get_recipes_by_meal('Обед')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов",
                         reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🌙 Ужин", "Ужин"]:
        recipes = get_recipes_by_meal('Ужин')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов",
                         reply_markup=get_main_keyboard(), parse_mode='Markdown')
    elif text in ["🍎 Перекус", "Перекус"]:
        recipes = get_recipes_by_meal('Перекус')
        bot.send_message(message.chat.id, format_recipe(random.choice(recipes)) if recipes else "😕 Нет рецептов",
                         reply_markup=get_main_keyboard(), parse_mode='Markdown')

    # 3. НОВАЯ КНОПКА: ИИ-ПОМОЩНИК
    elif text in ["🤖 ИИ-помощник", "ИИ-помощник"]:
        user_states[user_id] = 'waiting_for_ingredients'
        bot.send_message(
            message.chat.id,
            "🤖 *ИИ-помощник активирован!*\n\nНапиши мне, какие продукты у тебя есть в холодильнике (например: 'курица, кабачок, рис, яйца'), и я придумаю из них вкусный рецепт, который строго подходит для Стола №5!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    # 4. ПОИСК ПО ТЕКСТУ (если ничего не совпало)
    else:
        found = [r for r in all_recipes if text.lower() in r.get('Название', '').lower()]
        if found:
            bot.send_message(message.chat.id, format_recipe(found[0]), reply_markup=get_main_keyboard(),
                             parse_mode='Markdown')
        else:
            bot.reply_to(message, f"🤔 Не нашёл \"{text}\".\nПопробуй написать часть названия или нажми кнопку.",
                         reply_markup=get_main_keyboard())


# ============================================================
# 9. ЗАПУСК
# ============================================================

if __name__ == '__main__':
    print("🚀 Бот запущен!")
    print(f"📚 Рецептов: {len(all_recipes)}")
    print("🤖 DeepSeek подключен")
    bot.infinity_polling()
