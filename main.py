import asyncio
import sqlite3
import math
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, \
    KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==========================================
# 1. НАЛАШТУВАННЯ ТА ІНІЦІАЛІЗАЦІЯ
# ==========================================
TOKEN = '8989889983:AAH93DfEGNuwCGf7UqLl27lJ2xgKUDyTTvk'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- БАЗА ДАНИХ ---
conn = sqlite3.connect('aura_system.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (
                      user_id
                      INTEGER
                      PRIMARY
                      KEY,
                      aura
                      INTEGER
                      DEFAULT
                      0,
                      coupons
                      INTEGER
                      DEFAULT
                      0
                  )''')
conn.commit()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN coupons INTEGER DEFAULT 0")
    conn.commit()
except sqlite3.OperationalError:
    pass


def get_or_create_user(user_id):
    cursor.execute("SELECT aura, coupons FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, aura, coupons) VALUES (?, 0, 0)", (user_id,))
        conn.commit()
        return (0, 0)
    return user


def update_coupons(user_id, amount):
    cursor.execute("UPDATE users SET coupons = coupons + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()


# ==========================================
# 2. МАТЕМАТИКА РІВНІВ ТА АУРИ
# ==========================================
def calculate_level(aura):
    if aura == 0:
        return 0
    elif aura > 0:
        return math.floor((aura / 50) ** (1 / 2.5))
    else:
        return -math.floor((abs(aura) / 50) ** (1 / 2.5))


def aura_for_level(level):
    if level == 0:
        return 0
    elif level > 0:
        return int((level ** 2.5) * 50)
    else:
        return -int((abs(level) ** 2.5) * 50)


async def update_aura_and_check_level(message: Message, user_id: int, amount: int, action_text: str):
    aura, coupons = get_or_create_user(user_id)
    old_level = calculate_level(aura)

    new_aura = aura + amount
    cursor.execute("UPDATE users SET aura = ? WHERE user_id = ?", (new_aura, user_id))
    conn.commit()

    new_level = calculate_level(new_aura)

    sign = "+" if amount > 0 else ""
    await message.answer(f"{action_text}\n{sign}{amount} Аури ✨", reply_markup=main_kb)

    if new_level > old_level:
        old_milestones = max(0, old_level) // 5
        new_milestones = max(0, new_level) // 5
        earned_coupons = new_milestones - old_milestones

        coupon_msg = ""
        if earned_coupons > 0:
            update_coupons(user_id, earned_coupons)
            coupon_msg = f"\n🎟️ **БОНУС:** Отримано купон(и) на гріхи: **+{earned_coupons} шт.**!"

        if new_level <= 0:
            await message.answer(
                f"📈 **ПІДЙОМ З ДНА!** Ти досяг **{new_level} рівня**!\nПродовжуй відпрацьовувати карму! 🛠️{coupon_msg}",
                parse_mode="Markdown")
        else:
            await message.answer(f"🎉 **ЛЕВЕЛ-АП!** Ти досяг **{new_level} рівня**!\nПродовжуй гріндити! 💪{coupon_msg}",
                                 parse_mode="Markdown")
    elif new_level < old_level:
        if new_level < 0:
            await message.answer(f"📉 **ВТРАТА РІВНЯ.** Ти впав на **{new_level} рівень**.\nЗберися, бо це вже кринж! 💀",
                                 parse_mode="Markdown")
        else:
            await message.answer(f"📉 **ВТРАТА РІВНЯ.** Через втрату аури ти скотився на **{new_level} рівень**.",
                                 parse_mode="Markdown")


# ==========================================
# 3. КЛАВІАТУРИ ТА СТАНИ
# ==========================================
class AuraAction(StatesGroup):
    waiting_for_study_mins = State()
    waiting_for_cleaning_mins = State()
    waiting_for_pullups = State()
    waiting_for_pushups = State()
    waiting_for_squats = State()
    waiting_for_expander35 = State()
    waiting_for_expander67 = State()
    waiting_for_tiktok_mins = State()


main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📚 Навчання"), KeyboardButton(text="💪 Спорт"), KeyboardButton(text="🧹 Прибирання")],
    [KeyboardButton(text="⚠️ Шкідливі звички (Мінус Аура)")],
    [KeyboardButton(text="🔮 Мій профіль"), KeyboardButton(text="⚙️ Налаштування")]
], resize_keyboard=True)

cancel_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="❌ Скасувати")]
], resize_keyboard=True)

sport_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Підтягування", callback_data="sport_pullups")],
    [InlineKeyboardButton(text="Відтискання", callback_data="sport_pushups")],
    [InlineKeyboardButton(text="Присідання", callback_data="sport_squats")],
    [InlineKeyboardButton(text="✊ Еспандер (35 кг)", callback_data="sport_expander35")],
    [InlineKeyboardButton(text="🏋️‍♂️ Еспандер (67 кг)", callback_data="sport_expander67")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_inline")]
])

bad_habits_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Мастурбація / Порно (-5000)", callback_data="bad_fap")],
    [InlineKeyboardButton(text="Алкоголь (-10000)", callback_data="bad_alcohol")],
    [InlineKeyboardButton(text="🍩 Солодощі / Фастфуд (-1500)", callback_data="bad_sweets")],
    [InlineKeyboardButton(text="ТікТок (за часом)", callback_data="bad_tiktok")],
    [InlineKeyboardButton(text="Просто злінився (-500)", callback_data="bad_lazy")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_inline")]
])

settings_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔄 Скинути прогрес", callback_data="settings_reset")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_inline")]
])

confirm_reset_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Так, скинути все", callback_data="confirm_reset")],
    [InlineKeyboardButton(text="❌ Ні, я передумав", callback_data="cancel_inline")]
])


# ==========================================
# 4. ОБРОБКА КНОПОК "НАЗАД" ТА СКАСУВАННЯ
# ==========================================
@dp.message(F.text == "❌ Скасувати")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Дію скасовано. Повертаємось до головного меню.", reply_markup=main_kb)


@dp.callback_query(F.data == "cancel_inline")
async def cancel_inline_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Повертаємось до головного меню.", reply_markup=main_kb)
    await callback.answer()


# ==========================================
# 5. НАЛАШТУВАННЯ ТА СКИДАННЯ ПРОГРЕСУ
# ==========================================
@dp.message(F.text == "⚙️ Налаштування")
async def settings_menu(message: Message):
    await message.answer("⚙️ **Меню налаштувань:**\nОбери дію нижче:", reply_markup=settings_kb, parse_mode="Markdown")


@dp.callback_query(F.data == "settings_reset")
async def settings_reset_prompt(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ **УВАГА!** ⚠️\nТи дійсно хочеш скинути весь свій прогрес?\nТвоя Аура, Рівень та Купони назавжди стануть 0.",
        reply_markup=confirm_reset_kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_reset")
async def confirm_reset_action(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("UPDATE users SET aura = 0, coupons = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    await callback.message.delete()
    await callback.message.answer("♻️ Твій прогрес було повністю скинуто. Починаємо з чистого аркуша.",
                                  reply_markup=main_kb)
    await callback.answer()


# ==========================================
# 6. ОСНОВНИЙ ФУНКЦІОНАЛ
# ==========================================
@dp.message(Command('start'))
async def start_cmd(message: Message):
    get_or_create_user(message.from_user.id)
    await message.answer(
        "RPG Система Аури активована.\nФарми ауру, отримуй купони за кожні 5 рівнів, уникай залежностей.",
        reply_markup=main_kb)


# --- ПРОФІЛЬ ---
@dp.message(F.text == "🔮 Мій профіль")
async def show_stats(message: Message):
    aura_points, coupons = get_or_create_user(message.from_user.id)

    current_level = calculate_level(aura_points)
    formatted_aura = "{:,}".format(aura_points).replace(",", " ")

    current_level_start = aura_for_level(current_level)
    next_level_start = aura_for_level(current_level + 1)

    exp_in_level = aura_points - current_level_start
    exp_needed = next_level_start - current_level_start

    if exp_needed > 0:
        percent = max(0.0, min(1.0, exp_in_level / exp_needed))
        filled_length = int(percent * 10)
        bar_str = "=" * filled_length + "-" * (10 - filled_length)
        progress_bar = f"|{bar_str}| {exp_in_level}/{exp_needed}"
    else:
        progress_bar = "|==========| 0/0"

    if current_level >= 100:
        title = "Абсолют 🌌"
    elif current_level >= 75:
        title = "Мільйонер Аури 🗿"
    elif current_level >= 50:
        title = "Божество Аури 👑✨"
    elif current_level >= 25:
        title = "Гігачад 💪"
    elif current_level >= 10:
        title = "На шляху до величі 🏃‍♂️"
    elif current_level >= 5:
        title = "Впевнений старт 😐"
    elif current_level >= 0:
        title = "Новачок 📉"
    elif current_level >= -9:
        title = "Мінус Аура 💀"
    elif current_level >= -24:
        title = "Гоблін 👹"
    elif current_level >= -49:
        title = "Повна деградація 🧟‍♂️"
    else:
        title = "Біосміття 🗑️ (Дно пробито)"

    text_profile = (
        f"🏆 **LVL {current_level} | {title}**\n\n"
        f"✨ Загальна Аура: **{formatted_aura}**\n"
        f"🎟️ Купони на гріхи: **{coupons} шт.**\n\n"
        f"📊 **Прогрес до LVL {current_level + 1}:**\n`{progress_bar}`"
    )

    await message.answer(text_profile, parse_mode="Markdown")


# --- ПРИБИРАННЯ ---
@dp.message(F.text == "🧹 Прибирання")
async def cleaning_start(message: Message, state: FSMContext):
    await message.answer(
        "Скільки хвилин ти витратив на прибирання?\n*(Наприклад: 30 для швидкого, 120 для генерального)*",
        reply_markup=cancel_kb)
    await state.set_state(AuraAction.waiting_for_cleaning_mins)


@dp.message(AuraAction.waiting_for_cleaning_mins)
async def process_cleaning(message: Message, state: FSMContext):
    try:
        mins = int(message.text)
        if mins <= 0 or mins > 1440: raise ValueError

        earned_aura = int(mins * 1000 / 60)
        await update_aura_and_check_level(message, message.from_user.id, earned_aura,
                                          f"Зараховано {mins} хв прибирання! Кімната сяє ✨🧹")
        await state.clear()
    except ValueError:
        await message.answer("Введи ціле число хвилин (наприклад: 30 або 90).")


# --- ШКІДЛИВІ ЗВИЧКИ ---
BAD_HABITS_DATA = {
    "fap": (-5000, "Ти піддався слабкості і втратив життєву енергію. 💀"),
    "alcohol": (-10000, "Алкоголь вбиває твої нейрони і твою Ауру. 🍺🗑️"),
    "sweets": (-1500, "Цукровий удар! Солодощі знищили форму та Ауру. 🍩🍰"),
    "lazy": (-500, "Просто прокравстинував. 🥱")
}


@dp.message(F.text == "⚠️ Шкідливі звички (Мінус Аура)")
async def bad_habits_menu(message: Message):
    await message.answer("Що ти наробив? Обирай гріх:", reply_markup=bad_habits_kb)


@dp.callback_query(F.data.startswith("bad_"))
async def bad_habits_callback(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    user_id = callback.from_user.id
    aura, coupons = get_or_create_user(user_id)

    if action == "tiktok":
        await callback.message.delete()
        await callback.message.answer("Скільки хвилин ти скролив ТікТок/Рілси/Шортси?", reply_markup=cancel_kb)
        await state.set_state(AuraAction.waiting_for_tiktok_mins)
        await callback.answer()
        return

    if action in BAD_HABITS_DATA:
        penalty, text = BAD_HABITS_DATA[action]

        if coupons > 0:
            coupon_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🎟️ Використати купон (0 штрафу)", callback_data=f"usecoupon_{action}")],
                [InlineKeyboardButton(text=f"💀 Отримати штраф ({penalty})", callback_data=f"applybad_{action}")]
            ])
            await callback.message.edit_text(
                f"У тебе є **{coupons}** купон(ів) на відпущення гріхів!\nБажаєш використати купон на цей гріх?",
                reply_markup=coupon_kb,
                parse_mode="Markdown"
            )
        else:
            await callback.message.delete()
            await update_aura_and_check_level(callback.message, user_id, penalty, text)

    await callback.answer()


@dp.callback_query(F.data.startswith("usecoupon_"))
async def use_coupon_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    aura, coupons = get_or_create_user(user_id)

    if coupons > 0:
        update_coupons(user_id, -1)
        await callback.message.delete()
        await callback.message.answer(
            f"🎟️ **КУПОН ВИКОРИСТАНО!**\nТвій гріх відпущено без втрати Аури! Залишилося купонів: {coupons - 1} шт.",
            reply_markup=main_kb)
    else:
        await callback.message.answer("У тебе немає купонів!")
    await callback.answer()


@dp.callback_query(F.data.startswith("applybad_"))
async def apply_bad_callback(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    user_id = callback.from_user.id

    if action in BAD_HABITS_DATA:
        penalty, text = BAD_HABITS_DATA[action]
        await callback.message.delete()
        await update_aura_and_check_level(callback.message, user_id, penalty, text)
    await callback.answer()


@dp.message(AuraAction.waiting_for_tiktok_mins)
async def process_tiktok(message: Message, state: FSMContext):
    try:
        mins = int(message.text)
        if mins <= 0: raise ValueError

        penalty = -(mins * 50)
        user_id = message.from_user.id
        aura, coupons = get_or_create_user(user_id)

        if coupons > 0:
            await state.update_data(tiktok_penalty=penalty, tiktok_mins=mins)
            coupon_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎟️ Використати купон (0 штрафу)", callback_data="usecoupon_tiktok")],
                [InlineKeyboardButton(text=f"💀 Отримати штраф ({penalty})", callback_data="applybad_tiktok")]
            ])
            await message.answer(
                f"Скролив ТікТок {mins} хв (Штраф: {penalty}).\nУ тебе є **{coupons}** купон(ів)! Бажаєш використати?",
                reply_markup=coupon_kb,
                parse_mode="Markdown"
            )
        else:
            await update_aura_and_check_level(message, user_id, penalty,
                                              f"Скролив ТікТок {mins} хвилин. Дофамінові рецептори спалені. 📱🧠")
            await state.clear()

    except ValueError:
        await message.answer("Введи ціле число хвилин більше нуля.")


@dp.callback_query(F.data == "usecoupon_tiktok")
async def use_coupon_tiktok(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    aura, coupons = get_or_create_user(user_id)
    if coupons > 0:
        update_coupons(user_id, -1)
        await callback.message.delete()
        await callback.message.answer(
            f"🎟️ **КУПОН ВИКОРИСТАНО!**\nТікТок пробачено без втрати Аури! Залишилося купонів: {coupons - 1} шт.",
            reply_markup=main_kb)
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "applybad_tiktok")
async def apply_bad_tiktok(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    penalty = data.get("tiktok_penalty", -500)
    mins = data.get("tiktok_mins", 10)
    user_id = callback.from_user.id

    await callback.message.delete()
    await update_aura_and_check_level(callback.message, user_id, penalty,
                                      f"Скролив ТікТок {mins} хвилин. Дофамінові рецептори спалені. 📱🧠")
    await state.clear()
    await callback.answer()


# --- НАВЧАННЯ ---
@dp.message(F.text == "📚 Навчання")
async def study_start(message: Message, state: FSMContext):
    await message.answer(
        "Скільки хвилин ти витратив на навчання?\n*(Наприклад: 30 для швидкого ДЗ, 120 для опрацювання теми)*",
        reply_markup=cancel_kb)
    await state.set_state(AuraAction.waiting_for_study_mins)


@dp.message(AuraAction.waiting_for_study_mins)
async def process_study(message: Message, state: FSMContext):
    try:
        mins = int(message.text)
        if mins <= 0 or mins > 1440: raise ValueError

        earned_aura = int(mins * 1000 / 60)
        await update_aura_and_check_level(message, message.from_user.id, earned_aura,
                                          f"Зараховано {mins} хв розумової праці! 🧠")
        await state.clear()
    except ValueError:
        await message.answer("Введи ціле число хвилин (наприклад: 30 або 90).")


# --- СПОРТ ---
@dp.message(F.text == "💪 Спорт")
async def sport_start(message: Message):
    await message.answer("Обери вправу:", reply_markup=sport_kb)


@dp.callback_query(F.data.startswith("sport_"))
async def sport_callback(callback: CallbackQuery, state: FSMContext):
    exercise = callback.data.split("_")[1]
    prompts = {
        "pullups": "Скільки разів підтягнувся за один підхід?",
        "pushups": "Скільки разів відтиснувся за один підхід?",
        "squats": "Скільки разів присів за один підхід?",
        "expander35": "Скільки разів стиснув еспандер (35 кг) за один підхід?",
        "expander67": "Скільки разів стиснув еспандер (67 кг) за один підхід?"
    }

    await callback.message.delete()
    await callback.message.answer(prompts[exercise], reply_markup=cancel_kb)
    await state.set_state(getattr(AuraAction, f"waiting_for_{exercise}"))
    await callback.answer()


async def process_exercise(message: Message, state: FSMContext, exercise_type: str):
    try:
        reps = int(message.text)
        if reps <= 0 or reps > 500: raise ValueError

        earned_aura = 0
        if exercise_type == "pullups":
            if reps <= 5:
                earned_aura = reps * 50
            elif reps <= 10:
                earned_aura = reps * 100
            elif reps <= 15:
                earned_aura = reps * 200
            else:
                earned_aura = reps * 300
        elif exercise_type == "pushups":
            if reps <= 10:
                earned_aura = reps * 10
            elif reps <= 20:
                earned_aura = reps * 20
            elif reps <= 30:
                earned_aura = reps * 40
            else:
                earned_aura = reps * 60
        elif exercise_type == "squats":
            if reps <= 15:
                earned_aura = reps * 10
            elif reps <= 30:
                earned_aura = reps * 20
            else:
                earned_aura = reps * 30
        elif exercise_type == "expander67":
            if reps <= 10:
                earned_aura = reps * 15
            elif reps <= 15:
                earned_aura = reps * 30
            else:
                earned_aura = reps * 50
        elif exercise_type == "expander35":
            if reps <= 10:
                earned_aura = reps * 3
            elif reps <= 15:
                earned_aura = reps * 6
            else:
                earned_aura = reps * 10

        await update_aura_and_check_level(message, message.from_user.id, earned_aura,
                                          f"Хороший підхід! ({reps} разів) 🔥")
        await state.clear()

    except ValueError:
        await message.answer("Введи ціле число більше нуля.")


@dp.message(AuraAction.waiting_for_pullups)
async def process_pullups(message: Message, state: FSMContext): await process_exercise(message, state, "pullups")


@dp.message(AuraAction.waiting_for_pushups)
async def process_pushups(message: Message, state: FSMContext): await process_exercise(message, state, "pushups")


@dp.message(AuraAction.waiting_for_squats)
async def process_squats(message: Message, state: FSMContext): await process_exercise(message, state, "squats")


@dp.message(AuraAction.waiting_for_expander35)
async def process_expander35(message: Message, state: FSMContext): await process_exercise(message, state, "expander35")


@dp.message(AuraAction.waiting_for_expander67)
async def process_expander67(message: Message, state: FSMContext): await process_exercise(message, state, "expander67")


# ==========================================
# ЗАПУСК БОТА
# ==========================================
async def main():
    print("Грінд-бот (Запис у хвилинах) запущений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())