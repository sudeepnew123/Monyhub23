import telebot
import random
import threading
import time
import json
import os
from datetime import datetime, timedelta

API_TOKEN = '7606806490:AAFe2V7yzGe6gpnD9Z9bWrFMdSnEWquuRIw'  # Replace with your bot token
bot = telebot.TeleBot(API_TOKEN)

DATA_FILE = "monyhub_data.json"

user_db = {}
transaction_db = {}
last_daily_claim = {}

# Save/load functions
def save_all_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "users": user_db,
            "transactions": transaction_db,
            "last_daily": {str(k): v.isoformat() for k, v in last_daily_claim.items()}
        }, f, indent=4)

def load_all_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            global user_db, transaction_db, last_daily_claim
            user_db = data.get("users", {})
            transaction_db = data.get("transactions", {})
            last_daily_claim = {
                int(k): datetime.fromisoformat(v) for k, v in data.get("last_daily", {}).items()
            }

load_all_data()

gift_emojis = {
    700: "🨨❤️",
    600: "😘",
    900: "💀",
    1000: "🫕"
}

store_items = {
    "🨨❤️": 700,
    "😘": 600,
    "💀": 900,
    "🫕": 1000,
}

GROUP_ID = -1002315817553

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    user_db.setdefault(user_id, {"name": message.from_user.first_name, "balance": 0, "collection": []})
    save_all_data()
    bot.reply_to(message, """Welcome to Monyhub!

Commands:
/profile - View your profile
/balance - Check your balance
/send or /se [amount] - Send money
/receive or /rc [transaction_code] - Receive money
/daily - Claim daily ₹100
/history - See your transactions
/redeem [gift_code] - Redeem a gift code
/leaderboard - Richest users
/store - Buy emojis
/mycollection - Your bought emojis

Owner: @HeartStealer_X
Join: https://t.me/+UBlGtjD5wjc5NzJl""")

@bot.message_handler(commands=['store'])
def show_store(message):
    user_db.setdefault(message.from_user.id, {"name": message.from_user.first_name, "balance": 0, "collection": []})
    store_list = "\n".join([f"{emoji} - ₹{price}" for emoji, price in store_items.items()])
    bot.reply_to(message, f"Store:\n\n{store_list}\n\nBuy using: /buy [emoji]")

@bot.message_handler(commands=['buy'])
def buy_emoji(message):
    user_id = message.from_user.id
    user = user_db.setdefault(user_id, {"name": message.from_user.first_name, "balance": 0, "collection": []})
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: /buy [emoji]")
        return

    emoji = parts[1]
    if emoji not in store_items:
        bot.reply_to(message, "Emoji not in store.")
        return

    price = store_items[emoji]
    if user["balance"] < price:
        bot.reply_to(message, f"Not enough balance. You need ₹{price - user['balance']} more.")
        return

    user["balance"] -= price
    user["collection"].append(emoji)
    save_all_data()
    bot.reply_to(message, f"Bought {emoji} for ₹{price}. New balance: ₹{user['balance']}")

@bot.message_handler(commands=['mycollection'])
def show_collection(message):
    user = user_db.setdefault(message.from_user.id, {"name": message.from_user.first_name, "balance": 0, "collection": []})
    if not user["collection"]:
        bot.reply_to(message, "You have no emojis. Buy from /store.")
    else:
        bot.reply_to(message, "Your Collection:\n" + "\n".join(user["collection"]))

@bot.message_handler(commands=['profile'])
def check_profile(message):
    user = user_db.setdefault(message.from_user.id, {"name": message.from_user.first_name, "balance": 0})
    bot.reply_to(message, f"Name: {user['name']}\nBalance: ₹{user['balance']}")

@bot.message_handler(commands=['balance'])
def check_balance(message):
    balance = user_db.setdefault(message.from_user.id, {"name": message.from_user.first_name, "balance": 0})['balance']
    bot.reply_to(message, f"Your balance: ₹{balance}")

@bot.message_handler(commands=['send', 'se'])
def send_money(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Use: /send [amount]")
            return

        amount = int(parts[1])
        sender_id = message.from_user.id
        user = user_db.setdefault(sender_id, {"name": message.from_user.first_name, "balance": 0})

        if user["balance"] < amount:
            bot.reply_to(message, "Insufficient balance!")
            return

        code = str(random.randint(1000, 9999))
        transaction_db[code] = {"sender_id": sender_id, "amount": amount, "status": "pending"}
        save_all_data()
        bot.reply_to(message, f"Transaction Code: {code}. Share with receiver.")

    except ValueError:
        bot.reply_to(message, "Enter a valid amount.")

@bot.message_handler(commands=['receive', 'rc'])
def receive_money(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: /receive [code]")
        return

    code = parts[1]
    if code not in transaction_db:
        bot.reply_to(message, "Invalid code!")
        return

    tx = transaction_db[code]
    if tx['status'] == 'completed':
        bot.reply_to(message, "Already completed.")
        return

    recipient_id = message.from_user.id
    user_db.setdefault(recipient_id, {"name": message.from_user.first_name, "balance": 0})
    user_db[tx['sender_id']]['balance'] -= tx['amount']
    user_db[recipient_id]['balance'] += tx['amount']
    tx['status'] = 'completed'
    save_all_data()

    bot.reply_to(message, f"Received ₹{tx['amount']}.")
    bot.send_message(tx['sender_id'], f"₹{tx['amount']} sent to {message.from_user.first_name} is complete.")
    
@bot.message_handler(commands=['pay'])
def mention_send(message):
    try:
        if not message.entities or message.entities[1].type != 'pay':
            bot.reply_to(message, "Tag a user like this: /pay @username amount")
            return

        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Use: /pay @username amount")
            return

        username = parts[1].lstrip("@")
        amount = int(parts[2])
        sender_id = message.from_user.id

        # Check sender balance
        sender = user_db.setdefault(sender_id, {"name": message.from_user.first_name, "balance": 0})
        if sender["balance"] < amount:
            bot.reply_to(message, "Insufficient balance.")
            return

        # Find recipient by username
        recipient_id = None
        for uid, data in user_db.items():
            if data.get("name", "").lower() == username.lower():
                recipient_id = uid
                break

        if recipient_id is None:
            bot.reply_to(message, "User not found or hasn't started the bot.")
            return

        # Transfer
        sender["balance"] -= amount
        user_db[recipient_id]["balance"] += amount
        save_all_data()

        bot.reply_to(message, f"₹{amount} sent to @{username}.")
        bot.send_message(recipient_id, f"You've received ₹{amount} from {message.from_user.first_name}!")

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")
        

@bot.message_handler(commands=['history'])
def view_history(message):
    user_id = message.from_user.id
    history = []
    for code, tx in transaction_db.items():
        if tx['sender_id'] == user_id or tx.get('status') == 'completed':
            sender = user_db[tx['sender_id']]['name']
            history.append(f"Code {code}: {tx['status']} ₹{tx['amount']} from {sender}")
    bot.reply_to(message, "\n".join(history) if history else "No transactions found.")

@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    top_users = sorted(user_db.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    leaderboard_text = "🏆 <b>Leaderboard</b> 🏆\n\n" + "\n".join([
        f"{i+1}. {data['name']} - ₹{data['balance']}" for i, (uid, data) in enumerate(top_users)
    ])
    bot.reply_to(message, leaderboard_text, parse_mode="HTML")

@bot.message_handler(commands=['redeem'])
def redeem_code(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: /redeem [gift_code]")
        return

    code = parts[1]
    if code not in transaction_db:
        bot.reply_to(message, "Invalid gift code!")
        return

    tx = transaction_db[code]
    if tx['status'] == 'completed':
        bot.reply_to(message, "This gift code has already been redeemed.")
        return

    recipient_id = message.from_user.id
    user_db.setdefault(recipient_id, {"name": message.from_user.first_name, "balance": 0})
    user_db[recipient_id]['balance'] += tx['amount']
    tx['status'] = 'completed'
    save_all_data()

    bot.reply_to(message, f"Redeemed ₹{tx['amount']}! New balance: ₹{user_db[recipient_id]['balance']}")
    bot.send_message(GROUP_ID, f"Gift code {code} has been redeemed by {message.from_user.first_name}. Amount: ₹{tx['amount']}")
    
@bot.message_handler(commands=['mine'])
def mine_game(message):
    user_id = message.from_user.id
    user = user_db.setdefault(user_id, {"name": message.from_user.first_name, "balance": 0})

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(message, "Use: /mine [1-5]")
        return

    choice = int(parts[1])
    if choice < 1 or choice > 5:
        bot.reply_to(message, "Pick a number between 1 and 5.")
        return

    bomb_position = random.randint(1, 5)

    if choice == bomb_position:
        user["balance"] = max(0, user["balance"] - 50)
        result = f"💣 Boom! You hit the bomb at position {bomb_position}.\nYou lost ₹50. New balance: ₹{user['balance']}"
    else:
        user["balance"] += 100
        result = f"✅ Safe! No bomb at position {choice}.\nYou won ₹100! New balance: ₹{user['balance']}"

    save_all_data()
    bot.reply_to(message, result)
    
@bot.message_handler(commands=['profile'])
def check_profile(message):
    user_id = message.from_user.id
    user = user_db.setdefault(user_id, {"name": message.from_user.first_name, "balance": 0})

    caption = f"""
<b>👤 Profile Info</b>

<b>Name:</b> {user['name']}
<b>User ID:</b> {user_id}
<b>Balance:</b> ₹{user['balance']}

Use <b>/daily</b> to claim ₹100 daily gift!
"""

    try:
        photos = bot.get_user_profile_photos(user_id)
        if photos.total_count > 0:
            file_id = photos.photos[0][-1].file_id
            bot.send_photo(message.chat.id, file_id, caption=caption, parse_mode="HTML")
        else:
            bot.reply_to(message, caption, parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"Error fetching profile photo: {str(e)}")

# Gift sender

def gift_sender_thread():
    while True:
        try:
            code = str(random.randint(10000, 99999))
            amount = random.choice([3, 10, 25, 50, 100, 300, 500, 600, 700, 900, 1000])
            emoji = gift_emojis.get(amount, '')

            message = f"""
<b>🏧 New Gift Alert! 🏧</b>

🔑 <b>Gift Code</b>: <code>{code}</code>
💸 <b>Amount</b>: ₹{amount} {emoji}

Use <code>/redeem {code}</code> to claim it!
Next gift coming soon! ⏳

<b>Owner</b>: @HeartStealer_X
<b>Group</b>: <a href="https://t.me/+UBlGtjD5wjc5NzJl">Monyhub</a>
"""
            transaction_db[code] = {"sender_id": 0, "amount": amount, "status": "pending"}
            bot.send_message(GROUP_ID, message, parse_mode="HTML")
            save_all_data()
        except Exception as e:
            print(f"[Gift Sender Error] {e}")
        time.sleep(300)

# Auto save thread

def auto_saver():
    while True:
        try:
            save_all_data()
        except Exception as e:
            print(f"[Auto Save Error] {e}")
        time.sleep(30)

# Start threads
gift_thread = threading.Thread(target=gift_sender_thread)
gift_thread.daemon = True
gift_thread.start()

auto_thread = threading.Thread(target=auto_saver)
auto_thread.daemon = True
auto_thread.start()

bot.infinity_polling(timeout=10, long_polling_timeout=5)
