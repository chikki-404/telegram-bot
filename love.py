from telegram.ext import Application, CommandHandler
import random, string, time, signal, sys, json, os

# ================== CONFIG ==================
TOKEN = "8595233518:AAHYLmSC7LJmK3WmX53iORCN4JinOzU1vOs"
DB_FILE = "db.json"
ADMIN_IDS = {7636298287, 6606949931}
# ============================================

# ---------------- DATABASE ------------------

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "proposals": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

db = load_db()
users = db["users"]
proposals = db["proposals"]

def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "partner": None,
            "points": 0,
            "married": False
        }
        save_db()
    return users[uid]

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# ---------------- COMMANDS ------------------

async def start(update, context):
    await update.message.reply_text(
        "💘 *Valentine Love Game* 💘\n\n"
        "/propose – create code 💌\n"
        "/accept CODE – accept love 💖\n"
        "/kiss /hug /holdhand – earn points\n"
        "/mylove – check points\n"
        "/marry – marry partner\n"
        "/breakup – breakup\n"
        "/global – leaderboard\n"
        "/backup – admin only",
        parse_mode="Markdown"
    )

async def propose(update, context):
    uid = update.message.from_user.id
    user = get_user(uid)

    if user["partner"]:
        await update.message.reply_text("❌ You already have a partner.")
        return

    code = gen_code()
    proposals[code] = str(uid)
    save_db()

    await update.message.reply_text(
        f"💌 *Proposal Created*\nCode: `{code}`",
        parse_mode="Markdown"
    )

async def accept(update, context):
    uid = update.message.from_user.id
    user = get_user(uid)

    if user["partner"]:
        await update.message.reply_text("❌ You already have a partner.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /accept CODE")
        return

    code = context.args[0]

    if code not in proposals:
        await update.message.reply_text("💔 Invalid code.")
        return

    partner_id = proposals.pop(code)

    if partner_id == str(uid):
        await update.message.reply_text("🤨 You can’t accept your own code.")
        return

    partner = get_user(partner_id)

    if partner["partner"]:
        await update.message.reply_text("💔 That person is taken.")
        return

    user["partner"] = partner_id
    partner["partner"] = str(uid)
    save_db()

    await update.message.reply_text("💖 You are now a couple!")

async def action(update, context, text, a, b):
    uid = update.message.from_user.id
    user = get_user(uid)

    if not user["partner"]:
        await update.message.reply_text("❌ You need a partner.")
        return

    partner = get_user(user["partner"])
    pts = random.randint(a, b)

    user["points"] += pts
    partner["points"] += pts
    save_db()

    await update.message.reply_text(f"💞 You {text} (+{pts} pts)")

async def kiss(update, context):
    await action(update, context, "kissed 😘", 10, 20)

async def hug(update, context):
    await action(update, context, "hugged 🤗", 5, 15)

async def holdhand(update, context):
    await action(update, context, "held hands 🤝", 3, 10)

async def mylove(update, context):
    user = get_user(update.message.from_user.id)
    await update.message.reply_text(
        f"❤️ Love Points: *{user['points']}*",
        parse_mode="Markdown"
    )

async def marry(update, context):
    uid = update.message.from_user.id
    user = get_user(uid)

    if not user["partner"]:
        await update.message.reply_text("💔 No partner.")
        return

    if user["points"] < 1000:
        await update.message.reply_text("💍 Need 1000 points.")
        return

    partner = get_user(user["partner"])
    user["married"] = True
    partner["married"] = True
    save_db()

    await update.message.reply_text("💍 Married successfully!")

async def breakup(update, context):
    uid = update.message.from_user.id
    user = get_user(uid)

    if not user["partner"]:
        await update.message.reply_text("❌ No relationship.")
        return

    partner = get_user(user["partner"])
    user["partner"] = None
    partner["partner"] = None
    user["married"] = False
    partner["married"] = False
    save_db()

    await update.message.reply_text("💔 Relationship ended.")

async def global_status(update, context):
    if not users:
        await update.message.reply_text("No data yet.")
        return

    top = sorted(users.items(), key=lambda x: x[1]["points"], reverse=True)[:5]
    msg = "🌍 *Global Love Leaders*\n\n"

    for i, (uid, data) in enumerate(top, 1):
        msg += f"{i}. `{uid}` — {data['points']} pts\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------- BACKUP ------------------

async def backup(update, context):
    uid = update.message.from_user.id

    if uid not in ADMIN_IDS:
        await update.message.reply_text("⛔ Not authorized.")
        return

    save_db()

    await context.bot.send_document(
        chat_id=uid,
        document=open(DB_FILE, "rb"),
        filename="db.json",
        caption="📦 Love Bot Backup"
    )

# ---------------- SAFE EXIT ----------------

def stop(sig, frame):
    print("🛑 Bot stopped.")
    save_db()
    sys.exit(0)

signal.signal(signal.SIGINT, stop)

# ---------------- POLLING LOOP ----------------

while True:
    try:
        print("🤖 Bot polling...")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("propose", propose))
        app.add_handler(CommandHandler("accept", accept))
        app.add_handler(CommandHandler("kiss", kiss))
        app.add_handler(CommandHandler("hug", hug))
        app.add_handler(CommandHandler("holdhand", holdhand))
        app.add_handler(CommandHandler("mylove", mylove))
        app.add_handler(CommandHandler("marry", marry))
        app.add_handler(CommandHandler("breakup", breakup))
        app.add_handler(CommandHandler("global", global_status))
        app.add_handler(CommandHandler("backup", backup))

        app.run_polling(drop_pending_updates=True)

    except Exception as e:
        print(f"⚠️ Crash: {e}")
        time.sleep(5)