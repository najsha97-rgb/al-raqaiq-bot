# -*- coding: utf-8 -*-
"""
BOT TELEGRAM AL-RAQĀ'IQ (الرقائق)
Pelembut-pelembut Hati Harakah Islamiyah
Karya: As-Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)
Siri Ketiga Fiqh Haraki (Siri Ihya' al-Fiqh al-Da'wi)
Versi: Refined 2.0 (In-Place Navigation, 117 Mutiara Hikmah Sequential, Smart Highlight Search)
"""

import os
import sys
import json
import time
import re
import html
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

# Konfigurasi Token & Data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DATA_PATH = os.path.join(BASE_DIR, "alraqaiq_data.json")
QUOTES_PATH = os.path.join(BASE_DIR, "alraqaiq_quotes.json")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_RAQAIQ", "")

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if not BOT_TOKEN and cfg.get("bot_token"):
                BOT_TOKEN = cfg.get("bot_token").strip()
    except Exception as e:
        print(f"Ralat membaca config.json: {e}")

# Muat Pangkalan Data Al-Raqaiq
if not os.path.exists(DATA_PATH):
    print(f"Ralat: Fail pangkalan data {DATA_PATH} tidak dijumpai!")
    sys.exit(1)

with open(DATA_PATH, "r", encoding="utf-8") as f:
    ALRAQAIQ_DATA = json.load(f)

CHAPTERS = ALRAQAIQ_DATA.get("chapters", [])
print(f"Berjaya memuatkan {len(CHAPTERS)} bahagian Al-Raqaiq.")

# Muat Mutiara Hikmah
HIKMAH_DATA = []
if os.path.exists(QUOTES_PATH):
    try:
        with open(QUOTES_PATH, "r", encoding="utf-8") as f:
            HIKMAH_DATA = json.load(f)
        print(f"Berjaya memuatkan {len(HIKMAH_DATA)} mutiara hikmah Al-Raqaiq dari JSON.")
    except Exception as e:
        print(f"Ralat memuatkan alraqaiq_quotes.json: {e}")

# Sesi HTTP dengan pooling
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=2)
session.mount("https://", adapter)
session.mount("http://", adapter)

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Penyimpanan Sesi Pengguna Sementara
USER_STATE = {}   # { chat_id: { 'layer': 'layer1' } }
USER_SEARCH = {}  # { chat_id: search_query }

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
            desc = data.get("description", "")
            if "message is not modified" not in desc.lower():
                print(f"Ralat Telegram ({method}): {desc}")
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
    # 0. Buang sebarang tag HTML mentah yang tidak disokong (seperti <div>, </div>, <center>, <span> dsb.)
    text = re.sub(r'</?(?:div|center|section|article|span|header|footer|p|small)[^>]*>', '', text, flags=re.IGNORECASE)
    # 1. Escape aksara khas HTML
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 2. Format Bold **teks** -> <b>teks</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    # 3. Format Italic *teks* atau _teks_ -> <i>teks</i> (Hanya teks Rumi/terjemahan, teks Arab kekal tegak)
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

def strip_tags(text):
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    return clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&apos;", "'")

def send_document(chat_id, file_path, caption="", reply_markup=None):
    url = f"{API_BASE}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            res = session.post(url, data=data, files=files, timeout=60)
            return res.json()
    except Exception as e:
        print(f"Ralat sendDocument: {e}")
        return None

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    if parse_mode == "HTML":
        text = escape_html_entities(text)
    
    # Telegram max 4096 aksara
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        res = None
        for idx, c in enumerate(chunks):
            rm = reply_markup if idx == len(chunks) - 1 else None
            res = send_api("sendMessage", {
                "chat_id": chat_id,
                "text": c,
                "parse_mode": parse_mode,
                "reply_markup": rm,
                "disable_web_page_preview": True
            })
            if idx < len(chunks) - 1:
                time.sleep(0.5)
        return res
    else:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        res = send_api("sendMessage", payload)
        # Fallback ke plain text jika ada isu entiti HTML
        if (not res or not res.get("ok")) and parse_mode:
            clean_plain = strip_tags(text)
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
    
    if res and not res.get("ok"):
        desc = res.get("description", "").lower()
        if "message is not modified" in desc:
            return {"ok": True, "result": True}
        if parse_mode and ("can't parse entities" in desc or "unsupported parse_mode" in desc or "entity" in desc):
            clean_plain = strip_tags(text)
            payload["text"] = clean_plain
            payload.pop("parse_mode", None)
            res = send_api("editMessageText", payload)
    return res

def edit_message_or_send(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    """
    Menyunting mesej sedia ada jika boleh (in-place) untuk kekemasan sembang.
    Jika teks melebihi 4000 aksara atau mesej tidak boleh disunting, hantar mesej baharu.
    """
    if message_id and len(text) <= 4000:
        res = edit_message(chat_id, message_id, text, reply_markup, parse_mode)
        if res and res.get("ok"):
            return res
        desc = res.get("description", "").lower() if res else ""
        if "message is not modified" in desc:
            return {"ok": True, "result": True}
    return send_message(chat_id, text, reply_markup, parse_mode)

def answer_callback_query(callback_query_id, text=""):
    payload = {
        "callback_query_id": callback_query_id,
        "text": text
    }
    return send_api("answerCallbackQuery", payload)

# ================= MENU GENERATORS =================

def get_pbi_main_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "👑 1. Tasbih Mengukuhkan Kerajaan (Bab 1)", "callback_data": "pbi_sub_1"}
            ],
            [
                {"text": "🌙 2. Madrasah Malam & Minit Berharga (Bab 2)", "callback_data": "pbi_sub_2"}
            ],
            [
                {"text": "🤝 3. Komuniti Akar Umbi & Fiqh Itsar (Bab 5)", "callback_data": "pbi_sub_3"}
            ],
            [
                {"text": "⛓️ 4. Memecahkan Belenggu Bumi (Bab 10)", "callback_data": "pbi_sub_4"}
            ],
            [
                {"text": "🕊️ 5. Hamba yang Merdeka & Izzah (Bab 11)", "callback_data": "pbi_sub_5"}
            ],
            [
                {"text": "⏳ 6. Etos Kerja: 'Lenyap Masa Terluang' (Bab 12)", "callback_data": "pbi_sub_6"}
            ],
            [
                {"text": "🏛️ Pemetaan 8 Tonggak Kuasa", "callback_data": "pbi_sub_tonggak"},
                {"text": "📚 Harmonisasi 4 Tetralogi", "callback_data": "pbi_sub_tetralogi"}
            ],
            [
                {"text": "📕 Dokumen Am PDF (886 KB)", "callback_data": "pbi_doc_pdf"},
                {"text": "📕 Dokumen Khas PDF (4.3 MB)", "callback_data": "pbi_khas_pdf"}
            ],
            [
                {"text": "📘 Dokumen Khas Word (.docx)", "callback_data": "pbi_khas_docx"}
            ],
            [
                {"text": "⬅️ Kembali ke Menu Utama", "callback_data": "menu_main"}
            ]
        ]
    }

def get_main_menu_keyboard():
    total_q = len(HIKMAH_DATA) if HIKMAH_DATA else 117
    return {
        "inline_keyboard": [
            [
                {"text": "🎨 Epigraf: Kepungan Angan-angan", "callback_data": "ch_0"},
                {"text": "📌 Mukadimah: Jiwa Beriman", "callback_data": "ch_1"}
            ],
            [
                {"text": "📘 Baca Ikut Bab (12 Bab Utama)", "callback_data": "menu_chapters"},
                {"text": "🔍 Carian Kata Kunci", "callback_data": "menu_search_info"}
            ],
            [
                {"text": f"💎 {total_q} Mutiara Hikmah (Hadis & Tokoh)", "callback_data": "hikmah_random"}
            ],
            [
                {"text": "🌍 Ummah Fadhilah & PBI (Sumbangan al-Raqā'iq)", "callback_data": "menu_pbi_raqaiq"}
            ],
            [
                {"text": "🔄 Pilihan Mod Bacaan (Lengkap / Ringkas)", "callback_data": "menu_mode"}
            ],
            [
                {"text": "🧭 Buka Web PWA Al-Raqaiq 🌐", "url": "https://najsha97-rgb.github.io/al-raqaiq/"}
            ],
            [
                {"text": "📕 Dokumen Am PDF (886 KB)", "callback_data": "pbi_doc_pdf"},
                {"text": "📕 Dokumen Khas PDF (4.3 MB)", "callback_data": "pbi_khas_pdf"}
            ],
            [
                {"text": "📘 Dokumen Khas Word (.docx)", "callback_data": "pbi_khas_docx"}
            ],
            [
                {"text": "ℹ️ Info Kitab & Syeikh", "callback_data": "menu_about"}
            ]
        ]
    }

def get_chapters_keyboard():
    buttons = []
    # Baris 1: Epigraf dan Mukadimah
    buttons.append([
        {"text": "🎨 Epigraf: Kepungan Angan-angan", "callback_data": "ch_0"},
        {"text": "📌 Mukadimah: Jiwa Beriman", "callback_data": "ch_1"}
    ])
    
    # Bab 1 hingga 12 (Indeks 2 hingga 13 dalam CHAPTERS)
    bab_list = [
        ("Bab 1: Tasbih Mengukuhkan Kerajaan", 2),
        ("Bab 2: Minit-Minit Berharga", 3),
        ("Bab 3: Permulaan", 4),
        ("Bab 4: Kegembiraan Akhirat", 5),
        ("Bab 5: Persaudaraan Syiar Kita", 6),
        ("Bab 6: Pohon-Pohon Keimanan", 7),
        ("Bab 7: Kepungan Angan-Angan", 8),
        ("Bab 8: 'Kubur-Kubur' Kaku", 9),
        ("Bab 9: Sekolah Kematian", 10),
        ("Bab 10: Pecah Belenggu Bumi", 11),
        ("Bab 11: Hamba yang Merdeka", 12),
        ("Bab 12: Hiburan Para Da'i", 13)
    ]
    
    row = []
    for title, ch_idx in bab_list:
        row.append({"text": f"💎 {title}", "callback_data": f"ch_{ch_idx}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
        
    buttons.append([{"text": "⬅️ Kembali ke Menu Utama", "callback_data": "menu_main"}])
    return {"inline_keyboard": buttons}

def get_subtopics_keyboard(ch_idx):
    if ch_idx < 0 or ch_idx >= len(CHAPTERS):
        ch_idx = 0
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

    # 1. Custom block: epigraf-art-presentation-card (Lakaran abstrak hadis)
    if "epigraf-art-presentation-card" in p:
        return (
            "🎨 <b>EPIGRAF: KEPUNGAN ANGAN-ANGAN (حِصَارُ الأَمَلِ)</b>\n"
            "<i>Sebuah Lukisan Seni Lukisan Abstrak Islam (لَوْحَةٌ مِنَ الفَنِّ التَّجْرِيدِيِّ الإِسْلَامِيِّ)</i>\n\n"
            "🖼 <i>Lakaran ini diilhamkan daripada hadis sahih Rasulullah SAW (riwayat Abdullah bin Mas'ud RA) "
            "tentang hakikat keterbatasan insan di dunia fana dalam kepungan ajal maut.</i>\n\n"
            "💡 Huraian mendalam konsep ini diperincikan seterusnya dalam <b>Bab 7: Kepungan Angan-angan</b>.\n"
            "🌐 <i>Naskhah visual HD penuh boleh ditatap dalam Web PWA Al-Raqaiq.</i>"
        )

    # 2. Handle footnote reference spans: <span class="fn-ref" ...>[X]</span>
    p = re.sub(r'<span[^>]*class=["\']fn-ref["\'][^>]*>(.*?)</span>', r"<b>\1</b>", p, flags=re.DOTALL)
    # 3. Handle other spans: e.g. <span class="num-card-badge">1</span>
    p = re.sub(r'<span[^>]*class=["\']num-card-badge["\'][^>]*>(.*?)</span>', r"<b>[\1]</b> ", p, flags=re.DOTALL)
    p = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", p, flags=re.DOTALL)
    p = re.sub(r"</?span[^>]*>", "", p)
    
    # 4. Buang komentar HTML <!-- ... -->
    p = re.sub(r"<!--.*?-->", "", p, flags=re.DOTALL)
    
    # 5. Remove HTML tags that Telegram does NOT support
    p = re.sub(r"<br\s*/?>", "\n", p)
    p = re.sub(r"</?(?:ul|ol|li)[^>]*>", "\n", p)
    p = re.sub(r"</?(?:h[1-6]|table|tr|td|th)[^>]*>", "\n", p)
    p = re.sub(r"</?(?:div|section|p|small|strong|em|header|footer|article|button|img)[^>]*>", "", p)
    p = re.sub(r'<a\s+[^>]*href=["\']#[^"\']*["\'][^>]*>(.*?)</a>', r"\1", p, flags=re.DOTALL)

    # 6. Markdown formatting
    p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p, flags=re.DOTALL)
    p = re.sub(r"(?<!\*)\*([^\*]+?)\*(?!\*)", format_smart_italic, p)
    p = re.sub(r"(?<!_)_([^_]+?)_(?!_)", format_smart_italic, p)
    
    # 7. Blockquote
    p = re.sub(r"^[ \t]*>[ \t]*(.*)$", r"<blockquote>\1</blockquote>", p, flags=re.MULTILINE)

    # Bersihkan baris kosong berlebihan
    p = re.sub(r"\n{3,}", "\n\n", p)
    return p.strip()

def format_subtopic_text(ch_idx, s_idx, layer, page=0, search_q=None):
    if ch_idx < 0 or ch_idx >= len(CHAPTERS):
        ch_idx = 0
    ch = CHAPTERS[ch_idx]
    subs = ch.get("subtopics", [])
    if not subs:
        return "<i>Tiada teks dalam bab ini.</i>", 1
    
    s_idx = min(s_idx, len(subs) - 1)
    sub = subs[s_idx]
    
    mode_label = "🔵 <b>Versi Lengkap (Terjemahan Penuh)</b>" if layer == "layer1" else "⚡ <b>Ringkasan Eksklusif (Layer 2)</b>"
    
    highlight_note = (f'🔍 <i>Kata Kunci: "<b>{search_q}</b>" (diserlahkan dengan garis tebal)</i>\n') if search_q else ""
    
    header = (
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
        f"🧭 <b>AL-RAQĀ'IQ (الرَّقَـائِق)</b>\n"
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
            
        # Paginasi perenggan (~1400 aksara per muka surat)
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
        if search_q:
            body = highlight_keyword(body, search_q)
        
        footer = f"\n\n🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n📄 <i>Halaman {page+1} daripada {total_pages}</i>"
        return header + body + footer, total_pages
    else:
        # Layer 2: Ringkasan Eksklusif
        summary_raw = sub.get("summary", "Ringkasan sedang dimantapkan...")
        summary_clean = md_to_telegram_html(summary_raw)
        if search_q:
            summary_clean = highlight_keyword(summary_clean, search_q)
        return header + f"<blockquote>{summary_clean}</blockquote>", 1

def get_subtopic_reading_keyboard(ch_idx, s_idx, layer, page, total_pages, search_q=None):
    ch = CHAPTERS[ch_idx]
    buttons = []
    
    # Pautan pantas antara Epigraf (Ch 0) <-> Bab 7: Kepungan Angan-angan (Ch 8)
    if ch_idx == 0:
        buttons.append([{"text": "📖 Buka Bab 7: Kepungan Angan-angan (Huraian Hadis) 🔍", "callback_data": "ch_8"}])
    elif ch_idx == 8:
        buttons.append([{"text": "🎨 Kembali ke Epigraf Lukisan Abstrak Hadis 🔙", "callback_data": "sub_0_0_0"}])
    
    # 1. Butang Paginasi
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

def format_hikmah_message(item, q_idx, total):
    arabic = item.get("arabic", "").strip()
    arabic_part = f"« {arabic} »\n\n" if arabic else ""
    
    translation = item.get("translation", "").strip()
    if not translation:
        translation = item.get("quote", "").strip()
    
    translation_clean = md_to_telegram_html(translation)
    dimensi = item.get("dimensi_haraki") or item.get("dimensi") or ""
    dimensi_clean = md_to_telegram_html(dimensi.strip())
    
    dimensi_part = f"\n\n⚔️ <b>Fiqh Tarbawi Haraki:</b>\n<i>{dimensi_clean}</i>" if dimensi_clean else ""
    
    ch_num = item.get("chapterNumber", "")
    ch_title = item.get("chapterTitle", "")
    sub_title = item.get("subtopicTitle", "")
    
    return (
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
        f"💎 <b>MUTIARA HIKMAH AL-RAQĀ'IQ #{item.get('id', q_idx + 1)} ({q_idx + 1}/{total})</b>\n"
        f"👤 <b>{item.get('speaker') or item.get('tokoh') or 'Tokoh Dakwah'}</b>\n"
        f"🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
        f"{arabic_part}"
        f"<blockquote>{translation_clean}</blockquote>"
        f"{dimensi_part}\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📚 <b>Sumber:</b> {ch_num} - {ch_title}\n"
        f"📑 <b>Topik:</b> {sub_title}\n"
        f"🧭 <i>Kitab Al-Raqā'iq — As-Syeikh Muhammad Ahmad Ar-Rasyid</i>"
    )

def get_hikmah_keyboard(item, q_idx, total):
    prev_idx = (q_idx - 1) % total
    next_idx = (q_idx + 1) % total
    
    ch_idx = item.get('chapterIndex', 1)
    s_idx = item.get('subtopicIndex', 0)
    
    return {
        "inline_keyboard": [
            [
                {"text": "⬅️ Sebelum", "callback_data": f"hikmah_{prev_idx}"},
                {"text": "🎲 Rawak", "callback_data": "hikmah_random"},
                {"text": "Seterusnya ➡️", "callback_data": f"hikmah_{next_idx}"}
            ],
            [
                {"text": f"📖 Baca: {item.get('subtopicTitle', 'Topik Asal')[:28]}", "callback_data": f"sub_{ch_idx}_{s_idx}_0"}
            ],
            [
                {"text": "📘 Senarai Bab", "callback_data": "menu_chapters"},
                {"text": "🏠 Menu Utama", "callback_data": "menu_main"}
            ]
        ]
    }

def handle_hikmah(chat_id, q_idx, message_id=None):
    if not HIKMAH_DATA:
        return edit_message_or_send(chat_id, message_id, "💎 <b>MUTIARA HIKMAH AL-RAQĀ'IQ</b>\n\nKoleksi mutiara hikmah sedang dikemas kini.", {"inline_keyboard": [[{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]]})
    
    total = len(HIKMAH_DATA)
    q_idx = q_idx % total
    item = HIKMAH_DATA[q_idx]
    
    txt = format_hikmah_message(item, q_idx, total)
    kb = get_hikmah_keyboard(item, q_idx, total)
    return edit_message_or_send(chat_id, message_id, txt, kb)

# ================= CARIAN PANTAS =================

def normalize_kw(text):
    if not text:
        return ""
    return re.sub(r"[\u2018\u2019\u02bb\u02bc`]", "'", str(text).lower())

def highlight_keyword(text, query):
    if not query:
        return text
    safe_q = html.escape(query)
    pattern = re.compile(r'(<[^>]+>)|(' + re.escape(safe_q) + r')', re.IGNORECASE)
    return pattern.sub(lambda m: m.group(1) if m.group(1) else f"<u><b>{m.group(2)}</b></u>", text)

def handle_search(chat_id, query):
    USER_SEARCH[chat_id] = query
    norm_query = normalize_kw(query)
    matches = []
    
    for ch_idx, ch in enumerate(CHAPTERS):
        for s_idx, sub in enumerate(ch["subtopics"]):
            found = False
            # 1. Semak Perenggan Versi Penuh
            for p in sub.get("paragraphs", []):
                cleaned_p = clean_paragraph_for_telegram(p)
                plain_p = strip_tags(cleaned_p)
                if norm_query in normalize_kw(plain_p):
                    idx = normalize_kw(plain_p).find(norm_query)
                    start_pos = max(0, idx - 45)
                    end_pos = min(len(plain_p), start_pos + 190)
                    prefix = "..." if start_pos > 0 else ""
                    suffix = "..." if end_pos < len(plain_p) else ""
                    snippet = prefix + plain_p[start_pos:end_pos] + suffix
                    safe_snippet = html.escape(snippet)
                    highlighted = highlight_keyword(safe_snippet, query)
                    matches.append((ch_idx, s_idx, "layer1", ch['number'], sub['title'], highlighted))
                    found = True
                    break
            if found:
                if len(matches) >= 6: break
                continue

            # 2. Semak Tajuk Subtopik
            if norm_query in normalize_kw(sub["title"]):
                matches.append((ch_idx, s_idx, "layer1", ch['number'], sub['title'], f"Tajuk subtopik membincangkan topik berkaitan <u><b>{html.escape(query)}</b></u>."))
                if len(matches) >= 6: break
                continue

            # 3. Semak Ringkasan Layer 2
            if norm_query in normalize_kw(sub.get("summary", "")):
                summary_clean = strip_tags(sub.get("summary", ""))
                idx = normalize_kw(summary_clean).find(norm_query)
                start_pos = max(0, idx - 45)
                end_pos = min(len(summary_clean), start_pos + 190)
                prefix = "..." if start_pos > 0 else ""
                suffix = "..." if end_pos < len(summary_clean) else ""
                snippet = prefix + summary_clean[start_pos:end_pos] + suffix
                safe_snippet = html.escape(snippet)
                highlighted = highlight_keyword(safe_snippet, query)
                matches.append((ch_idx, s_idx, "layer2", ch['number'], sub['title'], highlighted))
                if len(matches) >= 6: break

        if len(matches) >= 6:
            break
            
    if not matches:
        return send_message(
            chat_id, 
            f"🔍 Maaf, tiada perbincangan dijumpai bagi kata kunci: <b>\"{html.escape(query)}\"</b>.\n\n"
            f"Cuba kata kunci lain seperti: <i>tasbih, malam, istighfar, itsar, belenggu, merdeka, waktu terluang, daud</i>.",
            get_main_menu_keyboard()
        )

    buttons = []
    text_lines = [
        f"🔍 <b>HASIL CARIAN UNTUK: \"{html.escape(query)}\"</b>",
        f"<i>Dijumpai {len(matches)} perbincangan berkaitan dalam Al-Raqā'iq:</i>\n"
    ]
    for i, (ch_idx, s_idx, target_layer, ch_num, sub_title, snippet) in enumerate(matches):
        layer_badge = "📖" if target_layer == "layer1" else "⚡"
        text_lines.append(f"{layer_badge} <b>{i+1}. {ch_num}: {sub_title}</b>\n<i>\"{snippet}\"</i>\n")
        buttons.append([{"text": f"👉 Baca: {ch_num} - {sub_title[:22]}", "callback_data": f"subsearch_{ch_idx}_{s_idx}_{target_layer}_0"}])
        
    buttons.append([
        {"text": "🔍 Panduan Carian", "callback_data": "menu_search_info"},
        {"text": "🏠 Menu Utama", "callback_data": "menu_main"}
    ])
    
    return send_message(chat_id, "\n".join(text_lines), {"inline_keyboard": buttons})

# ================= HANDLERS =================

def get_welcome_text():
    total_q = len(HIKMAH_DATA) if HIKMAH_DATA else 117
    return (
        "🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
        "🧭 <b>AL-RAQĀ'IQ (الرَّقَـائِق)</b> 🧭\n"
        "<i>Pelembut-pelembut Hati Harakah Islamiyah</i>\n"
        "🔵 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
        "<blockquote>📖 <b>Pengarang:</b> As-Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)\n"
        "🌟 <b>Siri Ketiga Fiqh Haraki:</b> Jantung rohani, pelembut jiwa, dan benteng penawar terhadap penyakit mabuk kuasa (ghuluw siasah) dalam membina watan berdaulat.</blockquote>\n\n"
        "📚 <b>Kandungan &amp; Metrik Lengkap:</b>\n"
        "• 📚 <b>14 Bahagian:</b> Epigraf, Mukadimah &amp; 12 Bab Utama\n"
        "• 📑 <b>101 Topik Lengkap:</b> 1 Epigraf Pembuka + 100 Subtajuk Tematik\n"
        "• 📝 <b>181 Nota Kaki Ilmiah:</b> Takhrij hadis &amp; rujukan salaf\n"
        f"• 💎 <b>{total_q} Mutiara Hikmah:</b> Nukilan emas hadis Nabi SAW &amp; tokoh pejuang\n\n"
        "📚 <b>Struktur Dwi-Lapisan (Dual-Layer):</b>\n"
        "• 🔵 <code>Layer 1</code>: Versi Penuh Terjemahan Lengkap\n"
        "• ⚡ <code>Layer 2</code>: Ringkasan Eksklusif Berstruktur &amp; Analisis Haraki\n\n"
        "🌐 <b>Web PWA Rasmi (Tema Nilam &amp; Amber):</b>\n"
        "https://najsha97-rgb.github.io/al-raqaiq/\n\n"
        "<i>Sila pilih menu di bawah untuk memulakan bacaan:</i>"
    )

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()
    
    if text.startswith("/start") or text.startswith("/menu"):
        send_message(chat_id, get_welcome_text(), get_main_menu_keyboard())
        return

    if text.startswith("/baca"):
        edit_message_or_send(chat_id, None, "📘 <b>PILIH BAB KANDUNGAN AL-RAQĀ'IQ:</b>\n\nKitab ini mengandungi Epigraf Seni Lukisan Hadis, Mukadimah, dan 12 Bab Utama.\nSila pilih bab untuk melihat senarai topik:", get_chapters_keyboard())
        return

    if text.startswith("/cari"):
        query = text.replace("/cari", "").strip()
        if not query:
            handle_callback({"id": "0", "data": "menu_search_info", "message": {"chat": {"id": chat_id}, "message_id": 0}})
            return
        handle_search(chat_id, query)
        return

    if text.startswith("/help") or text.startswith("/panduan"):
        handle_callback({"id": "0", "data": "menu_search_info", "message": {"chat": {"id": chat_id}, "message_id": 0}})
        return

    if text.startswith("/hikmah"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            q_idx = int(parts[1]) - 1
        else:
            q_idx = random.randint(0, len(HIKMAH_DATA) - 1) if HIKMAH_DATA else 0
        handle_hikmah(chat_id, q_idx)
        return

    # Mesej biasa -> Lakukan carian pantas
    handle_search(chat_id, text)

def handle_callback(cb):
    cb_id = cb["id"]
    data = cb.get("data", "")
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb.get("message", {}).get("message_id")
    
    if cb_id != "0":
        answer_callback_query(cb_id)
    
    if data == "noop":
        return

    if data == "reopen_search":
        search_q = USER_SEARCH.get(chat_id)
        if search_q:
            handle_search(chat_id, search_q)
        else:
            send_message(chat_id, "Sila buat carian baru dengan <code>/cari [kata kunci]</code>.")
        return

    if data == "menu_main":
        edit_message_or_send(chat_id, msg_id, get_welcome_text(), get_main_menu_keyboard())
        return

    if data == "menu_prolog":
        # Akses pantas ke Epigraf Seni Lukisan Hadis (Bab 0, Subtopik 0)
        content_txt, total_pages = format_subtopic_text(0, 0, "layer1", 0)
        kb = get_subtopic_reading_keyboard(0, 0, "layer1", 0, total_pages)
        edit_message_or_send(chat_id, msg_id, content_txt, kb)
        return

    if data == "menu_chapters":
        txt = (
            "📘 <b>PILIH BAB KANDUNGAN AL-RAQĀ'IQ:</b>\n\n"
            "Kitab ini mengandungi Epigraf Seni Lukisan Hadis, Mukadimah, dan 12 Bab Utama.\n"
            "Sila pilih bab untuk melihat senarai topik perbincangan:"
        )
        edit_message_or_send(chat_id, msg_id, txt, get_chapters_keyboard())
        return

    if data.startswith("ch_"):
        ch_idx = int(data.split("_")[1])
        if ch_idx < 0 or ch_idx >= len(CHAPTERS):
            ch_idx = 0
        ch = CHAPTERS[ch_idx]
        txt = (
            f"🏛 <b>{ch['number']}: {ch['title']}</b>\n"
            f"🏷 <i>{ch.get('title_ar', '')}</i>\n\n"
            f"Terdapat <b>{len(ch['subtopics'])} sub-tajuk</b> dalam bahagian ini. Sila pilih tajuk yang ingin dibaca:"
        )
        edit_message_or_send(chat_id, msg_id, txt, get_subtopics_keyboard(ch_idx))
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
        edit_message_or_send(chat_id, msg_id, content_txt, kb)
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
        edit_message_or_send(chat_id, msg_id, content_txt, kb)
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
        edit_message_or_send(chat_id, msg_id, content_txt, kb)
        return

    if data == "hikmah_random":
        q_idx = random.randint(0, len(HIKMAH_DATA) - 1) if HIKMAH_DATA else 0
        handle_hikmah(chat_id, q_idx, msg_id)
        return

    if data.startswith("hikmah_"):
        q_idx = int(data.split("_")[1])
        handle_hikmah(chat_id, q_idx, msg_id)
        return

    if data == "menu_mode":
        cur = get_user_layer(chat_id)
        cur_name = "Versi Penuh (Terjemahan Lengkap)" if cur == "layer1" else "Ringkasan Eksklusif"
        txt = (
            f"🔄 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            f"⚙️ <b>TETAPAN MOD BACAAN AL-RAQĀ'IQ</b>\n"
            f"🔄 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            f"Mod semasa anda: <b>{cur_name}</b>\n\n"
            f"• 🔵 <b>Versi Penuh (Layer 1):</b> Memaparkan teks terjemahan penuh kitab tanpa tapisan (Epigraf, Mukadimah, 12 Bab Utama).\n"
            f"• ⚡ <b>Ringkasan Eksklusif (Layer 2):</b> Memaparkan intisari padat, poin-poin utama, serta nukilan tokoh penting bagi semakan pantas."
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🔵 Tetapkan: Versi Penuh", "callback_data": "setmode_layer1"}],
                [{"text": "⚡ Tetapkan: Ringkasan Eksklusif", "callback_data": "setmode_layer2"}],
                [{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]
            ]
        }
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data.startswith("setmode_"):
        new_mode = data.split("_")[1]
        set_user_layer(chat_id, new_mode)
        mode_str = "Versi Penuh" if new_mode == "layer1" else "Ringkasan Eksklusif"
        answer_callback_query(cb_id, f"Mod berjaya ditukar kepada: {mode_str}")
        handle_callback({"id": cb_id, "data": "menu_main", "message": cb["message"]})
        return

    if data == "menu_search_info":
        txt = (
            "🔍 ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "🧭 <b>PANDUAN CARIAN PANTAS AL-RAQĀ'IQ</b>\n"
            "🔍 ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "Anda boleh mencari sebarang topik, nama tokoh, mutiara tadabbur, atau kata kunci tazkiyah haraki dengan menaip terus:\n\n"
            "👉 <code>/cari [kata kunci]</code>\n\n"
            "<b>Contoh Kata Kunci Pilihan:</b>\n"
            "• <code>/cari tasbih</code> — Tasbih mengukuhkan kerajaan (Model Nabi Daud AS)\n"
            "• <code>/cari malam</code> — Madrasah malam &amp; sepertiga malam terakhir\n"
            "• <code>/cari itsar</code> — Fiqh al-i'tsar &amp; ukhuwah akar umbi\n"
            "• <code>/cari belenggu</code> — Memecahkan belenggu bumi (quyud al-ard)\n"
            "• <code>/cari merdeka</code> — Hamba yang merdeka &amp; izzah Islam\n"
            "• <code>/cari waktu terluang</code> — Wasiat Umar bin Abdul Aziz: Lenyaplah waktu terluang!\n"
            "• <code>/cari kematian</code> — Sekolah-sekolah kematian &amp; penawar angan-angan\n\n"
            "<i>Atau taipkan terus kata kunci carian anda ke dalam ruangan sembang ini!</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "📘 Senarai Bab", "callback_data": "menu_chapters"}],
                [{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]
            ]
        }
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "menu_pbi_raqaiq":
        txt = (
            "🌍 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>UMMAH FADHILAH &amp; PERADABAN BARU ISLAM (PBI)</b>\n"
            "<i>Sumbangan Kitab Al-Raqā'iq dalam Membina Kuasa Nasional 100 Tahun Kedua</i>\n"
            "🌍 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "<blockquote>🧭 <b>Peranan Strategik Kitab:</b>\n"
            "Kitab <b>Al-Raqā'iq</b> adalah <b>jantung rohani dan benteng moral</b> kepada seluruh pembinaan Kuasa Nasional. "
            "Ia merawat bahaya terbesar akhir 100 Tahun Pertama: <i>kekeringan batin dan mabuk kuasa (ghuluw siasah)</i>. "
            "Al-Raqā'iq memastikan kedaulatan dibina di atas sujud dan ubudiah mutlak kepada Allah SWT.</blockquote>\n\n"
            "📌 <b>Enam Teras Sumbangan Al-Raqā'iq:</b>\n"
            "1. 👑 <b>Tasbih Kerajaan:</b> Model Nabi Daud AS (Bab 1)\n"
            "2. 🌙 <b>Madrasah Malam:</b> Sepertiga malam terakhir (Bab 2)\n"
            "3. 🤝 <b>Komuniti Akar Umbi:</b> Ukhuwah &amp; fiqh itsar (Bab 5)\n"
            "4. ⛓️ <b>Pecah Belenggu Bumi:</b> Bebas ketakutan harta &amp; jawatan (Bab 10)\n"
            "5. 🕊️ <b>Hamba Merdeka:</b> Izzah &amp; runtuhkan inferiority complex (Bab 11)\n"
            "6. ⏳ <b>Etos Kerja Pejuang:</b> Lenyaplah waktu terluang! (Bab 12)\n\n"
            "<i>Sila pilih butang di bawah untuk membaca huraian lanjut atau memuat turun dokumen:</i>"
        )
        edit_message_or_send(chat_id, msg_id, txt, get_pbi_main_keyboard())
        return

    if data == "pbi_sub_1":
        txt = (
            "👑 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>1. TASBIH MENGUKUHKAN KERAJAAN (BAB 1)</b>\n"
            "<i>Model Kepimpinan Kenabian: Nabi Daud 'Alaihissalam</i>\n"
            "👑 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>Teladan Nabi Daud AS:</b> Baginda dianugerahkan kerajaan agung (<i>mulk</i>) dan kekuatan industri besi yang melentur bukan kerana tipu daya taktik, tetapi kerana baginda seorang hamba yang sentiasa merintih (<i>awwāb</i>), bertahajud, dan bertasbih di mihrab.\n\n"
            "• <b>Prinsip Kuasa Nasional:</b> Kedaulatan watan Islam berpasak kukuh pada sujud, istighfar, dan zikir, bukan semata-mata kelicikan politik. Peradaban teguh apabila puncaknya tunduk kepada Pencipta."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_2":
        txt = (
            "🌙 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>2. MADRASAH MALAM &amp; MINIT BERHARGA (BAB 2)</b>\n"
            "<i>Sepertiga Malam Terakhir: Medan Menakluk Tidur</i>\n"
            "🌙 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>Minit-Minit Berharga:</b> Waktu sepertiga malam terakhir adalah penentu darjat dan keampunan di sisi Allah SWT.\n\n"
            "• <b>Enjin Siang Bermula Malam:</b> Kemenangan dakwah di siang hari ditentukan oleh linangan air mata pejuang pada waktu malam. Pejuang yang gagal menakluk selimut tidurnya tidak akan mampu memimpin pembebasan dan membina peradaban baru."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_3":
        txt = (
            "🤝 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>3. KOMUNITI AKAR UMBI &amp; FIQH ITSAR (BAB 5)</b>\n"
            "<i>Asas Masyarakat Harmoni Pembina Ummah Fadhilah</i>\n"
            "🤝 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>Ukhuwah Takwa:</b> Ikatan persaudaraan sejati ditegakkan di atas ketakwaan, kebenaran dalam berkata-kata, dan menyingkirkan kepura-puraan (<i>takalluf</i>).\n\n"
            "• <b>Fiqh Al-I'tsār:</b> Mengutamakan saudara seakidah melebihi diri sendiri. Inilah benteng sosial yang menewaskan fahaman kebendaan dan individualisme liberal Barat di peringkat komuniti watan."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_4":
        txt = (
            "⛓️ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>4. MEMECAHKAN BELENGGU BUMI (BAB 10)</b>\n"
            "<i>Pembebasan daripada Keterikatan Harta &amp; Jawatan</i>\n"
            "⛓️ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>Quyūd al-Arḍ (Belenggu Bumi):</b> Ketakutan kehilangan rezeki, cinta keterlaluan kepada rumah mewah, dan kemaruk jawatan melumpuhkan cita-cita peradaban.\n\n"
            "• <b>Keberanian Mempertahankan Kedaulatan:</b> Pemimpin dan rakyat yang terbelenggu dengan kemewahan tidak akan sanggup berkorban mempertahankan kedaulatan watan daripada tekanan hegemoni luar."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_5":
        txt = (
            "🕊️ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>5. HAMBA YANG MERDEKA (BAB 11)</b>\n"
            "<i>Izzah Islam &amp; Meruntuhkan Rasa Rendah Diri</i>\n"
            "🕊️ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>Paradoks Kemerdekaan:</b> Kemerdekaan hakiki hanya lahir apabila seseorang menghambakan diri secara mutlak kepada Allah semata-mata.\n\n"
            "• <b>Menghapuskan Inferiority Complex:</b> Melahirkan da'i dan warganegara yang bermaruah tinggi (<i>izzah</i>), meneladani ketegasan Saidina Rib'i bin 'Amir RA ketika berhadapan dengan keangkuhan maharaja Parsi."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_6":
        txt = (
            "⏳ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>6. ETOS KERJA: LENYAPLAH WAKTU TERLUANG! (BAB 12)</b>\n"
            "<i>Wasiat Agung Khalifah Umar bin Abdul Aziz</i>\n"
            "⏳ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "<blockquote><b>وَأَيْنَ الفَرَاغُ؟ ذَهَبَ الفَرَاغُ فَلَا فَرَاغَ إِلاَّ عِنْدَ اللهِ!</b>\n"
            "<i>'Di manakah lagi adanya waktu terluang? Lenyaplah waktu terluang, maka tiada lagi kerehatan melainkan di sisi Allah!'</i></blockquote>\n\n"
            "• <b>Umat Pencipta:</b> Menukar masyarakat daripada pengguna pasif kepada arkitek dan pencipta tamadun yang produktif, berdaya saing, dan menghargai setiap detik kehidupan."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_tonggak":
        txt = (
            "🏛️ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>PEMETAAN 8 TONGGAK KUASA NASIONAL</b>\n"
            "<i>Sumbangan Kitab Al-Raqā'iq</i>\n"
            "🏛️ ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>Tonggak 1 (Tasawur &amp; Akidah):</b> Pemurnian tauhid &amp; ubudiah batin; menyandarkan keteguhan kuasa watan kepada tasbih dan sujud.\n"
            "• <b>Tonggak 5 (Kesatuan Ummah):</b> Menghidupkan sifat <i>al-i'tsār</i> dan ukhuwah takwa di peringkat komuniti akar umbi.\n"
            "• <b>Tonggak 6 (Pertahanan &amp; Keselamatan):</b> Membina daya tahan batiniah mencontohi kekuatan ketenteraan Nabi Daud AS.\n"
            "• <b>Tonggak 8 (Integriti Sosial &amp; Akhlak):</b> Memerdekakan jiwa daripada belenggu kebendaan dan keselesaan duniawi."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_sub_tetralogi":
        txt = (
            "📚 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "<b>HARMONISASI 4 KARYA TETRALOGI AL-RASYID</b>\n"
            "<i>Gagasan Menuju 100 Tahun Kedua</i>\n"
            "📚 ━━━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "• <b>1. Al-Muntalaq:</b> Titik mula kesedaran, memurnikan tauhid, kefahaman komprehensif dakwah.\n"
            "• <b>2. Al-‘Awā’iq:</b> Radar pengesan ranjau nafsu, kepentingan diri, dan fitnah perjalanan.\n"
            "• <b>3. Al-Raqā'iq:</b> Enjin batin pejuang, pelembut hati, benteng pencegah <i>ghuluw siasah</i>.\n"
            "• <b>4. Al-Masār:</b> Seni bina perancangan, polisi pentadbiran, dan strategi peradaban watan."
        )
        kb = {"inline_keyboard": [[{"text": "⬅️ Kembali ke Menu PBI", "callback_data": "menu_pbi_raqaiq"}]]}
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

    if data == "pbi_doc_docx":
        doc_path = os.path.join(os.path.dirname(__file__), "Gagasan_Ummah_Fadhilah_Kuasa_Nasional_dan_Tetralogi_Al-Rasyid.docx")
        if os.path.exists(doc_path):
            caption = (
                "📄 <b>DOKUMEN PENUH (MICROSOFT WORD)</b>\n\n"
                "<b>Tajuk:</b> Gagasan Ummah Fadhilah, Kuasa Nasional dan Sumbangan Tetralogi Al-Rasyid\n"
                "<b>Format:</b> .docx (Boleh disunting &amp; dikaji bersama komuniti/usrah)\n\n"
                "<i>Al-Raqā'iq: Pelembut Hati, Enjin Ruhiyah &amp; Pembinaan Komuniti Rabbani</i>"
            )
            send_document(chat_id, doc_path, caption)
        else:
            send_message(chat_id, "⚠️ Fail Word (.docx) tidak ditemui dalam direktori bot.")
        return

    if data == "pbi_doc_pdf":
        pdf_path = os.path.join(os.path.dirname(__file__), "Gagasan_Ummah_Fadhilah_Kuasa_Nasional_dan_Tetralogi_Al-Rasyid.pdf")
        if os.path.exists(pdf_path):
            caption = (
                "📕 <b>E-BUKU DOKUMEN PENGENALAN AM (PDF)</b>\n\n"
                "<b>Tajuk:</b> Gagasan Ummah Fadhilah, Kuasa Nasional dan Sumbangan Tetralogi Al-Rasyid\n"
                "<b>Format:</b> .pdf (Sedia dicetak &amp; dibaca di mana-mana peranti)\n\n"
                "<i>Kerangka Pemikiran Menuju 100 Tahun Kedua Pasca-1924</i>"
            )
            send_document(chat_id, pdf_path, caption)
        else:
            send_message(chat_id, "⚠️ Fail PDF (.pdf) tidak ditemui dalam direktori bot.")
        return

    if data == "pbi_khas_docx":
        doc_path = os.path.join(os.path.dirname(__file__), "Sumbangan_Al_Raqaiq_Dalam_Ummah_Fadhilah_Kuasa_Nasional_dan_PBI.docx")
        if os.path.exists(doc_path):
            caption = (
                "📄 <b>DOKUMEN KHAS AL-RAQĀ'IQ (WORD)</b>\n\n"
                "<b>Tajuk:</b> Sumbangan Kitab Al-Raqā'iq dalam Pembinaan Ummah Fadhilah, Kuasa Nasional &amp; PBI\n"
                "<b>Format:</b> .docx (Pelembut Hati, Enjin Ruhiyah &amp; Pembinaan Komuniti Rabbani)\n\n"
                "<i>Siri Ihya' Fiqh Ad-Da'wah • As-Syeikh Muhammad Ahmad al-Rasyid</i>"
            )
            send_document(chat_id, doc_path, caption)
        else:
            send_message(chat_id, "⚠️ Fail Word (.docx) Khas tidak ditemui dalam direktori bot.")
        return

    if data == "pbi_khas_pdf":
        pdf_path = os.path.join(os.path.dirname(__file__), "Sumbangan_Al_Raqaiq_Dalam_Ummah_Fadhilah_Kuasa_Nasional_dan_PBI.pdf")
        if os.path.exists(pdf_path):
            caption = (
                "📕 <b>DOKUMEN KHAS AL-RAQĀ'IQ (PDF)</b>\n\n"
                "<b>Tajuk:</b> Sumbangan Kitab Al-Raqā'iq dalam Pembinaan Ummah Fadhilah, Kuasa Nasional &amp; PBI\n"
                "<b>Format:</b> .pdf (E-Buku sedia cetak)\n\n"
                "<i>Enjin Ruhiyah &amp; Benteng Pencegah Ghuluw Siasah</i>"
            )
            send_document(chat_id, pdf_path, caption)
        else:
            send_message(chat_id, "⚠️ Fail PDF (.pdf) Khas tidak ditemui dalam direktori bot.")
        return

    if data == "menu_about":
        txt = (
            "ℹ️ ━━━━━━━━━━━━━━━━━━━ ⚡\n"
            "🧭 <b>TENTANG KITAB AL-RAQĀ'IQ (الرقائق)</b> 🧭\n"
            "ℹ️ ━━━━━━━━━━━━━━━━━━━ ⚡\n\n"
            "<blockquote><b>Pengarang:</b> As-Syeikh Muhammad Ahmad Ar-Rasyid (رحمه الله)\n"
            "<b>Siri:</b> Siri Ketiga Fiqh Haraki (Siri Ihya' al-Fiqh al-Da'wi)\n"
            "<b>Tema Utama:</b> Tazkiyah al-Nafs, Tarbiyah Ruhiyyah &amp; Fiqh Qulub Harakah Islamiyah\n"
            "<b>Peranan:</b> Jantung rohani, pelembut hati pejuang, dan benteng penawar terhadap penyakit mabuk kekuasaan (ghuluw siasah) dalam membina watan berdaulat.</blockquote>\n\n"
            "📚 <b>Kedudukan dalam Tetralogi al-Rasyid:</b>\n"
            "1. <b>Al-Muntalaq:</b> Titik tolak kebangkitan &amp; kefahaman syumul.\n"
            "2. <b>Al-‘Awā’iq:</b> Radar pengesan ranjau &amp; batu penghalang jalan dakwah.\n"
            "3. <b>Al-Raqā'iq:</b> Enjin batin, santapan jiwa, dan keikhlasan mutlak.\n"
            "4. <b>Al-Masār:</b> Seni bina perancangan, polisi pentadbiran, dan strategi peradaban.\n\n"
            "🌐 <b>Aplikasi Web PWA Rasmi (Tema Nilam &amp; Amber):</b>\n"
            "https://najsha97-rgb.github.io/al-raqaiq/"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "🔵 Layari Web PWA Al-Raqaiq 🌐", "url": "https://najsha97-rgb.github.io/al-raqaiq/"}],
                [{"text": "⬅️ Menu Utama", "callback_data": "menu_main"}]
            ]
        }
        edit_message_or_send(chat_id, msg_id, txt, kb)
        return

# ================= POLLING ENGINE =================

def run_bot():
    if not BOT_TOKEN or "ISI_TOKEN" in BOT_TOKEN or "MASUKKAN_TOKEN" in BOT_TOKEN or ":" not in BOT_TOKEN:
        print("\n" + "="*65)
        print("❌ PERHATIAN: TOKEN BOT TELEGRAM AL-RAQAIQ BELUM DITETAPKAN!")
        print("Sila masukkan token bot anda daripada @BotFather ke dalam fail config.json.")
        print("="*65 + "\n")
        return

    print("="*60)
    print("Bot Telegram Al-Raqaiq sedang dijalankan (Refined 2.0)...")
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
        elif me and me.get("error_code") == 404:
            print("\n" + "="*65)
            print("❌ RALAT KRITIKAL: Token bot tidak sah atau tidak wujud di Telegram (404 Not Found)!")
            print("Sila pastikan anda menyalin token bot yang betul daripada @BotFather ke dalam config.json.")
            print("="*65 + "\n")
            return
        print("Sambungan ke api.telegram.org mengalami timeout / lengah rangkaian.")
        print("Mencuba semula dalam 5 saat...")
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
            time.sleep(3)
        except Exception as e:
            print(f"Ralat polling: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_bot()
