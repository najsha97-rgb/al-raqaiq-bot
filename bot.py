# -*- coding: utf-8 -*-
"""
BOT TELEGRAM AL-RAQĀ'IQ (الرقائق)
Pelembut-pelembut Hati Harakah Islamiyah
Karya: Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)
"""

import os
import sys
import json
import time
import re
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot Al-Raqaiq Telegram (@RaqaiqKu_bot) beroperasi 24/7.".encode("utf-8"))

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get("PORT", 0))
    if port:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Health-check HTTP Server aktif pada port {port} (Sedia untuk Render).")

# Pastikan stream selamat jika dijalankan tanpa konsol (background / pythonw)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Pastikan konsol Windows menyokong emoji dan teks Arab (UTF-8)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Konfigurasi Token
# Pengguna boleh letak token dalam environment variable atau terus dalam fail ini/config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DATA_PATH = os.path.join(os.path.dirname(__file__), "alraqaiq_data.json")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_AWAIQ", "")

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if not BOT_TOKEN and cfg.get("bot_token"):
                BOT_TOKEN = cfg.get("bot_token")
    except Exception as e:
        print(f"Ralat membaca config.json: {e}")

# Muat Pangkalan Data Al-Raqaiq
if not os.path.exists(DATA_PATH):
    print(f"Ralat: Fail pangkalan data {DATA_PATH} tidak dijumpai!")
    sys.exit(1)

with open(DATA_PATH, "r", encoding="utf-8") as f:
    ALRAQAIQ_DATA = json.load(f)

CHAPTERS = ALRAQAIQ_DATA.get("chapters", [])
print(f"Berjaya memuatkan {len(CHAPTERS)} bab Al-Raqaiq.")

# Sesi HTTP
session = requests.Session()
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Penyimpanan Sesi Pengguna Sementara
USER_STATE = {} # { chat_id: { 'layer': 'layer1' } }
USER_SEARCH = {} # { chat_id: search_query }

def get_user_layer(chat_id):
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {'layer': 'layer1'}
    return USER_STATE[chat_id].get('layer', 'layer1')

def set_user_layer(chat_id, layer):
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {}
    USER_STATE[chat_id]['layer'] = layer

def send_api(method, payload):
    url = f"{API_BASE}/{method}"
    try:
        res = session.post(url, json=payload, timeout=30)
        data = res.json()
        if not data.get("ok"):
            print(f"Ralat Telegram ({method}): {data.get('description')}")
        return data
    except Exception as e:
        print(f"Ralat API Telegram ({method}): {e}")
        return None

def format_smart_italic(match):
    inner = match.group(1)
    # Kira huruf Arab
    ar_count = len(re.findall(r'[\u0600-\u06FF]', inner))
    latin_count = len(re.findall(r'[a-zA-Z]', inner))
    # Jika teks adalah bahasa Arab atau dominan Arab, JANGAN italic-kan (kekal tegak)
    if ar_count > 0 and ar_count >= latin_count:
        return inner
    return f"<i>{inner}</i>"

def md_to_telegram_html(text):
    if not text:
        return ""
    # 1. Escape aksara khas HTML
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 2. Format Bold **teks** -> <b>teks</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    # 3. Format Italic *teks* atau _teks_ -> <i>teks</i> (Hanya teks Rumi/terjemahan, teks Arab tidak di-italic-kan)
    text = re.sub(r'(?<!\*)\*([^\*\n]+?)\*(?!\*)', format_smart_italic, text)
    text = re.sub(r'(?<!_)_([^_\n]+?)_(?!_)', format_smart_italic, text)
    # 4. Senarai bullet (* atau - di awal baris) -> • 
    text = re.sub(r'^[ \t]*[\*\-][ \t]+', '• ', text, flags=re.MULTILINE)
    return text

def escape_html_entities(text):
    if not text:
        return ""
    # Gantikan sebarang & yang bukan sebahagian daripada entiti sah
    return re.sub(r"&(?!(?:amp|lt|gt|quot|apos);)", "&amp;", text)

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    if parse_mode == "HTML":
        text = escape_html_entities(text)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = send_api("sendMessage", payload)
    # Fallback ke plain text jika ada isu entiti HTML: WAJIB buang semua tanda < > agar bersih 100%
    if (not res or not res.get("ok")) and parse_mode:
        clean_plain = re.sub(r"<[^>]+>", "", text)
        payload["text"] = clean_plain
        payload.pop("parse_mode", None)
        res = send_api("sendMessage", payload)
    return res

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    if parse_mode == "HTML":
        text = escape_html_entities(text)
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = send_api("editMessageText", payload)
    # Fallback ke plain text jika ada isu entiti HTML: WAJIB buang semua tanda < > agar bersih 100%
    if res and not res.get("ok"):
        desc = res.get("description", "")
        if "message is not modified" in desc:
            return res
        if parse_mode and ("can't parse entities" in desc or "unsupported parse_mode" in desc or not res.get("ok")):
            clean_plain = re.sub(r"<[^>]+>", "", text)
            payload["text"] = clean_plain
            payload.pop("parse_mode", None)
            res = send_api("editMessageText", payload)
    return res

def answer_callback_query(callback_query_id, text=""):
    payload = {
        "callback_query_id": callback_query_id,
        "text": text
    }
    return send_api("answerCallbackQuery", payload)

# ================= MENU GENERATORS =================

def get_main_menu_keyboard():
    return {
        "inline_keyboard": [
                        [
                {"text": "🏃‍♂️ Prolog Puitis (Lima Gerak Sang Pelari)", "callback_data": "menu_prolog"}
            ],
[
                {"text": "📘 Baca Ikut Bab (20 Bab)", "callback_data": "menu_chapters"},
                {"text": "🔍 Carian Topik", "callback_data": "menu_search_info"}
            ],
            [
                {"text": "💎 227 Mutiara Kata (Hadis Nabi SAW + Tokoh & Pejuang)", "callback_data": "hikmah_random"}
            ],
            [
                {"text": "🔄 Pilihan Mod Bacaan", "callback_data": "menu_mode"}
            ],
            [
                {"text": "🧭 Buka Web PWA Al-Raqaiq 🌐", "url": "https://najsha97-rgb.github.io/al-awaiq-pwa/"}
            ],
            [
                {"text": "ℹ️ Info Kitab & Syeikh", "callback_data": "menu_about"}
            ]
        ]
    }

def get_chapters_keyboard():
    buttons = []
    # Mukadimah
    buttons.append([{"text": "📌 Mukadimah: Dasar Perancangan", "callback_data": "ch_0"}])
    
    # Bab 1 hingga 20 (2 butang per baris)
    row = []
    for idx in range(1, len(CHAPTERS)):
        ch = CHAPTERS[idx]
        if ch.get("number") == "Penutup" or "Khatimah" in ch.get("title", ""):
            continue
        title_raw = ch['title'].split(':')[1].strip() if ':' in ch['title'] else ch['title']
        title_short = f"💎 Bab {idx}: {title_raw}"
        if len(title_short) > 25:
            title_short = title_short[:23] + ".."
        row.append({"text": title_short, "callback_data": f"ch_{idx}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    # Penutup / Khatimah
    penutup_idx = len(CHAPTERS) - 1
    if penutup_idx > 0 and (CHAPTERS[penutup_idx].get("number") == "Penutup" or "Khatimah" in CHAPTERS[penutup_idx].get("title", "")):
        buttons.append([{"text": "🌟 Penutup: Khatimah (Kewaspadaan & Optimisme)", "callback_data": f"ch_{penutup_idx}"}])
        
    buttons.append([{"text": "⬅️ Kembali ke Menu Utama", "callback_data": "menu_main"}])
    return {"inline_keyboard": buttons}

def get_subtopics_keyboard(ch_idx):
    ch = CHAPTERS[ch_idx]
    buttons = []
    
    for s_idx, sub in enumerate(ch["subtopics"]):
        title_btn = f"🧭 {s_idx+1}. {sub.get('menu_title') or sub['title']}"
        if len(title_btn) > 34:
            title_btn = title_btn[:32] + ".."
        buttons.append([{"text": title_btn, "callback_data": f"sub_{ch_idx}_{s_idx}_0"}])
        
    buttons.append([
        {"text": "⬅️ Senarai Bab", "callback_data": "menu_chapters"},
        {"text": "🏠 Utama", "callback_data": "menu_main"}
    ])
    return {"inline_keyboard": buttons}

def clean_paragraph_for_telegram(p):
    if not p:
        return ""

    # 1. Custom block: prolog-center-card (Bait lima gerak)
    if "prolog-center-card" in p:
        bis_m = re.search(r"prolog-center-bismillah[^>]*>(.*?)</div>", p, re.DOTALL)
        bis = f"<b>{bis_m.group(1).strip()}</b>\n\n" if bis_m else ""
        
        ar_m = re.search(r"prolog-center-arabic[^>]*>(.*?)</div>", p, re.DOTALL)
        ar = ""
        if ar_m:
            ar_clean = ar_m.group(1).replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n").strip()
            ar = f"<blockquote>{ar_clean}</blockquote>\n\n"
            
        my_m = re.search(r"prolog-center-malay[^>]*>(.*?)</div>", p, re.DOTALL)
        my = ""
        if my_m:
            my_clean = my_m.group(1).replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n").strip()
            my = f"<blockquote><i>{my_clean}</i></blockquote>\n\n"
            
        note = "💡 Keterangan rahsia tersirat lima gerak dihuraikan secara terperinci dalam <b>Keterangan Prolog (Bab Penutup)</b>."
        return f"{bis}{ar}{my}{note}"

    # 2. Custom block: prolog-nav-note in Keterangan Prolog
    if "prolog-nav-note" in p:
        return "🔙 <i>Bait-bait epigraf asal boleh dihayati semula di <b>Prolog Puitis (Prakata)</b>.</i>"

    # 3. Handle footnote reference spans: <span class="fn-ref" ...>[X]</span>
    p = re.sub(r'<span[^>]*class=["\']fn-ref["\'][^>]*>(.*?)</span>', r"<b>\1</b>", p, flags=re.DOTALL)
    # 4. Handle other spans: e.g. <span class="num-card-badge">1</span>
    p = re.sub(r'<span[^>]*class=["\']num-card-badge["\'][^>]*>(.*?)</span>', r"<b>[\1]</b> ", p, flags=re.DOTALL)
    p = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", p, flags=re.DOTALL)
    p = re.sub(r"</span>", "", p)
    # Buang komentar HTML <!-- ... -->
    p = re.sub(r"<!--.*?-->", "", p, flags=re.DOTALL)
    # 5. Remove HTML tags that Telegram does NOT support (div, section, p, etc.)
    p = re.sub(r"<br\s*/?>", "\n", p)
    p = re.sub(r"</?(?:ul|ol|li)[^>]*>", "\n", p)
    p = re.sub(r"</?(?:h[1-6]|table|tr|td|th)[^>]*>", "\n", p)
    p = re.sub(r"</?(?:div|section|span|p|small|strong|em|header|footer|article)[^>]*>", "", p)
    # Strip internal anchor links
    p = re.sub(r'<a\s+[^>]*href=["\']#[^"\']*["\'][^>]*>(.*?)</a>', r"\1", p, flags=re.DOTALL)

    # 6. Markdown formatting
    p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p, flags=re.DOTALL)
    p = re.sub(r"(?<!\*)\*([^\*]+?)\*(?!\*)", format_smart_italic, p)
    p = re.sub(r"(?<!_)_([^_]+?)_(?!_)", format_smart_italic, p)
    
    # 7. Blockquote
    p = re.sub(r"^[ \t]*>[ \t]*(.*)$", r"<blockquote>\1</blockquote>", p, flags=re.MULTILINE)

    # Clean multiple newlines
    p = re.sub(r"\n{3,}", "\n\n", p)
    return p.strip()

def format_subtopic_text(ch_idx, s_idx, layer, page=0, search_q=None):
    ch = CHAPTERS[ch_idx]
    sub = ch["subtopics"][s_idx]
    
    mode_label = "🔵 <b>Versi Lengkap (Terjemahan Penuh)</b>" if layer == "layer1" else "⚡ <b>Ringkasan Eksklusif (Layer 2)</b>"
    
    highlight_note = (f'🔍 <i>Kata Kunci: "<b>{search_q}</b>" (diserlahkan dengan garis tebal)</i>\n') if search_q else ""
    
    header = (
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
        f"🧭 <b>AL-AWAIQ (المَسَار)</b>\n"
        f"📚 <b>{ch['number']}: {ch['title']}</b>\n"
        f"📑 <b>Tajuk: {sub['title']}</b>\n"
        f"🏷 {mode_label}\n"
        f"{highlight_note}"
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
    )
    
    if layer == "layer1":
        paras = sub.get("paragraphs", [])
        if not paras:
            return header + "<i>Tiada teks dalam bahagian ini.</i>", 1
            
        # Paginasi perenggan (setiap muka surat memaparkan sekitar 3-4 perenggan / ~1800 aksara)
        pages_content = []
        cur_page = []
        cur_len = 0
        
        for p in paras:
            cleaned_p = clean_paragraph_for_telegram(p)
            cur_page.append(cleaned_p)
            cur_len += len(cleaned_p)
            if cur_len > 1400:
                pages_content.append("\n\n".join(cur_page))
                cur_page = []
                cur_len = 0
        if cur_page:
            pages_content.append("\n\n".join(cur_page))
            
        total_pages = len(pages_content)
        page = min(page, total_pages - 1)
        body = pages_content[page] if pages_content else "<i>Tiada kandungan.</i>"
        if search_q and search_q.lower() in body.lower():
            pattern = re.compile(re.escape(search_q), re.IGNORECASE)
            body = pattern.sub(lambda m: f"<b><u>{m.group(0)}</u></b>", body)
        
        footer = f"\n\n🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n📄 <i>Halaman {page+1} daripada {total_pages}</i>"
        return header + body + footer, total_pages
    else:
        # Layer 2: Ringkasan Eksklusif
        summary_raw = sub.get("summary", "Ringkasan sedang dimantapkan...")
        summary_clean = md_to_telegram_html(summary_raw)
        if search_q and search_q.lower() in summary_clean.lower():
            pattern = re.compile(re.escape(search_q), re.IGNORECASE)
            summary_clean = pattern.sub(lambda m: f"<b><u>{m.group(0)}</u></b>", summary_clean)
        return header + f"<blockquote>{summary_clean}</blockquote>", 1

def get_subtopic_reading_keyboard(ch_idx, s_idx, layer, page, total_pages, search_q=None):
    ch = CHAPTERS[ch_idx]
    buttons = []
    
    # Butang Lompatan Khas Prolog Puitis (ch 0, s 0) <-> Keterangan Prolog (ch 21, s 8)
    if ch_idx == 0 and s_idx == 0:
        buttons.append([{"text": "🔍 Buka Keterangan Prolog (Rahsia Tersirat) 📖", "callback_data": "sub_21_8_0"}])
    elif ch_idx == 21 and s_idx == 8:
        buttons.append([{"text": "🏃‍♂️ Kembali ke Prolog Puitis (Epigraf) 🔙", "callback_data": "sub_0_0_0"}])
    
    # 1. Butang Paginasi (jika teks panjang)
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append({"text": "◀️ Sebelum", "callback_data": f"sub_{ch_idx}_{s_idx}_{page-1}"})
        nav_row.append({"text": f"{page+1}/{total_pages}", "callback_data": "noop"})
        if page < total_pages - 1:
            nav_row.append({"text": "Seterusnya ▶️", "callback_data": f"sub_{ch_idx}_{s_idx}_{page+1}"})
        buttons.append(nav_row)
        
    # 2. Butang Tukar Layer (Lengkap vs Ringkasan)
    toggle_text = "⚡ Tukar ke Ringkasan" if layer == "layer1" else "📖 Tukar ke Versi Lengkap"
    buttons.append([{"text": toggle_text, "callback_data": f"toglayer_{ch_idx}_{s_idx}"}])
    
    # 3. Butang Subtajuk Sebelumnya / Seterusnya
    sub_nav = []
    if s_idx > 0:
        sub_nav.append({"text": "⏮ Subtajuk Lepas", "callback_data": f"sub_{ch_idx}_{s_idx-1}_0"})
    if s_idx < len(ch["subtopics"]) - 1:
        sub_nav.append({"text": "Subtajuk Depan ⏭", "callback_data": f"sub_{ch_idx}_{s_idx+1}_0"})
    if sub_nav:
        buttons.append(sub_nav)
        
    # 4. Navigasi Pulang
    buttons.append([
        {"text": "📋 Senarai Subtajuk", "callback_data": f"ch_{ch_idx}"},
        {"text": "🏠 Menu Utama", "callback_data": "menu_main"}
    ])
    return {"inline_keyboard": buttons}

# ================= MUTIARA HIKMAH =================
QUOTES_PATH = os.path.join(os.path.dirname(__file__), "alraqaiq_quotes.json")
HIKMAH_DATA = []
if os.path.exists(QUOTES_PATH):
    try:
        with open(QUOTES_PATH, "r", encoding="utf-8") as f:
            HIKMAH_DATA = json.load(f)
        print(f"Berjaya memuatkan {len(HIKMAH_DATA)} mutiara hikmah Al-Raqaiq dari JSON.")
    except Exception as e:
        print(f"Ralat memuatkan alraqaiq_quotes.json: {e}")

def format_hikmah_message(item):
    quote_text = md_to_telegram_html(item.get("quote", ""))
    total_q = len(HIKMAH_DATA) if HIKMAH_DATA else 227
    q_id = item.get("id", "")
    badge = f" #{q_id}" if q_id else ""
    return (
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
        f"💎 <b>MUTIARA HIKMAH DAKWAH AL-AWAIQ</b> 💎\n"
        f"✨ <i>Koleksi Mutiara Emas ({badge} / {total_q})</i>\n"
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
        f"👤 <b>{item.get('speaker', 'Tokoh Dakwah')}</b>\n\n"
        f"<blockquote>“{quote_text}”</blockquote>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📚 <b>Sumber:</b> {item.get('chapterNumber', '')} - {item.get('chapterTitle', '')}\n"
        f"📑 <b>Topik:</b> {item.get('subtopicTitle', '')}\n"
        f"🧭 <i>Kitab Al-Raqaiq — Syeikh Muhammad Ahmad Ar-Rasyid</i>\n"
        f"🌐 https://najsha97-rgb.github.io/al-awaiq-pwa/"
    )

def get_hikmah_keyboard(item):
    ch_idx = item.get('chapterIndex')
    s_idx = item.get('subtopicIndex')
    if ch_idx is None or s_idx is None:
        sub_id = item.get('subtopicId')
        for c_i, ch in enumerate(CHAPTERS):
            for s_i, sub in enumerate(ch.get('subtopics', [])):
                if sub.get('id') == sub_id:
                    ch_idx, s_idx = c_i, s_i
                    break
            if ch_idx is not None and s_idx is not None:
                break
    ch_idx = ch_idx if ch_idx is not None else 0
    s_idx = s_idx if s_idx is not None else 0
    return {
        "inline_keyboard": [
            [{"text": f"📖 Baca: {item.get('subtopicTitle', 'Topik Ini')[:28]}", "callback_data": f"sub_{ch_idx}_{s_idx}_0"}],
            [{"text": "🎲 Mutiara Lain (Rawak)", "callback_data": "hikmah_random"}],
            [{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]
        ]
    }

# ================= HANDLERS =================

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    
    if text.startswith("/start") or text.startswith("/menu"):
        welcome_txt = (
            "🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "🧭 <b>AL-AWAIQ (المَسَار)</b> 🧭\n"
            "<i>Pelembut-pelembut Hati Harakah Islamiyah</i>\n"
            "🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "<blockquote>📖 <b>Pengarang:</b> As-Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)\n"
            "🌟 <i>Siri Kelima Siri Fiqh Haraki — Menempa perancangan strategik, disiplin amal, dan hikmah polisi harakah.</i></blockquote>\n\n"
            "📚 <b>Struktur Dwi-Lapisan (Dual-Layer):</b>\n"
            "• 🔵 <code>Layer 1</code>: Versi Penuh Terjemahan Lengkap (20 Bab + 210 Topik Lengkap)\n"
            "• ⚡ <code>Layer 2</code>: Ringkasan Eksklusif Berstruktur & Analisis Haraki\n"
            "• 💎 <code>Mutiara Hikmah</code>: Himpunan 227 Nukilan Emas Tokoh & Pemimpin Dakwah\n\n"
            "🌐 <b>Web PWA (Tema Nilam & Amber):</b>\n"
            "https://najsha97-rgb.github.io/al-awaiq-pwa/\n\n"
            "<i>Sila pilih menu di bawah untuk memulakan bacaan:</i>"
        )
        send_message(chat_id, welcome_txt, get_main_menu_keyboard())
        return

    if text.startswith("/cari"):
        query = text.replace("/cari", "").strip()
        if not query:
            send_message(chat_id, "ℹ️ Sila taip kata kunci carian selepas arahan.\nContoh: <code>/cari syaitan</code> atau <code>/cari tanzim</code>")
            return
        handle_search(chat_id, query)
        return

    if text.startswith("/hikmah"):
        if HIKMAH_DATA:
            item = random.choice(HIKMAH_DATA)
            send_message(chat_id, format_hikmah_message(item), get_hikmah_keyboard(item))
        else:
            send_message(chat_id, "💎 <b>MUTIARA HIKMAH DAKWAH</b>\n\nKoleksi mutiara hikmah sedang dikemas kini.")
        return

    # Mesej biasa -> Lakukan carian pantas
    handle_search(chat_id, text)

def normalize_kw(text):
    if not text:
        return ""
    return re.sub(r"[\u2018\u2019\u02bb\u02bc`]", "'", str(text).lower())

def handle_search(chat_id, query):
    USER_SEARCH[chat_id] = query
    query_lower = query.lower()
    norm_query = normalize_kw(query)
    matches = []
    
    for ch_idx, ch in enumerate(CHAPTERS):
        for s_idx, sub in enumerate(ch["subtopics"]):
            found_p = False
            # 1. Keutamaan Utama: Versi Penuh (Layer 1)
            for p in sub.get("paragraphs", []):
                if norm_query in normalize_kw(p):
                    matches.append((ch_idx, s_idx, "layer1", f"📖 [Versi Penuh] {ch['number']}: {sub['title']}"))
                    found_p = True
                    break
            if found_p:
                if len(matches) >= 10: break
                continue

            if norm_query in normalize_kw(sub["title"]):
                matches.append((ch_idx, s_idx, "layer1", f"📖 [Versi Penuh] {ch['number']}: {sub['title']}"))
                if len(matches) >= 10: break
                continue

            # 2. Keutamaan Kedua: Ringkasan Eksklusif (Layer 2)
            if norm_query in normalize_kw(sub.get("summary", "")):
                matches.append((ch_idx, s_idx, "layer2", f"📑 [Ringkasan] {ch['number']}: {sub['title']}"))
                if len(matches) >= 10: break

        if len(matches) >= 10:
            break
            
    if not matches:
        send_message(chat_id, f"🔍 Maaf, tiada perbincangan dijumpai bagi kata kunci: <b>\"{query}\"</b>.\nCuba kata kunci lain seperti <i>tarbiah, politik, tanzim, banna, iktibar</i>.")
        return

    keyboard = []
    for item in matches:
        if len(item) == 4:
            ch_idx, s_idx, target_layer, label = item
            keyboard.append([{"text": label[:42], "callback_data": f"subsearch_{ch_idx}_{s_idx}_{target_layer}_0"}])
        else:
            ch_idx, s_idx, label = item[:3]
            keyboard.append([{"text": label[:42], "callback_data": f"sub_{ch_idx}_{s_idx}_0"}])
    keyboard.append([{"text": "🏠 Menu Utama", "callback_data": "menu_main"}])
    
    send_message(
        chat_id, 
        f"🔍 <b>Hasil Carian untuk: \"{query}\"</b>\nDijumpai {len(matches)} topik berkaitan. Sila pilih:",
        {"inline_keyboard": keyboard}
    )

def handle_callback(cb):
    cb_id = cb["id"]
    data = cb.get("data", "")
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]
    
    answer_callback_query(cb_id)
    
    if data == "reopen_search":
        search_q = USER_SEARCH.get(chat_id)
        if search_q:
            handle_search(chat_id, search_q)
        else:
            send_message(chat_id, "Sila buat carian baru dengan /cari [kata kunci].")
        return

    if data == "menu_main":
        welcome_txt = (
            "🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "🧭 <b>AL-AWAIQ (المَسَار)</b> 🧭\n"
            "<i>Pelembut-pelembut Hati Harakah Islamiyah</i>\n"
            "🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "<blockquote>📖 <b>Pengarang:</b> As-Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)\n"
            "🌟 <i>Siri Kelima Siri Fiqh Haraki — Menempa perancangan strategik, disiplin amal, dan hikmah polisi harakah.</i></blockquote>\n\n"
            "📚 <b>Struktur Dwi-Lapisan (Dual-Layer):</b>\n"
            "• 🔵 <code>Layer 1</code>: Versi Penuh Terjemahan Lengkap (20 Bab + 210 Topik Lengkap)\n"
            "• ⚡ <code>Layer 2</code>: Ringkasan Eksklusif Berstruktur & Analisis Haraki\n"
            "• 💎 <code>Mutiara Hikmah</code>: Himpunan 227 Nukilan Emas Tokoh & Pemimpin Dakwah\n\n"
            "🌐 <b>Web PWA (Tema Nilam & Amber):</b>\n"
            "https://najsha97-rgb.github.io/al-awaiq-pwa/\n\n"
            "<i>Sila pilih seksyen di bawah untuk memulakan bacaan:</i>"
        )
        edit_message(chat_id, msg_id, welcome_txt, get_main_menu_keyboard())
        return

    if data == "menu_prolog":
        # Akses pantas ke Prolog Puitis: Lima Gerak Sang Pelari (Bab 0, Subtopik 0)
        content_txt, total_pages = format_subtopic_text(0, 0, "layer1", 0)
        kb = get_subtopic_reading_keyboard(0, 0, "layer1", 0, total_pages)
        edit_message(chat_id, msg_id, content_txt, kb)
        return

    if data == "menu_chapters":
        txt = "📘 <b>PILIH BAB KANDUNGAN AL-AWAIQ:</b>\n\nKitab ini mengandungi Mukadimah, 20 Bab utama dan Khatimah (Penutup).\nPilih bab untuk melihat senarai topik:"
        edit_message(chat_id, msg_id, txt, get_chapters_keyboard())
        return

    if data.startswith("ch_"):
        ch_idx = int(data.split("_")[1])
        ch = CHAPTERS[ch_idx]
        txt = (
            f"🏛 <b>{ch['number']}: {ch['title']}</b>\n"
            f"🏷 <i>{ch['title_ar']}</i>\n\n"
            f"Terdapat <b>{len(ch['subtopics'])} sub-tajuk</b> dalam bab ini. Sila pilih tajuk yang ingin dibaca:"
        )
        edit_message(chat_id, msg_id, txt, get_subtopics_keyboard(ch_idx))
        return

    if data.startswith("subsearch_"):
        parts = data.split("_")
        ch_idx = int(parts[1])
        s_idx = int(parts[2])
        target_layer = parts[3]
        page = int(parts[4]) if len(parts) > 4 else 0
        
        set_user_layer(chat_id, target_layer)
        search_q = USER_SEARCH.get(chat_id)
        
        content_txt, total_pages = format_subtopic_text(ch_idx, s_idx, target_layer, page, search_q)
        kb = get_subtopic_reading_keyboard(ch_idx, s_idx, target_layer, page, total_pages, search_q=search_q)
        edit_message(chat_id, msg_id, content_txt, kb)
        return

    if data.startswith("sub_"):
        parts = data.split("_")
        ch_idx = int(parts[1])
        s_idx = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        layer = get_user_layer(chat_id)
        search_q = USER_SEARCH.get(chat_id)
        
        content_txt, total_pages = format_subtopic_text(ch_idx, s_idx, layer, page, search_q)
        kb = get_subtopic_reading_keyboard(ch_idx, s_idx, layer, page, total_pages, search_q=search_q)
        edit_message(chat_id, msg_id, content_txt, kb)
        return

    if data.startswith("toglayer_"):
        parts = data.split("_")
        ch_idx = int(parts[1])
        s_idx = int(parts[2])
        cur_layer = get_user_layer(chat_id)
        new_layer = "layer2" if cur_layer == "layer1" else "layer1"
        set_user_layer(chat_id, new_layer)
        
        content_txt, total_pages = format_subtopic_text(ch_idx, s_idx, new_layer, 0)
        kb = get_subtopic_reading_keyboard(ch_idx, s_idx, new_layer, 0, total_pages)
        edit_message(chat_id, msg_id, content_txt, kb)
        return

    if data == "hikmah_random":
        if HIKMAH_DATA:
            item = random.choice(HIKMAH_DATA)
            edit_message(chat_id, msg_id, format_hikmah_message(item), get_hikmah_keyboard(item))
        else:
            edit_message(chat_id, msg_id, "💎 <b>MUTIARA HIKMAH DAKWAH</b>\n\nKoleksi mutiara hikmah sedang dikemas kini.", {"inline_keyboard": [[{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]]})
        return

    if data == "menu_mode":
        cur = get_user_layer(chat_id)
        cur_name = "Versi Penuh (Terjemahan Lengkap)" if cur == "layer1" else "Ringkasan Eksklusif"
        txt = (
            f"🔄 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            f"⚙️ <b>TETAPAN MOD BACAAN AL-AWAIQ</b>\n"
            f"🔄 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            f"Mod semasa anda: <b>{cur_name}</b>\n\n"
            f"• 🔵 <b>Versi Penuh (Layer 1):</b> Memaparkan teks terjemahan penuh kitab tanpa tapisan.\n"
            f"• ⚡ <b>Ringkasan Eksklusif (Layer 2):</b> Memaparkan intisari padat, poin-poin utama, serta nukilan tokoh penting bagi semakan pantas."
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🔵 Tetapkan: Versi Penuh", "callback_data": "setmode_layer1"}],
                [{"text": "⚡ Tetapkan: Ringkasan Eksklusif", "callback_data": "setmode_layer2"}],
                [{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]
            ]
        }
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data.startswith("setmode_"):
        new_mode = data.split("_")[1]
        set_user_layer(chat_id, new_mode)
        mode_str = "Versi Penuh" if new_mode == "layer1" else "Ringkasan Eksklusif"
        answer_callback_query(cb_id, f"Mod berjaya ditukar kepada: {mode_str}")
        # Kembali ke menu utama
        handle_callback({"id": cb_id, "data": "menu_main", "message": cb["message"]})
        return

    if data == "menu_search_info":
        txt = (
            "🔍 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "🧭 <b>PANDUAN CARIAN PANTAS AL-AWAIQ</b>\n"
            "🔍 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "Anda boleh mencari sebarang topik, nama tokoh, atau istilah fiqh dakwah dengan menaip terus:\n\n"
            "👉 <code>/cari [kata kunci]</code>\n\n"
            "<b>Contoh:</b>\n"
            "• <code>/cari syaitan</code> (6 medan perang syaitan)\n"
            "• <code>/cari tanzim</code> (Fiqh organisasi & rahsia)\n"
            "• <code>/cari wanita</code> (Peranan dakwah muslimat)\n"
            "• <code>/cari banna</code> (Nukilan Imam Hasan al-Banna)\n"
            "• <code>/cari qutb</code> (Kritikan Sayyid Qutb terhadap tanzim khas)\n"
            "• <code>/cari tajmi'</code> (10 Seni pengumpulan mad'u)"
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]]}
        edit_message(chat_id, msg_id, txt, kb)
        return

    if data == "menu_about":
        txt = (
            "ℹ️ ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "🧭 <b>TENTANG KITAB AL-AWAIQ (المسار)</b> 🧭\n"
            "ℹ️ ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "<blockquote><b>Pengarang:</b> As-Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)\n"
            "<b>Genre:</b> Strategi, Polisi & Fiqh Perancangan Harakah Islamiyah\n"
            "<b>Cakupan:</b> Polisi Luaran, Polisi Dalaman & Polisi Tarbawi Harakah Islamiyah</blockquote>\n\n"
            "Al-Raqaiq adalah buku siri kelima daripada siri-siri fiqh dakwah dan harakah Islamiyah dimulai dengan <i>al-Muntalaq</i> (mengenali tabiatnya), <i>al-‘Awa’iq</i> (halangan dakwah), <i>al-Raqa’iq</i> (kelembutan jiwa), dan <i>al-Bawariq</i> (lintasan panduan).\n\n"
            "🌐 <b>Aplikasi Web PWA (Tema Nilam & Amber):</b>\n"
            "https://najsha97-rgb.github.io/al-awaiq-pwa/"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🔵 Layari Web PWA Al-Raqaiq 🌐", "url": "https://najsha97-rgb.github.io/al-awaiq-pwa/"}],
                [{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]
            ]
        }
        edit_message(chat_id, msg_id, txt, kb)
        return

# ================= POLLING ENGINE =================

def run_bot():
    if not BOT_TOKEN or BOT_TOKEN == "ISI_TOKEN_BOT_ANDA_DI_SINI":
        print("\n" + "="*60)
        print("PERHATIAN: Token Bot Telegram Belum Ditetapkan!")
        print("Sila masukkan token bot anda ke dalam fail config.json atau set environment variable TELEGRAM_BOT_TOKEN_AWAIQ.")
        print("="*60 + "\n")
        return

    print("="*60)
    print("Bot Telegram Al-Raqaiq sedang dijalankan (Polling Mode)...")
    print("Tekan Ctrl + C untuk menghentikan bot.")
    print("="*60)

    # Aktifkan server HTTP jika berjalan di Render / cloud (PORT dikesan)
    start_health_server()
    
    # Uji sambungan ke Telegram dengan cubaan semula automatik (Auto-retry)
    bot_info = None
    attempt = 1
    while not bot_info:
        print(f"Menyambung ke Telegram (Percubaan #{attempt})...")
        me = send_api("getMe", {})
        if me and me.get("ok"):
            bot_info = me["result"]
            print(f"Berjaya log masuk sebagai @{bot_info.get('username')} ({bot_info.get('first_name')})")
            break
        print("Sambungan ke api.telegram.org mengalami timeout / lengah rangkaian (VPN/ISP).")
        print("Mencuba semula dalam 5 saat... (Jika menggunakan VPN, sila cuba jeda atau tukar lokasi VPN)")
        attempt += 1
        time.sleep(5)

    last_update_id = 0
    while True:
        try:
            url = f"{API_BASE}/getUpdates?offset={last_update_id + 1}&timeout=20"
            resp = session.get(url, timeout=30)
            data = resp.json()
            
            if data.get("ok"):
                for upd in data.get("result", []):
                    last_update_id = upd["update_id"]
                    if "message" in upd:
                        handle_message(upd["message"])
                    elif "callback_query" in upd:
                        handle_callback(upd["callback_query"])
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nBot dihentikan oleh pengguna.")
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            # Lengahan rangkaian sementara - tunggu sekejap dan sambung semula
            time.sleep(3)
        except Exception as e:
            print(f"Ralat polling: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_bot()
