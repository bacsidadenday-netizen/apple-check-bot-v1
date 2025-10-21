import requests
import time
import json
import os
import threading
import random
from flask import Flask

# --- PING SERVER REPLIT ---
app = Flask('')


@app.route('/')
def home():
    return "Bot is running!"


def run_web():
    app.run(host='0.0.0.0', port=8080)


threading.Thread(target=run_web, daemon=True).start()

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PASSWORD = os.getenv("BOT_PASSWORD", "")  # Mật khẩu đăng nhập bot
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# --- FILE LƯU DANH SÁCH ---
WATCHLIST_FILE = "watchlist.json"
AUTH_FILE = "authorized.json"

# --- DỮ LIỆU CỐ ĐỊNH ---
PRODUCTS = {
    "ip17pm_2t_cosmic": ("2TB Cosmic", "MFYK4J/A"),
    "ip17pm_1t_cosmic": ("1TB Cosmic", "MFYG4J/A"),
    "ip17pm_512_cosmic": ("512GB Cosmic", "MFYD4J/A"),
    "ip17pm_256_cosmic": ("256GB Cosmic", "MFY94J/A"),
    "ip17pm_256_white": ("256GB Trắng", "MFY84J/A"),
    "ip17pm_512_white": ("512GB Trắng", "MFYC4J/A"),
    "ip17pm_1t_white": ("1TB Trắng", "MFYF4J/A"),
    "ip17pm_2t_white": ("2TB Trắng", "MFYJ4J/A"),
    "ip17pm_256_blue": ("256GB Xanh", "MFYA4J/A"),
    "ip17pm_512_blue": ("512GB Xanh", "MFYE4J/A"),
    "ip17pm_1t_blue": ("1TB Xanh", "MFYH4J/A"),
    "ip17pm_2t_blue": ("2TB Xanh", "MFYL4J/A"),
}

STORES = [
    "Shinjuku", "Ginza", "Omotesando", "Marunouchi", "Shibuya", "Roppongi",
    "Yokohama", "Nagoya Sakae", "Fukuoka", "Sapporo", "Osaka Shinsaibashi",
    "Kobe", "Sendai Ichibancho"
]

# --- GLOBAL ---
watchlist = {}
user_state = {}
authorized_users = set()


# --- TIỆN ÍCH LƯU / TẢI ---
def load_watchlist():
    global watchlist
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            watchlist = json.load(f)
    else:
        watchlist = {}


def save_watchlist():
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def load_auth():
    global authorized_users
    if os.path.exists(AUTH_FILE):
        with open(AUTH_FILE, "r") as f:
            authorized_users = set(json.load(f))
    else:
        authorized_users = set()


def save_auth():
    with open(AUTH_FILE, "w") as f:
        json.dump(list(authorized_users), f)


# --- GỬI TIN NHẮN ---
def send_message(text, chat_id, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{BASE_URL}/sendMessage", data=payload, timeout=10)
    except Exception as e:
        print("❌ Telegram error:", e)


# --- KIỂM TRA KHO ---
def check_stock(part_number, location):
    if location == "TEST_STORE":
        return [{
            "name": "Apple Store TEST_STORE",
            "address": "123 Test Street, Tokyo",
            "phone": "03-0000-0000",
            "email": "teststore@apple.com"
        }]

    ts = int(time.time() * 1000) + random.randint(0, 999)
    url = f"https://www.apple.com/jp/shop/retail/pickup-message?parts.0={part_number}&location={location}&_={ts}"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        stores = data.get("body", {}).get("stores", [])
        available = []

        for s in stores:
            info = s.get("partsAvailability", {}).get(part_number, {})
            if info.get("pickupDisplay") == "available":
                available.append({
                    "name":
                    s.get("storeName"),
                    "address":
                    s.get("address", {}).get("address", "Không rõ địa chỉ"),
                    "phone":
                    s.get("phoneNumber", "Không có số điện thoại"),
                    "email":
                    s.get("storeEmail", "Không có email")
                })
        return available

    except Exception as e:
        print("⚠️ API error:", e)
        return []


# --- GIAO DIỆN ---
def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{
                "text": "➕ Theo dõi sản phẩm"
            }],
            [{
                "text": "📋 Danh sách theo dõi"
            }],
            [{
                "text": "📦 Kiểm tra trạng thái"
            }],
            [{
                "text": "🧪 Test báo có hàng"
            }],
        ],
        "resize_keyboard":
        True
    }
    send_message("🤖 Chọn thao tác:", chat_id, keyboard)


def show_product_selection(chat_id):
    keyboard = {
        "inline_keyboard": [[{
            "text": name,
            "callback_data": f"select_product|{name}"
        }] for name in PRODUCTS.keys()]
    }
    send_message("📱 Chọn sản phẩm muốn theo dõi:", chat_id, keyboard)


def show_store_selection(chat_id, product_name):
    keyboard = {
        "inline_keyboard": [[{
            "text":
            store,
            "callback_data":
            f"select_store|{product_name}|{store}"
        }] for store in STORES]
    }
    send_message(f"🏬 Chọn cửa hàng cho:\n{product_name}", chat_id, keyboard)


def show_watchlist(chat_id):
    if not watchlist:
        send_message("📭 Danh sách theo dõi trống.", chat_id)
        return
    keyboard = {"inline_keyboard": []}
    msg = "📋 Danh sách theo dõi:\n\n"
    for key in watchlist.keys():
        msg += f"• {key}\n"
        keyboard["inline_keyboard"].append([{
            "text":
            f"❌ Xóa {key}",
            "callback_data":
            f"delete_watch|{key}"
        }])
    send_message(msg, chat_id, keyboard)


# --- XỬ LÝ UPDATE ---
def handle_update(update):
    message = update.get("message")
    callback = update.get("callback_query")

    if message:
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        # --- KIỂM TRA XÁC THỰC ---
        if chat_id not in authorized_users:
            if text.startswith("/start"):
                send_message("🔒 Vui lòng nhập mật khẩu để sử dụng bot:",
                             chat_id)
            elif text.strip() == PASSWORD:
                authorized_users.add(chat_id)
                save_auth()
                send_message("✅ Đăng nhập thành công! Bạn có thể sử dụng bot.",
                             chat_id)
                show_main_menu(chat_id)
            else:
                send_message(
                    "❌ Sai mật khẩu hoặc chưa nhập mật khẩu. Gõ /start để thử lại.",
                    chat_id)
            return

        # --- NGƯỜI DÙNG ĐÃ XÁC THỰC ---
        if text == "/start":
            show_main_menu(chat_id)
        elif text == "➕ Theo dõi sản phẩm":
            show_product_selection(chat_id)
        elif text == "📋 Danh sách theo dõi":
            show_watchlist(chat_id)
        elif text == "📦 Kiểm tra trạng thái":
            # 🔹 Hiệu ứng typing
            requests.post(f"{BASE_URL}/sendChatAction",
                          data={
                              "chat_id": chat_id,
                              "action": "typing"
                          })
            time.sleep(1.5)

            # 🔹 Gửi tin nhắn chờ
            waiting = requests.post(
                f"{BASE_URL}/sendMessage",
                data={
                    "chat_id":
                    chat_id,
                    "text":
                    "🔍 Đang kiểm tra trạng thái từ Apple... vui lòng chờ trong giây lát ⏳"
                },
            ).json()

            # 🔹 Kiểm tra từng sản phẩm
            msg = "📦 **Trạng thái theo dõi hiện tại:**\n\n"
            has_available = False
            for key, part in watchlist.items():
                product, location = key.split(" | ")
                available_stores = check_stock(part, location)
                if available_stores:
                    has_available = True
                    msg += f"✅ *{product}* tại *{location}*:\n"
                    for s in available_stores:
                        msg += (f"🏬 {s['name']}\n"
                                f"📍 {s['address']}\n"
                                f"📞 {s['phone']}\n"
                                f"📧 {s['email']}\n\n")
                else:
                    msg += f"❌ *{product}* tại *{location}*: HẾT HÀNG\n\n"

            if not has_available:
                msg += "🚫 Hiện tại không có sản phẩm nào còn hàng.\n\n"

            # 🔹 Cập nhật lại tin nhắn
            requests.post(
                f"{BASE_URL}/editMessageText",
                data={
                    "chat_id": chat_id,
                    "message_id": waiting["result"]["message_id"],
                    "text": msg.strip(),
                    "parse_mode": "Markdown"
                },
            )

        elif text == "🧪 Test báo có hàng" or text == "/test":
            product_name = "Test iPhone"
            store = "TEST_STORE"
            part_number = "TEST123"
            key = f"{product_name} | {store}"
            watchlist[key] = part_number
            save_watchlist()
            available = check_stock(part_number, store)
            if available:
                s = available[0]
                send_message(
                    f"🚨 Có hàng!\n📱 {product_name}\n🏬 {s['name']}\n📍 {s['address']}\n📞 {s['phone']}\n📧 {s['email']}",
                    chat_id)
            else:
                send_message("❌ Hiện tại chưa có hàng.", chat_id)

    elif callback:
        data = callback.get("data", "")
        chat_id = callback["message"]["chat"]["id"]

        if data.startswith("select_product|"):
            _, product_name = data.split("|", 1)
            user_state[chat_id] = {"product": product_name}
            show_store_selection(chat_id, product_name)

        elif data.startswith("select_store|"):
            _, product_name, store = data.split("|", 2)
            part_number = PRODUCTS[product_name][1]
            key = f"{product_name} | {store}"
            watchlist[key] = part_number
            save_watchlist()

            available = check_stock(part_number, store)
            if available:
                store_names = [s['name'] for s in available]
                status = f"✅ Hiện CÓ HÀNG tại {', '.join(store_names)}"
            else:
                status = f"❌ Hiện tại HẾT HÀNG ở {store}"

            send_message(
                f"👀 Đã thêm theo dõi:\n📱 {PRODUCTS[product_name][0]}\n🏬 {store}\n\n{status}\n\nBot sẽ nhắc bạn khi sản phẩm có hàng tại {store}",
                chat_id)
            show_main_menu(chat_id)

        elif data.startswith("delete_watch|"):
            _, key = data.split("|", 1)
            if key in watchlist:
                del watchlist[key]
                save_watchlist()
                send_message(f"🗑️ Đã xóa khỏi danh sách: {key}", chat_id)
            show_watchlist(chat_id)


# --- TỰ ĐỘNG KIỂM TRA ---
def auto_check():
    last_available = {}
    print("🔁 Bắt đầu vòng kiểm tra tự động...")

    while True:
        for key, part in list(watchlist.items()):
            product, location = key.split(" | ")
            time.sleep(1)

            available_stores = check_stock(part, location)
            is_available = bool(available_stores)
            prev_state = last_available.get(key, False)

            if is_available and not prev_state:
                print(f"📦 {product} tại {location}: CÓ HÀNG")
                for s in available_stores:
                    for user in authorized_users:
                        send_message(
                            f"🚨 Có hàng!\n"
                            f"📱 {product}\n"
                            f"🏬 {s['name']}\n"
                            f"📍 {s['address']}\n"
                            f"📞 {s['phone']}\n"
                            f"📧 {s['email']}", user)

            elif not is_available and prev_state:
                print(f"❌ {product} tại {location}: Hết hàng trở lại")
                for user in authorized_users:
                    send_message(f"❌ {product} tại {location} đã hết hàng.",
                                 user)

            last_available[key] = is_available

        time.sleep(120)


# --- MAIN ---
if __name__ == "__main__":
    load_watchlist()
    load_auth()
    print("🤖 Bot đang chạy... Watchlist:", watchlist)

    threading.Thread(target=auto_check, daemon=True).start()

    last_update_id = None
    while True:
        try:
            res = requests.get(f"{BASE_URL}/getUpdates",
                               params={
                                   "offset": last_update_id,
                                   "timeout": 30
                               },
                               timeout=35)
            data = res.json()
            for update in data.get("result", []):
                last_update_id = update["update_id"] + 1
                handle_update(update)
        except Exception as e:
            print("⚠️ Polling error:", e)
            time.sleep(5)
