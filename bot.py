import discord
import os
import json
import asyncio
import requests
from dotenv import load_dotenv


BOT_NAME = "ClankerBot"

load_dotenv()  # This loads variables from .env


# === CONFIG ===
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1300862501407162449  # convert to int
CHECK_INTERVAL = 30000  # 30 min

# === test ===
print("TOKEN:", TOKEN)  # Debug to make sure it loaded
print("CHANNEL_ID:", CHANNEL_ID)

# === FILES ===
WISHLIST_FILE = "data/wishlists.json"
TRACKED_FILE = "data/tracked_games.json"

# === HELPERS ===
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

def get_game_price(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        response = requests.get(url, timeout=10).json()
        data = response[str(appid)]["data"]
        if "price_overview" in data:
            price = data["price_overview"]["final"] / 100
            discount = data["price_overview"]["discount_percent"]
            name = data["name"]
            return price, discount, name
        else:
            return None, 0, data.get("name", f"AppID {appid}")
    except:
        return None, 0, f"AppID {appid}"

# === DISCORD CLIENT ===
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === COMMANDS ===
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    user_id = str(message.author.id)
    wishlists = load_json(WISHLIST_FILE)
    tracked_games = load_json(TRACKED_FILE)

    if content.startswith("!addwish"):
        try:
            appid = content.split()[1]
            wishlists.setdefault(user_id, [])
            if appid not in wishlists[user_id]:
                wishlists[user_id].append(appid)
                save_json(WISHLIST_FILE, wishlists)
                if appid not in tracked_games:
                    tracked_games[appid] = {"last_price": None}
                    save_json(TRACKED_FILE, tracked_games)
                await message.channel.send(f"✅ Added `{appid}` to your wishlist!")
            else:
                await message.channel.send(f"⚠ `{appid}` is already in your wishlist.")
        except:
            await message.channel.send("Usage: `!addwish <Steam AppID>`")

    elif content.startswith("!removewish"):
        try:
            appid = content.split()[1]
            if user_id in wishlists and appid in wishlists[user_id]:
                wishlists[user_id].remove(appid)
                save_json(WISHLIST_FILE, wishlists)
                await message.channel.send(f"❌ Removed `{appid}` from your wishlist!")
            else:
                await message.channel.send(f"⚠ `{appid}` not found in your wishlist.")
        except:
            await message.channel.send("Usage: `!removewish <Steam AppID>`")

    elif content.startswith("!list"):
        user_wishlist = wishlists.get(user_id, [])
        if not user_wishlist:
            await message.channel.send("Your wishlist is empty.")
        else:
            text = "Your wishlist:\n" + "\n".join(user_wishlist)
            await message.channel.send(f"```{text}```")

# === BACKGROUND TASK ===
async def check_prices():
    await client.wait_until_ready()
    while not client.is_closed():
        tracked_games = load_json(TRACKED_FILE)
        wishlists = load_json(WISHLIST_FILE)
        channel = client.get_channel(CHANNEL_ID)

        for appid, info in tracked_games.items():
            price, discount, name = get_game_price(appid)
            if price is None:
                continue

            last_price = info.get("last_price")
            if last_price is None or price < last_price:
                if discount > 0:
                    message = f"🔥 **SALE ALERT!** `{name}` is now ${price:.2f} ({discount}% off)"
                    users = [f"<@{uid}>" for uid, apps in wishlists.items() if appid in apps]
                    if users:
                        message += "\n" + " ".join(users)
                    await channel.send(message)

            tracked_games[appid]["last_price"] = price

        save_json(TRACKED_FILE, tracked_games)
        await asyncio.sleep(CHECK_INTERVAL)

# === START BOT ===
@client.event
async def on_ready():
    print(f"{BOT_NAME} is online!")
    client.loop.create_task(check_prices())



print("TOKEN:", TOKEN)


client.run(TOKEN)