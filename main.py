import discord
import requests
import time
import csv
from datetime import datetime, timedelta
import asyncio

# ⚠️ Replace this with your real token before deploying
TOKEN = "DISCORD_TOKEN"
USERNAME = "shinshinshina04"
INTERVAL_SECONDS = 120
DAILY_LOG_FILE = f"roblox_presence_{datetime.now().strftime('%Y-%m-%d')}.csv"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

HEADERS = {"Content-Type": "application/json"}

# Get Roblox user ID from username
def get_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    body = {"usernames": [username]}
    response = requests.post(url, json=body, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data["data"][0]["id"] if data["data"] else None
    return None

# Get presence info of the user
def get_user_presence(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    body = {"userIds": [user_id]}
    response = requests.post(url, json=body, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["userPresences"][0]
    return None

# Log status to CSV
async def log_presence(timestamp, status, game_name=""):
    with open(DAILY_LOG_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, status, game_name])

# Analyze daily activity
def analyze_daily_log():
    try:
        with open(DAILY_LOG_FILE, mode='r') as file:
            reader = csv.reader(file)
            rows = list(reader)
    except FileNotFoundError:
        return None

    online_sessions = playing_sessions = offline_sessions = 0
    time_online = time_playing = time_offline = timedelta()
    online_count = playing_count = offline_count = 0
    previous_time = previous_status = last_counted_status = None

    for row in rows:
        current_time = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        status = row[1]

        if previous_time:
            duration = current_time - previous_time
            if previous_status == "Online":
                time_online += duration
            elif previous_status == "Playing":
                time_playing += duration
            elif previous_status == "Offline":
                time_offline += duration

        if status == "Online":
            online_sessions += 1
        elif status == "Playing":
            playing_sessions += 1
        elif status == "Offline":
            offline_sessions += 1

        if status != last_counted_status:
            if status == "Online":
                online_count += 1
            elif status == "Playing":
                playing_count += 1
            elif status == "Offline":
                offline_count += 1
            last_counted_status = status

        previous_time = current_time
        previous_status = status

    return {
        "Online Sessions": online_sessions,
        "Playing Sessions": playing_sessions,
        "Offline Sessions": offline_sessions,
        "Online Count": online_count,
        "Play Count": playing_count,
        "Offline Count": offline_count,
        "Time Online": str(time_online),
        "Time Playing": str(time_playing),
        "Time Offline": str(time_offline)
    }

# Bot events
@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(track_user())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = message.content.lower()

    if msg.startswith("/status"):
        username = message.content.split(' ')[1] if len(message.content.split(' ')) > 1 else USERNAME
        user_id = get_user_id(username)
        if not user_id:
            await message.channel.send(f"❌ User not found: `{username}`")
            return
        presence = get_user_presence(user_id)
        if presence:
            status = presence["userPresenceType"]
            if status == 0:
                await message.channel.send(f"🟥 `{username}` is **Offline**")
            elif status == 1:
                await message.channel.send(f"🟨 `{username}` is **Online**, but not in a game.")
            elif status == 2:
                game_name = presence.get("lastLocation", "")
                await message.channel.send(f"🟩 `{username}` is **Playing** `{game_name}`")
        else:
            await message.channel.send("⚠️ Could not fetch status.")

    elif msg.startswith("/summary"):
        summary = analyze_daily_log()
        if not summary:
            await message.channel.send("⚠️ No log file found for today.")
            return
        summary_msg = "\n".join([f"**{key}**: {value}" for key, value in summary.items()])
        await message.channel.send(f"📊 **Daily Summary for `{USERNAME}`**:\n{summary_msg}")

    elif msg.startswith("/history"):
        try:
            with open(DAILY_LOG_FILE, mode='r') as file:
                logs = file.readlines()
                if not logs:
                    await message.channel.send("⚠️ No history available.")
                    return
                msg = "📜 **Today's History:**\n"
                for line in logs[-15:]:
                    parts = line.strip().split(",")
                    timestamp = parts[0]
                    status = parts[1]
                    game = parts[2] if len(parts) > 2 else ""
                    msg += f"`{timestamp}` - **{status}**"
                    if game:
                        msg += f" in *{game}*"
                    msg += "\n"
                await message.channel.send(msg)
        except FileNotFoundError:
            await message.channel.send("⚠️ No history file found for today.")

# Background task to track presence
async def track_user():
    await client.wait_until_ready()
    user_id = get_user_id(USERNAME)
    if not user_id:
        print(f"❌ User not found: {USERNAME}")
        return

    print(f"🔍 Tracking user: {USERNAME} (ID: {user_id})")

    try:
        while not client.is_closed():
            presence = get_user_presence(user_id)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if presence:
                status = presence["userPresenceType"]
                if status == 0:
                    await log_presence(now, "Offline")
                elif status == 1:
                    await log_presence(now, "Online")
                elif status == 2:
                    game_name = presence.get("lastLocation", "")
                    await log_presence(now, "Playing", game_name)
                print(f"[{now}] Logged presence: {status}")
            await asyncio.sleep(INTERVAL_SECONDS)
    except asyncio.CancelledError:
        print("Tracking cancelled.")

# Run the bot
client.run(TOKEN)
