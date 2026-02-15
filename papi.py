import os
import random
import time
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)
PORT = int(os.getenv("PORT", 8080))

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Battleground Bot is Running!")

def start_http_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = [7800914151, 6606949931, 7122295702]

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Main Group ID
main_group_id = -1003565341717

# Game Data
players = {}        # player_id: data
poison_zones = {}  # zone_no : { "damage": int, "interval": int, "last_tick": timestamp } 
lobby = []          # current lobby players
airdrops = {}       # zone: item
dungeon_zones = []  # zones with dungeon
cooldowns = {}      # (user_id, action): timestamp
current_game = {}   # global game info
zone_ids = {
    1: -1002880128355, 2: -1002503998760, 3: -1002802748304, 4: -1002826584214, 5: -1002872584338,
    6: -1002790903433, 7: -1002872240951, 8: -1002758381995, 9: -1002870220439, 10: -1002726014247
}
poison_zones[zone] = {
    "start_time": now,
    "damage": poison_damage,
    "interval": 5,      #  5 sec tick
    "last_tick": now
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        " **Welcome to Ultimate Battleground Survival!** \n\n"
        "Survive in zones, collect weapons & shields, heal, fight opponents, open dungeons & claim rare airdrops!\n\n"
        " Base HP: 20\n"
        " Shields: Stackable (max 40)\n"
        " Weapons & Items: Collect, Equip, and Use\n"
        " Zones: Travel & Hunt Your Opponents\n\n"
        "Use `/help` to see all commands and get ready to survive! "
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        " **Battleground Survival – Commands List** \n\n"
        " **Short Game Description:**\n"
        "Survive in zones, collect weapons & shields, heal, fight opponents, open dungeons & claim rare airdrops. Tactical long fights! \n\n"
        " **Player Commands:**\n"
        "/start_game <time> – Start lobby\n"
        "/join – Join lobby\n"
        "/extend – Extend join time\n"
        "/force_start – Admin: start lobby immediately\n"
        "/cancel_game – Cancel current lobby/game\n"
        "/myprofile – Show stats\n"
        "/inventory – Check items\n"
        "/map – View zones & dungeons\n"
        "/leaderboard – Check top killers & survival\n"
        "/travel <zone> – Move to zone\n"
        "/airdrop – Summon airdrop\n"
        "/claim – Claim airdrop reward\n"
        "/open – Open dungeon with key\n"
        "/search – Find weapons, shields, healing items\n"
        "/select <weapon> – Choose weapon\n"
        "/equip <shield> – Equip shield\n"
        "/use <item> – Use healing/combat item\n"
        "/kill <@player> – Attack opponent in same zone\n"
        "/hp – Check HP & shield\n"
        "/impact <zone> – Meteor Impact if owned\n\n"
        " **Admin Commands:**\n"
        "/reset <user_id> – Reset a player\n"
        "/reset all – Reset whole game\n"
        "/restart – Reconnect bot\n"
        "/add_item <item> – Add item to player\n"
        "/set_time <minutes> – Set game duration"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
    
async def check_poison():
    """
    Check every 1 sec for players in poisonous zones.
    Apply damage every 5 seconds.
    Handles Phoenix Sigil revival automatically.
    """
    while current_game.get("running"):
        now = time.time()
        for zone, info in poison_zones.items():
            if now - info["last_tick"] >= 5:  #  5 sec interval now
                for uid, p in players.items():
                    if p.get("zone") == zone:
                        p["hp"] -= info["damage"]
                        if p["hp"] <= 0:
                            if "phoenix_sigil" in p.get("inventory", []):
                                p["hp"] = 20
                                p["shield"] = 0
                                p["inventory"].remove("phoenix_sigil")
                                await bot.send_message(uid, " Phoenix Sigil activated! You revived with full HP!")
                            else:
                                await bot.send_message(uid, f" You died in poisonous Zone {zone}!")
                info["last_tick"] = now
        await asyncio.sleep(1)  # loop check every second
   
async def escalate_poison():
    """Gradually makes zones poisonous and increases damage over time."""
    while current_game.get("running"):
        now = time.time()
        elapsed = now - current_game.get("start_time", now)
        total_time = current_game.get("total_time", 600)  # default 10 min
        progress = elapsed / total_time

        total_zones = len(zone_ids)
        poison_count = max(1, int(total_zones * progress))  # how many zones should be poisonous
        poison_damage = 2 + int(progress * 5)  # damage increases with time

        current_poisoned = list(poison_zones.keys())
        available_zones = [z for z in zone_ids if z not in current_poisoned]
        zones_to_poison = available_zones[:poison_count - len(current_poisoned)]

        for zone in zones_to_poison:
            poison_zones[zone] = {
                "start_time": now,
                "damage": poison_damage,
                "interval": 5,       # 5 sec damage interval
                "last_tick": now
            }
            await bot.send_message(main_group_id,
                                   f" Zone {zone} has become poisonous! Damage: {poison_damage}/
    
 async def start_game(update, context):
    global lobby, current_game
    if current_game.get("running"):
        await update.message.reply_text(" A game is already running!")
        return

    # Parse time argument
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Specify lobby time in minutes, e.g., /start_game 5")
        return
    try:
        lobby_time_min = int(args[0])
    except:
        await update.message.reply_text("Invalid time format. Use minutes as number.")
        return

    # Initialize game
    lobby = []
    current_game = {
        "running": True,
        "start_time": time.time(),
        "total_time": lobby_time_min * 60,
        "creator": update.effective_user.id
    }

    await update.message.reply_text(f" Battleground started! Lobby open for {lobby_time_min} minutes. Use /join to enter!")

    # Start poison tasks
    asyncio.create_task(check_poison())
    asyncio.create_task(escalate_poison())

    # Auto-close lobby after lobby_time_min
    await asyncio.sleep(lobby_time_min * 60)
    if current_game.get("running"):
        await update.message.reply_text(" Lobby time ended! Game starting now...")

        num_players = len(lobby)
        if num_players < 10:
            active_zones = zone_ids[:5]
        else:
            active_zones = zone_ids

        for uid in lobby:
            players[uid]["zone"] = active_zones[0]  # start everyone in first zone
            await bot.send_message(uid, f" You have been placed in Zone {active_zones[0]}!")

        await update.message.reply_text(f"Zones activated: {', '.join(map(str, active_zones))}")
        
       
    
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in lobby:
        await update.message.reply_text("You are already in the lobby! ")
        return
    lobby.append(user_id)
    await update.message.reply_text(f"{update.effective_user.first_name} joined the lobby! ")
    
async def travel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in players:
        await update.message.reply_text("You are not in game yet!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /travel <zone_no>")
        return

    zone_no = int(context.args[0])
    # Check active zones in current game
    active_zones = None
    for game in games.values():
        if user_id in game["players"]:
            active_zones = game["active_zones"]
            break

    if not active_zones or zone_no not in active_zones:
        await update.message.reply_text("Invalid zone. Check active zones for your game!")
        return

    # Kick player from previous zone
    previous_zone = players.get(user_id, {}).get("zone")
    if previous_zone:
        # remove from previous zone group logic if needed
        pass

    # Assign new zone
    players.setdefault(user_id, {})["zone"] = zone_no
    await update.message.reply_text(f" You traveled to zone {zone_no} successfully!")
    
async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    inv = players.get(user_id, {}).get("inventory", [])
    if not inv:
        await update.message.reply_text("Your inventory is empty! ")
        return
    inv_text = "\n".join([f"• {item}" for item in inv])
    await update.message.reply_text(f" **Inventory:**\n{inv_text}", parse_mode="Markdown")
    
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()

    # cooldown check (20 sec)
    last = cooldowns.get((user_id, "search"), 0)
    if now - last < 20:
        await update.message.reply_text(f" Search is on cooldown. Try again in {int(20 - (now - last))} sec")
        return

    cooldowns[(user_id, "search")] = now

    # Items pool
    items_pool = [
        "Wooden Shield ", "Iron Shield ", "Golden Shield ", "Mythril Shield ",
        "Potion ", "Mushroom ", "Stone ", "Knife ", "Bow & Arrow ",
        "Gun ", "Bullets ", "Flare Gun ", "Gasoline & Fire ", "Elixir ",
        # Dungeon key rare
        "Dungeon Key "
    ]

    # Weighted rarity (higher damage/HP bonus  rarer)
    found_item = random.choices(
        items_pool,
        weights=[30, 25, 15, 10, 40, 35, 25, 20, 15, 10, 10, 15, 5, 5, 3],
        k=1
    )[0]

    players.setdefault(user_id, {}).setdefault("inventory", []).append(found_item)
    await update.message.reply_text(f" You searched and found: {found_item}")
    
async def airdrop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = players.setdefault(user_id, {})
    zone = player.get("zone")
    if not zone:
        await update.message.reply_text("You are not in a zone! Travel first using /travel <zone>")
        return

    # 1 min delay
    await update.message.reply_text(f" Airdrop summoned in zone {zone}! It will land in 1 min...")
    await asyncio.sleep(60)

    # Random reward pool
    rewards = ["Bulletproof Vest ", "Sniper ", "Dungeon Key "]
    reward = random.choice(rewards)
    airdrops[zone] = reward
    await update.message.reply_text(f" Airdrop landed in zone {zone}! Use /claim to get your reward.")
    
async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    zone = players.get(user_id, {}).get("zone")
    if not zone or zone not in airdrops:
        await update.message.reply_text("No airdrop to claim in your zone!")
        return

    reward = airdrops.pop(zone)
    players[user_id].setdefault("inventory", []).append(reward)
    await update.message.reply_text(f" You claimed: {reward}")
    
async def open_dungeon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    inventory = players.setdefault(user_id, {}).setdefault("inventory", [])
    if "Dungeon Key " not in inventory:
        await update.message.reply_text("You need a Dungeon Key  to open the dungeon!")
        return

    inventory.remove("Dungeon Key ")

    # Dungeon reward pool
    dungeon_rewards = ["Phoenix Sigil ", "Intangible Spell ", "Meteor Impact "]
    reward = random.choice(dungeon_rewards)

    inventory.append(reward)
    await update.message.reply_text(f" You opened a dungeon and got: {reward}")
    
async def select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /select <weapon_name>")
        return

    weapon = " ".join(context.args)
    inventory = players.setdefault(user_id, {}).setdefault("inventory", [])
    if weapon not in inventory:
        await update.message.reply_text("You don't have this weapon in your inventory! ")
        return

    # Equip only one weapon at a time
    players[user_id]["weapon"] = weapon
    await update.message.reply_text(f" You selected weapon: {weapon}")

async def equip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /equip <shield_name>")
        return

    shield = " ".join(context.args)
    inventory = players.setdefault(user_id, {}).setdefault("inventory", [])
    if shield not in inventory:
        await update.message.reply_text("You don't have this shield in your inventory! ")
        return

    # Equip shield and remove from inventory
    inventory.remove(shield)
    shield_points = {
        "Wooden Shield ": 1,
        "Iron Shield ": 3,
        "Golden Shield ": 6,
        "Mythril Shield ": 10,
        "Bulletproof Vest ": 20
    }.get(shield, 0)

    players[user_id]["shield"] = min(players[user_id].get("shield", 0) + shield_points, 40)
    await update.message.reply_text(f" You equipped {shield} (Shield points: {players[user_id]['shield']})")
    
async def use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /use <item_name>")
        return

    item = " ".join(context.args)
    inventory = players.setdefault(user_id, {}).setdefault("inventory", [])
    if item not in inventory:
        await update.message.reply_text("You don't have this item! ")
        return

    hp = players[user_id].get("hp", 20)
    if item == "Potion ":
        if hp >= 20:
            await update.message.reply_text("Your HP is full! Cannot use Potion ")
            return
        players[user_id]["hp"] = min(hp + 10, 20)
        inventory.remove(item)
        await update.message.reply_text(f" You used Potion  (HP: {players[user_id]['hp']}/20)")
    elif item == "Mushroom ":
        if hp >= 20:
            await update.message.reply_text("Your HP is full! Cannot use Mushroom ")
            return
        players[user_id]["hp"] = min(hp + 2, 20)
        inventory.remove(item)
        await update.message.reply_text(f" You used Mushroom  (HP: {players[user_id]['hp']}/20)")
    elif item == "Elixir ":
        if hp >= 20:
            await update.message.reply_text("Your HP is full! Cannot use Elixir ")
            return
        players[user_id]["hp"] = min(hp + 20, 20)
        inventory.remove(item)
        await update.message.reply_text(f" You used Elixir  (HP: {players[user_id]['hp']}/20)")
    else:
        await update.message.reply_text("Item cannot be used directly!")
        
async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker_id = update.effective_user.id
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("Use /kill @username or reply to attack!")
        return

    # Get target user_id
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        # Assuming username to user_id mapping exists
        target_id = None  # TODO: map username to id
        await update.message.reply_text("Reply attack not implemented yet")
        return

    attacker = players.setdefault(attacker_id, {})
    target = players.setdefault(target_id, {})

    # Check same zone
    if attacker.get("zone") != target.get("zone"):
        await update.message.reply_text("Target is not in your zone! ")
        return

    now = time.time()
    last_attack = cooldowns.get((attacker_id, "attack"), 0)
    if now - last_attack < 10:
        await update.message.reply_text(f" Attack cooldown. Try after {int(10 - (now - last_attack))} sec")
        return
    cooldowns[(attacker_id, "attack")] = now

    # Calculate damage
    weapon_damage = {
        "Stone ": 1,
        "Knife ": 2,
        "Bow & Arrow ": 4,
        "Gun ": 10
    }.get(attacker.get("weapon"), 1)  # default punch = 1

    target_shield = target.get("shield", 0)
    remaining_damage = max(0, weapon_damage - target_shield)
    target["shield"] = max(0, target_shield - weapon_damage)
    target["hp"] = max(0, target.get("hp", 20) - remaining_damage)

    await update.message.reply_text(
        f" You attacked {target_id} for {weapon_damage} damage! "
        f"Target HP: {target['hp']}/20 | Shield: {target['shield']}"
    )

    # Death check
    if target["hp"] <= 0:
        # Check for Phoenix Sigil
        if "Phoenix Sigil " in target.get("inventory", []):
            target["inventory"].remove("Phoenix Sigil ")
            target["hp"] = 20
            target["shield"] = 0
            await update.message.reply_text(f" {target_id} revived using Phoenix Sigil!")
        else:
            await update.message.reply_text(f" {target_id} has died!")
            
async def hp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = players.get(user_id, {})
    await update.message.reply_text(
        f" HP: {player.get('hp', 20)}/20 |  Shield: {player.get('shield', 0)}"
    )
    
async def impact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /impact <zone_no>")
        return

    zone_no = int(context.args[0])
    player_inv = players.setdefault(user_id, {}).setdefault("inventory", [])
    if "Meteor Impact " not in player_inv:
        await update.message.reply_text("You don't own Meteor Impact ")
        return

    player_inv.remove("Meteor Impact ")
    for pid, p in players.items():
        if p.get("zone") == zone_no:
            p["hp"] = max(0, p.get("hp", 20) - 7)
    await update.message.reply_text(f" Meteor Impact hit zone {zone_no}! All players there took 7 damage")
    
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text(" You are not an admin!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /reset <user_id/all>")
        return

    target = context.args[0]
    if target.lower() == "all":
        players.clear()
        lobby.clear()
        airdrops.clear()
        cooldowns.clear()
        await update.message.reply_text(" All game data reset! Fresh start!")
    else:
        try:
            uid = int(target)
            if uid in players:
                del players[uid]
                await update.message.reply_text(f" Player {uid} data reset!")
            else:
                await update.message.reply_text("User not found!")
        except ValueError:
            await update.message.reply_text("Invalid user ID!")
            
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text(" You are not an admin!")
        return

    await update.message.reply_text(" Restarting bot...")
    # For Replit or other host: just reconnect / reload main loop
    # Placeholder logic:
    # sys.exit()  # Replit will auto restart bot script
    
async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text(" You are not an admin!")
        return

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
            context.args = context.args[1:]
        except ValueError:
            await update.message.reply_text("Invalid user ID or usage!")
            return

    if not context.args:
        await update.message.reply_text("Usage: /add_item <item_name>")
        return

    item = " ".join(context.args)
    players.setdefault(target_id, {}).setdefault("inventory", []).append(item)
    await update.message.reply_text(f" {item} added to user {target_id}'s inventory!")
    
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text(" You are not an admin!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /set_time <minutes>")
        return

    try:
        minutes = int(context.args[0])
        current_game["total_time"] = minutes * 60
        await update.message.reply_text(f" Game duration set to {minutes} minutes")
    except ValueError:
        await update.message.reply_text("Invalid number!")
        
async def myprofile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = players.get(user_id)
    if not player:
        await update.message.reply_text("You are not in a game yet! Join first using /join")
        return

    kills = player.get("kills", 0)
    coins = player.get("coins", 0)
    total_games = player.get("games_played", 0)
    hp = player.get("hp", 20)
    shield = player.get("shield", 0)
    zone = player.get("zone", "N/A")

    await update.message.reply_text(
        f" **Your Profile:**\n"
        f"• ID: {user_id}\n"
        f"• Zone: {zone}\n"
        f"• HP: {hp}/20 | Shield: {shield}\n"
        f"• Kills: {kills}\n"
        f"• Coins: {coins}\n"
        f"• Games Played: {total_games}",
        parse_mode="Markdown"
    )
    
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_players = sorted(players.items(), key=lambda x: x[1].get("coins", 0), reverse=True)[:10]
    if not top_players:
        await update.message.reply_text("No players yet!")
        return

    text = " **Top 10 Players by Coins:**\n"
    for idx, (uid, p) in enumerate(top_players, start=1):
        text += f"{idx}. {uid} - {p.get('coins',0)} coins\n"
    await update.message.reply_text(text, parse_mode="Markdown")
    
async def map(update, context):
    zone_map = {}
    for uid, p in players.items():
        zone = p.get("zone", None)
        if zone:
            zone_map.setdefault(zone, []).append(uid)

    text = " **Current Zone Map:**\n"
    for z, uids in zone_map.items():
        text += f"• Zone {z}: {len(uids)} player(s)\n"
        if z in dungeon_zones:
            text += "   Dungeon present\n"
        if z in airdrops:
            text += f"   Airdrop: {airdrops[z]}\n"
        if z in poison_zones:
            dmg = poison_zones[z]["damage"]
            text += f"   Poisonous Zone - Damage: {dmg}/5 sec\n"

    await update.message.reply_text(text, parse_mode="Markdown")
    
async def end_game():
    for uid, p in players.items():
        zone = p.get("zone")
        # Optionally send DM: Game ended
        # Kick from all zones / reset temporary data
        p["zone"] = None

    lobby.clear()
    # Optional: announce in main group
    await bot.send_message(chat_id=main_group_id, text=" Game has ended! Thanks for playing!")
    
app = ApplicationBuilder().token(TOKEN).build()

# Core Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help))
app.add_handler(CommandHandler("myprofile", myprofile))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("map", map))

# Game Lobby & Travel
app.add_handler(CommandHandler("start_game", start_game))
app.add_handler(CommandHandler("join", join))
app.add_handler(CommandHandler("extend", extend))
app.add_handler(CommandHandler("force_start", force_start))
app.add_handler(CommandHandler("cancel_game", cancel_game))
app.add_handler(CommandHandler("travel", travel))

# Combat & Items
app.add_handler(CommandHandler("select", select))
app.add_handler(CommandHandler("equip", equip))
app.add_handler(CommandHandler("use", use))
app.add_handler(CommandHandler("kill", kill))
app.add_handler(CommandHandler("hp", hp))
app.add_handler(CommandHandler("impact", impact))
app.add_handler(CommandHandler("claim", claim_airdrop))
app.add_handler(CommandHandler("open", open_dungeon))
app.add_handler(CommandHandler("search", search))

# Admin Commands
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("restart", restart))
app.add_handler(CommandHandler("add_item", add_item))
app.add_handler(CommandHandler("set_time", set_time))

if __name__ == "__main__":
    print(" Bot is starting...")
    app.run_polling()