import asyncio
import datetime as dt
from dataclasses import dataclass

import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# =========================
# CONFIG
# =========================
TOKEN = "8060185815:AAFp9aqKCrV4RRTw6zOg7v3jJ7QTs9xREoE"
TZ = "Asia/Tashkent"
DB_PATH = "coach.db"

# Default reminders (Toshkent vaqti bilan)
REMINDER_TIMES = {
    "breakfast": "08:00",
    "lunch": "12:00",
    "snack": "16:00",
    "dinner": "19:00",
}

# =========================
# MENU DATABASE (7-kun aylantirish)
# =========================
# Har bir ovqat turi bo'yicha (breakfast/lunch/snack/dinner)
# 7 ta variant -> kunlar bo'yicha aylantiradi

MENUS = {
    "lose": {  # OZISH
        "breakfast": [
            "🍳 2 dona tuxum + 🥣 suli bo‘tqa (shakarsiz)",
            "🧀 Tvorog 200g + 🍏 olma",
            "🍳 Omlet (2 tuxum) + 🍅 pomidor/bodring",
            "🥣 Suli + yarim 🍌 banan",
            "🍳 2 tuxum + 1 bo‘lak qora non + ko‘kat",
            "🥛 Yogurt + ozroq suli",
            "🧀 Tvorog + ko‘kat + choy (shakarsiz)",
        ],
        "lunch": [
            "🍗 Tovuq 150–180g + 🍚 grechka (4–6 qoshiq) + 🥗 salat",
            "🥩 Mol go‘sht 150g + 🥗 salat + ozroq guruch",
            "🍗 Tovuq + 🥔 pechda kartoshka (kam) + 🥗 salat",
            "🐟 Baliq 160–200g + 🍚 grechka + 🥗 salat",
            "🥣 Yog‘siz moshxo‘rda + 🥗 salat",
            "🍢 Kam yog‘li kabob + 🥗 salat",
            "🍜 Lag‘mon (kichik porsiya) + 🥗 salat",
        ],
        "snack": [
            "🥛 Kefir 1 stakan",
            "🍏 Olma + choy (shakarsiz)",
            "🥛 Yogurt + 1 dona meva",
            "🥜 Yong‘oq 15–20g",
            "🥛 Kefir + ko‘kat",
            "🍐 Nok/Olma",
            "🥛 Yogurt",
        ],
        "dinner": [
            "🐟 Baliq + 🥦 sabzavot (yengil)",
            "🥣 Sho‘rva + 🥗 salat",
            "🥗 Katta salat + 1–2 tuxum",
            "🥘 Sabzavotli dimlama",
            "🍗 Tovuq 150g + 🥗 salat",
            "🐟 Baliq + sabzavot",
            "🥣 Sho‘rva (yengil)",
        ],
        "tips": [
            "💧 Bugun 2 litr suv ich.",
            "🚶 30 daqiqa yur.",
            "❌ Shirinlik va gazli ichimlik yo‘q.",
            "🕙 Kech yeb qo‘yma: 21:00 dan keyin yo‘q.",
            "🥗 Salatni ko‘paytir.",
            "🍞 Oqartirilgan nonni kamaytir.",
            "😴 7–8 soat uxla.",
        ],
    },

    "gain": {  # SEMIRISH
        "breakfast": [
            "🍳 3 tuxum + 🧀 pishloq + 🍞 non + 🍌 banan",
            "🥣 Suli bo‘tqa + 🥜 yong‘oq + 🥛 sut",
            "🧀 Tvorog 250g + 🍯 ozroq asal + 🍌 banan",
            "🍞 Sendvich: tovuq + pishloq + sabzavot",
            "🍳 Omlet + 🥔 kartoshka + 🍞 non",
            "🥛 Smoothie: sut + banan + yong‘oq",
            "🍳 2 tuxum + 🥣 bo‘tqa + 1 dona meva",
        ],
        "lunch": [
            "🍗 Tovuq 200–250g + 🍚 guruch (ko‘proq) + 🥗 salat",
            "🥩 Mol go‘sht + 🍝 makaron + 🥗 salat",
            "🍗 Tovuq + 🥔 kartoshka + 🥗 salat",
            "🐟 Baliq + 🍚 guruch + 🥗 salat",
            "🥣 Sho‘rva + 🍞 non + 🥗 salat",
            "🍛 Palov (o‘rtacha porsiya) + 🥗 salat",
            "🍜 Lag‘mon (o‘rtacha) + 🥗 salat",
        ],
        "snack": [
            "🍌 Banan + 🥜 yong‘oq 30g",
            "🥛 Yogurt + 🍯 ozroq asal",
            "🥪 Yengil sendvich",
            "🥛 Sut + pechenye (kam)",
            "🧀 Tvorog + meva",
            "🥜 Yong‘oq 30g + meva",
            "🥛 Kefir + banan",
        ],
        "dinner": [
            "🍗 Tovuq + 🍚 ozroq guruch + 🥗 salat",
            "🥩 Mol go‘sht + sabzavot",
            "🐟 Baliq + 🥔 kartoshka",
            "🥘 Dimlama + 🍞 non (1-2 bo‘lak)",
            "🥣 Sho‘rva + 🍞 non",
            "🍳 Omlet + 🧀 pishloq",
            "🍗 Tovuq + sabzavot",
        ],
        "tips": [
            "🍽 Kunda 4 mahal ovqatni tashlama.",
            "🥜 Yong‘oq/banan kabi kaloriyali snack qo‘sh.",
            "💪 Yengil kuch mashqlari qil.",
            "💧 Suvni unutma.",
            "😴 Uyqu 7–8 soat.",
            "🍚 Uglevodni (guruch/makaron) ozroq ko‘paytir.",
            "✅ Har kuni bir xil vaqtda ye.",
        ],
    },

    "keep": {  # VAZN SAQLASH
        "breakfast": [
            "🍳 2 tuxum + 🥣 suli",
            "🧀 Tvorog + meva",
            "🍳 Omlet + sabzavot",
            "🥣 Bo‘tqa + meva",
            "🍞 1 bo‘lak non + tuxum + ko‘kat",
            "🥛 Yogurt + suli",
            "🧀 Tvorog + ko‘kat",
        ],
        "lunch": [
            "🍗 Tovuq 180–220g + 🍚 grechka + 🥗 salat",
            "🥩 Mol go‘sht + sabzavot + ozroq guruch",
            "🐟 Baliq + guruch + salat",
            "🥣 Sho‘rva + salat",
            "🍛 Palov (kichik/o‘rtacha) + salat",
            "🍜 Lag‘mon (kichik) + salat",
            "🍗 Tovuq + kartoshka (oz) + salat",
        ],
        "snack": [
            "🍏 Olma",
            "🥛 Kefir",
            "🥛 Yogurt",
            "🥜 Yong‘oq 20g",
            "🍐 Nok",
            "🥛 Kefir + meva",
            "🧀 Tvorog ozroq",
        ],
        "dinner": [
            "🐟 Baliq + sabzavot",
            "🥣 Sho‘rva",
            "🥗 Salat + 1 tuxum",
            "🥘 Dimlama (yengil)",
            "🍗 Tovuq + salat",
            "🐟 Baliq + salat",
            "🥣 Sho‘rva + salat",
        ],
        "tips": [
            "🚶 20–30 daqiqa yur.",
            "💧 Suv: 1.5–2L.",
            "❌ Gazli ichimlikni kamaytir.",
            "✅ Porsiyani nazorat qil.",
            "😴 Uyquni to‘g‘rila.",
            "🍬 Shirinlikni haftasiga 1–2 marta.",
            "🥗 Sabzavotni ko‘paytir.",
        ],
    },
}

GOAL_MAP = {
    "Ozish": "lose",
    "Semirish": "gain",
    "Saqlash": "keep",
}

MEAL_LABEL = {
    "breakfast": "🕗 Nonushta",
    "lunch": "🕛 Tushlik",
    "snack": "🕓 Snack",
    "dinner": "🕖 Kechki ovqat",
}

# =========================
# DB
# =========================
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  gender TEXT,
  age INTEGER,
  height_cm INTEGER,
  weight_kg REAL,
  goal TEXT,                -- Ozish / Semirish / Saqlash
  reminders_enabled INTEGER DEFAULT 1,
  breakfast_enabled INTEGER DEFAULT 1,
  lunch_enabled INTEGER DEFAULT 1,
  snack_enabled INTEGER DEFAULT 1,
  dinner_enabled INTEGER DEFAULT 1,
  created_at INTEGER
);
"""

async def db_init():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_SQL)
        await db.commit()

async def upsert_user(user_id: int, gender: str, age: int, height_cm: int, weight_kg: float, goal: str):
    now = int(dt.datetime.now().timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users(user_id, gender, age, height_cm, weight_kg, goal, created_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
          gender=excluded.gender,
          age=excluded.age,
          height_cm=excluded.height_cm,
          weight_kg=excluded.weight_kg,
          goal=excluded.goal
        """, (user_id, gender, age, height_cm, weight_kg, goal, now))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, gender, age, height_cm, weight_kg, goal, reminders_enabled, breakfast_enabled, lunch_enabled, snack_enabled, dinner_enabled FROM users WHERE user_id=?",
                               (user_id,))
        row = await cur.fetchone()
        return row

async def list_users_for_meal(meal_key: str):
    col = meal_key + "_enabled"
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(f"""
          SELECT user_id, age, height_cm, weight_kg, goal
          FROM users
          WHERE reminders_enabled=1 AND {col}=1
        """)
        rows = await cur.fetchall()
        return rows

async def toggle_all_reminders(user_id: int, enabled: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET reminders_enabled=? WHERE user_id=?", (enabled, user_id))
        await db.commit()

# =========================
# HELPERS
# =========================
def day_index() -> int:
    # Har kuni o'zgarishi uchun: yilning nechinchi kuni
    return dt.date.today().timetuple().tm_yday

def bmi(height_cm: int, weight_kg: float) -> float:
    m = height_cm / 100.0
    return weight_kg / (m * m)

def bmi_status(b: float) -> str:
    if b < 18.5:
        return "Ozg‘in"
    if b < 25:
        return "Normal"
    if b < 30:
        return "Ortiqcha vazn"
    return "Semirish"

def normal_weight_range(height_cm: int):
    m = height_cm / 100.0
    min_w = 18.5 * (m*m)
    max_w = 24.9 * (m*m)
    return round(min_w, 1), round(max_w, 1)

def pick_plan(goal_key: str, meal_key: str):
    idx = (day_index() - 1) % 7
    plan = MENUS[goal_key][meal_key][idx]
    tip = MENUS[goal_key]["tips"][idx]
    return plan, tip

def profile_text(age: int, height_cm: int, weight_kg: float, goal: str) -> str:
    b = bmi(height_cm, weight_kg)
    st = bmi_status(b)
    mn, mx = normal_weight_range(height_cm)
    return (
        f"📊 Holatingiz:\n"
        f"🎂 Yosh: {age}\n"
        f"📏 Bo‘y: {height_cm} sm\n"
        f"⚖️ Vazn: {weight_kg} kg\n"
        f"🎯 Maqsad: {goal}\n\n"
        f"✅ BMI: {b:.1f} ({st})\n"
        f"🧭 Normal vazn oraliq: {mn} – {mx} kg"
    )

# =========================
# BOT
# =========================
dp = Dispatcher()

def main_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🧾 Profil kiritish")
    kb.button(text="📊 Mening holatim")
    kb.button(text="🍽 Bugungi reja")
    kb.button(text="⏰ Eslatmalarni yoq/o‘chir")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)

@dataclass
class ProfileDraft:
    step: str = "gender"
    gender: str = ""
    age: int = 0
    height_cm: int = 0
    weight_kg: float = 0.0
    goal: str = ""

profile_states: dict[int, ProfileDraft] = {}

@dp.message(CommandStart())
async def start(m: types.Message):
    await m.answer(
        "👋 Salom! Men Ozish/Semirish Coach botman.\n\n"
        "🧾 Profil kiritasiz — keyin men har kuni avtomatik ovqat rejasini yuboraman.\n"
        "Default: 08:00 / 12:00 / 16:00 / 19:00 (Toshkent vaqti).\n\n"
        "Boshlash uchun: 🧾 Profil kiritish",
        reply_markup=main_kb()
    )

@dp.message(F.text == "🧾 Profil kiritish")
async def profile_start(m: types.Message):
    profile_states[m.from_user.id] = ProfileDraft(step="gender")
    kb = ReplyKeyboardBuilder()
    kb.button(text="Ayol")
    kb.button(text="Erkak")
    kb.adjust(2)
    await m.answer("👤 Jinsingizni tanlang:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(F.text.in_(["Ayol", "Erkak"]))
async def set_gender(m: types.Message):
    st = profile_states.get(m.from_user.id)
    if not st or st.step != "gender":
        return
    st.gender = m.text
    st.step = "age"
    await m.answer("🎂 Yoshingiz, faqat raqam (masalan 22):", reply_markup=types.ReplyKeyboardRemove())

@dp.message()
async def profile_flow(m: types.Message, bot: Bot):
    uid = m.from_user.id

    # --- Toggle reminders ---
    if m.text == "⏰ Eslatmalarni yoq/o‘chir":
        row = await get_user(uid)
        if not row:
            await m.answer("Avval 🧾 Profil kiritish qiling.")
            return
        enabled = row[6]
        new_val = 0 if enabled == 1 else 1
        await toggle_all_reminders(uid, new_val)
        await m.answer("✅ Eslatmalar YOQILDI." if new_val == 1 else "⛔ Eslatmalar O‘CHIRILDI.", reply_markup=main_kb())
        return

    # --- My status ---
    if m.text == "📊 Mening holatim":
        row = await get_user(uid)
        if not row:
            await m.answer("Avval 🧾 Profil kiritish qiling.")
            return
        _, _, age, height_cm, weight_kg, goal, *_ = row
        await m.answer(profile_text(age, height_cm, weight_kg, goal), reply_markup=main_kb())
        return

    # --- Today plan (all meals) ---
    if m.text == "🍽 Bugungi reja":
        row = await get_user(uid)
        if not row:
            await m.answer("Avval 🧾 Profil kiritish qiling.")
            return
        _, _, age, height_cm, weight_kg, goal, *_ = row
        gkey = GOAL_MAP.get(goal, "keep")
        out = [profile_text(age, height_cm, weight_kg, goal), ""]
        for meal in ["breakfast", "lunch", "snack", "dinner"]:
            plan, tip = pick_plan(gkey, meal)
            out.append(f"{MEAL_LABEL[meal]}:\n• {plan}\n{tip}")
            out.append("")
        await m.answer("\n".join(out).strip(), reply_markup=main_kb())
        return

    # --- Profile state machine ---
    st = profile_states.get(uid)
    if not st:
        return

    if st.step == "age":
        if not m.text.isdigit():
            await m.answer("Yosh faqat raqam bo‘lsin. Masalan: 22")
            return
        st.age = int(m.text)
        st.step = "height"
        await m.answer("📏 Bo‘yingiz (sm), masalan 175:")
        return

    if st.step == "height":
        if not m.text.isdigit():
            await m.answer("Bo‘y faqat raqam bo‘lsin. Masalan: 175")
            return
        st.height_cm = int(m.text)
        st.step = "weight"
        await m.answer("⚖️ Vazningiz (kg), masalan 70:")
        return

    if st.step == "weight":
        try:
            w = float(m.text.replace(",", "."))
        except:
            await m.answer("Vazn raqam bo‘lsin. Masalan: 70")
            return
        st.weight_kg = w
        st.step = "goal"
        kb = ReplyKeyboardBuilder()
        kb.button(text="Ozish")
        kb.button(text="Semirish")
        kb.button(text="Saqlash")
        kb.adjust(3)
        await m.answer("🎯 Maqsadingizni tanlang:", reply_markup=kb.as_markup(resize_keyboard=True))
        return

    if st.step == "goal":
        if m.text not in ["Ozish", "Semirish", "Saqlash"]:
            await m.answer("Maqsadni tugma orqali tanlang: Ozish / Semirish / Saqlash")
            return
        st.goal = m.text

        await upsert_user(uid, st.gender, st.age, st.height_cm, st.weight_kg, st.goal)
        profile_states.pop(uid, None)

        # Immediately show status + explain auto
        await m.answer(
            "✅ Profil saqlandi!\n\n"
            f"⏰ Endi men har kuni avtomatik yuboraman:\n"
            f"• 08:00 Nonushta\n"
            f"• 12:00 Tushlik\n"
            f"• 16:00 Snack\n"
            f"• 19:00 Kechki ovqat\n\n"
            "🍽 Menyu har kuni o‘zgaradi va maqsadingizga qarab (ozish/semirish/saqlash) mos bo‘ladi.",
            reply_markup=main_kb()
        )
        await m.answer(profile_text(st.age, st.height_cm, st.weight_kg, st.goal), reply_markup=main_kb())
        return

# =========================
# SCHEDULER JOBS
# =========================
async def send_meal(bot: Bot, meal_key: str):
    users = await list_users_for_meal(meal_key)
    for (user_id, age, height_cm, weight_kg, goal) in users:
        gkey = GOAL_MAP.get(goal, "keep")
        plan, tip = pick_plan(gkey, meal_key)
        txt = (
            f"{MEAL_LABEL[meal_key]} (avtomatik)\n"
            f"🎯 Maqsad: {goal}\n\n"
            f"• {plan}\n\n"
            f"{tip}\n"
            f"💧 Suv ichishni unutmang."
        )
        try:
            await bot.send_message(user_id, txt)
        except Exception:
            # user block qilgan yoki chat yo‘q — jim o'tamiz
            pass

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    sch = AsyncIOScheduler(timezone=TZ)

    for meal_key, hhmm in REMINDER_TIMES.items():
        hh, mm = map(int, hhmm.split(":"))
        sch.add_job(
            lambda mk=meal_key: asyncio.create_task(send_meal(bot, mk)),
            CronTrigger(hour=hh, minute=mm, timezone=TZ),
            name=f"send_{meal_key}",
            replace_existing=True
        )
    return sch

# =========================
# RUN
# =========================
async def main():
    await db_init()
    bot = Bot(TOKEN)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
