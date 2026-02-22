import telebot
import gspread
import time
import datetime
import os
import threading
from oauth2client.service_account import ServiceAccountCredentials
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import apihelper

# --- БАПТАУЛАР ---
TOKEN = '8368545992:AAHb0uhvMycEUVZY_brBT-m7KNEeF_e88js'
bot = telebot.TeleBot(TOKEN)

apihelper.CONNECT_TIMEOUT = 90
apihelper.READ_TIMEOUT = 90

ALLOWED_USERS = [6823758315, 1422985265, 1308796608, 1164531927, 6878526912, 6410241910, 894058330, 7106426018,
                 7453779842, 914579084, 7728808297, 6314059700, 6613036663, 6727349090, 6723015393, 7794645879,
                 750015780, 5626103363, 6613799418, 5917588361, 7604320093, 6785692540, 8353014504, 936232920,
                 1219046090, ]

AUYZ_SUBS = ["АНГЛ", "ӘДЕБ", "БИО", "ГЕО", "ДЖТ", "ҚҰҚЫҚ", "ЛИТ", "РУС", "ТАРИХ", "ТІЛ"]
ESEP_SUBS = ["ИНФО", "МАТ", "МС", "ФИЗ", "ХИМ", "ГЕОМ"]

BM_CRITERIA = [
    "Тапсырмалардың уақытылы әрі дұрыс салынуы",
    "ПС алдындағы мұғалімдердің материалдарын (слайд) тексеру",
    "ПС шынайы тексеру",
    "ПС записі мен отслежка уақытылы енгізілуі",
    "СТ запись пен отслежканы уақытылы жинап беру",
    "СТ бойынша ескертулерді уақытылы айту",
    "СТ сұрақтарын уақытылы жіберу",
    "СТ шынайы алған куратор пайызы",
    "СТ уақытылы алған куратор пайызы"
]

TM_CRITERIA = [
    "Платформаның уақытылы әрі толық тексеру",
    "ЖЖ пікір шынайылығын тексеру",
    "ПС оқушы камерасын толық тексеру",
    "СТ запись пен отслежканы толық қосуын қадағалау",
    "СТ бойынша ескертулерді уақытылы айту",
    "СТ рейтингін уақытылы жіберу",
    "СТ қатысым",
    "Кураторлардың платформа ескертуді түзеу пайызы",
    "ПС қатысым уақытылы толтыру",
    "Платформа бойынша ескертулерді уақытылы беру"
]

pending_responses = {}


# --- ФУНКЦИЯЛАР ---

def send_reminder(chat_id, name, manager_id, message_id):
    time.sleep(1800)  # 30 минут күту

    if chat_id in pending_responses and pending_responses[chat_id] == message_id:
        reminder_msg = (
            f"Құрметті <b>{name}</b>,\n\n"
            f"Сіз бұған дейін жіберілген сапа бағалауы бойынша <b>келісемін/келіспеймін</b> батырмасын баспадыңыз. 🧐\n\n"
            f"Төмендегі батырмалардың бірін таңдап, кері байланыс берсеңіз."
        )
        # manager_id дұрыс келуі үшін
        ikb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Келісемін", callback_data=f"ok_{manager_id}"),
            InlineKeyboardButton("❌ Келіспеймін", callback_data=f"no_{manager_id}")
        )
        try:
            bot.send_message(chat_id, reminder_msg, parse_mode="HTML", reply_markup=ikb)
        except:
            pass


def get_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        ss = client.open('ТАБ')
        return {
            "SMART_AUYZ": ss.worksheet("SMART_AUYZ"), "SMART_ESEP": ss.worksheet("SMART_ESEP"),
            "GENIUS_AUYZ": ss.worksheet("GENIUS_AUYZ"), "GENIUS_ESEP": ss.worksheet("GENIUS_ESEP"),
            "JUNIOR_AUYZ": ss.worksheet("JUNIOR_AUYZ"), "JUNIOR_ESEP": ss.worksheet("JUNIOR_ESEP"),
            "BM": ss.worksheet("BM"), "TM": ss.worksheet("TM")
        }
    except:
        return None


def send_anon(message):
    uid = message.from_user.id
    first_name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "жоқ"
    admin_text = (
        f"<b>АНОНИМДІ ХАБАРЛАМА!</b>\n\n"
        f"<b>Кімнен:</b> {first_name}\n"
        f"<b>Username:</b> {username}\n\n"
        f"<b>ХАБАРЛАМАСЫ:</b>\n{message.text}"
    )
    for a in ALLOWED_USERS:
        try:
            bot.send_message(a, admin_text, parse_mode="HTML")
        except:
            continue
    bot.send_message(message.chat.id, "✅ Хабарламаңыз жіберілді.")


# --- ЖЕТКІЗУ ФУНКЦИЯЛАРЫ ---

def process_rating_delivery(call, r_type):
    manager_id = call.from_user.id
    sheets = get_sheets()
    if not sheets:
        bot.send_message(call.message.chat.id, "❌ Кестеге қосылу мүмкін болмады!")
        return

    active_sheet = sheets.get(r_type)
    criteria_list = BM_CRITERIA if r_type == "BM" else TM_CRITERIA
    display_name = "БМ" if r_type == "BM" else "ТМ"

    st_msg = bot.send_message(call.message.chat.id, f"⌛ {display_name} рейтингі жіберілуде...")

    try:
        all_data = active_sheet.get_all_records()
        sent = 0

        for r in all_data:
            row = {str(k).strip(): v for k, v in r.items()}
            tid = row.get('TG_ID')
            name = row.get('АТЫ-ЖӨНІ') or row.get('Аты-жөні') or "куратор"

            if tid and str(tid).strip():
                msg = (
                    f"Құрметті <b>{name}</b>,\n"
                    f"Сапа көрсеткіштері бойынша апталық рейтингіңіз дайын:\n"
                    f"<b>{display_name} 🌟</b>\n\n"
                    f"📊 <b>Нәтижелерге жеке тоқталып өтсек:</b>\n"
                )

                for idx, c in enumerate(criteria_list, 1):
                    val = row.get(c.strip())
                    if val == "" or val is None or val == "-%":
                        val_str = "-% (бағаланбады)"
                    elif isinstance(val, (int, float)):
                        val_str = f"{val * 100:.2f}%".replace('.', ',')
                    else:
                        val_str = str(val)
                    msg += f"{idx}. {c}: <b>{val_str}</b>\n"

                total = row.get('Жалпы') or row.get('ОРТАК') or row.get('ОРТАҚ') or "-%"
                if isinstance(total, (int, float)):
                    total = f"{total * 100:.2f}%".replace('.', ',')

                msg += f"\n💌 <b>Жалпы бағалауыңыз - {total}</b>\n\n"
                msg += "<b>Бағалаумен келісесіз бе? Кері байланыс беру үшін төмендегі батырманы басу қажет 🫶</b>"

                # Жаңартылған батырма: manager_id қолданылды
                ikb = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Келісемін", callback_data=f"ok_{manager_id}"),
                    InlineKeyboardButton("❌ Келіспеймін", callback_data=f"no_{manager_id}")
                )

                try:
                    sent_msg = bot.send_message(tid, msg, parse_mode="HTML", reply_markup=ikb,
                                                disable_web_page_preview=True)
                    sent += 1
                    pending_responses[tid] = sent_msg.message_id
                    t = threading.Thread(target=send_reminder, args=(tid, name, manager_id, sent_msg.message_id))
                    t.daemon = True
                    t.start()
                    time.sleep(0.2)
                except:
                    continue

        bot.edit_message_text(f"✅ {display_name} рейтингі {sent} адамға жіберілді.", call.message.chat.id,
                              st_msg.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Қате орын алды: {e}")


def process_delivery(call):
    manager_id = call.from_user.id
    p = call.data.split("_")
    sh_key = f"{p[1]}_{p[2]}"
    pan, potok = p[3], p[4]

    sheets = get_sheets()
    if not sheets:
        bot.send_message(call.message.chat.id, "❌ Кестеге қосылу мүмкін болмады!")
        return

    active_sheet = sheets.get(sh_key)
    st_msg = bot.send_message(call.message.chat.id, "⌛ Деректер өңделуде...")

    try:
        recs = active_sheet.get_all_records()
        targets = [r for r in recs if
                   str(r.get('ПӘН', '')).strip().upper() == pan.upper() and str(r.get('ПОТОК', '')).strip() == str(
                       potok)]
        sent = 0

        for r in targets:
            tid = r.get('TG_ID')
            if tid:
                row = {str(k).strip(): v for k, v in r.items()}
                name = row.get('АТЫ-ЖӨНІ') or row.get('Аты-жөні') or "Куратор"

                if "AUYZ" in sh_key:
                    criteria = ["Камера, сырт-келбет/мұқияттылық", "Демонстрация, таймер", "Бекітілген сұрақтарды қою",
                                "Подсказка бермеу/екінші мүмкіндік", "Сұрақтың жауабын айтпау",
                                "Толық емес және қате жауапты қабылдамау", "Оқушының талапқа сай отыруы",
                                "Рейтинг балмен сай келу", "5-10 мин аралығында алу",
                                "Дөрекі болмау, жылы сөйлесу, кері байланыс беру"]
                else:
                    criteria = ["Камера, сырт келбет", "Демонстрация", "Куратордың мұқиятсыздығы", "Екінші гаджет",
                                "Ақ парақпен отыру", "Оқушының талапқа сай отыруы", "Интернеттің дұрыс жасауы, таймер",
                                "Платформаға жүктегенін тексеріп алу", "Рейтинг баллмен сәйкес келу",
                                "Бекітілген уақыт аралығында алу/оқушы саны//дөрекілік танытпау, жылы сөйлесу"]

                raw_val = row.get('Бағалау', '0')
                try:
                    num_score = float(str(raw_val).replace(',', '.'))
                    if num_score > 10:
                        num_score = num_score / 10
                    elif 0 < num_score <= 1:
                        num_score = num_score * 10
                    score_display = "{:.1f}".format(num_score).replace('.', ',')
                except:
                    score_display = str(raw_val).replace('.', ',')

                msg = (
                    f"Құрметті <b>{name}</b>,\n"
                    f"Сабақ тапсыру бойынша сапа бағалауыңыз дайын 🌟\n\n"
                    f"Кері байланысқа тоқталсақ,\n"
                    f"📍 <b>Пән:</b> {pan}\n"
                    f"💌 <b>Бағалауыңыз:</b> {score_display}/10\n\n"
                )

                errs = []
                for c in criteria:
                    val = row.get(c)
                    # Мәнді мәтінге айналдырып, бос орындарды тазалаймыз
                    val_str = str(val).strip().replace(',', '.')

                    # 1. Егер ұяшық бос болса (чекбокс басылмаса), оны өткізіп жібереміз
                    if val_str == "" or val is None:
                        continue

                    # 2. Егер 0.5 болса - ескертуге қосамыз
                    if val_str == "0.5":
                        errs.append(f"⚪️ {c}(0,5)")

                    # 3. Егер нақты 0, False немесе "0.0" болса - ескертуге қосамыз
                    elif val_str in ["0", "0.0", "False", "FALSE"]:
                        errs.append(f"⚪️ {c}")

                if errs:
                    msg += "<b>Ескерту берілген критерий:</b>\n" + "\n".join(errs) + "\n\n"
                else:
                    msg += "<b>СТ бойынша:</b>\n✅ Талапқа сай алынған, ескерту жоқ. Жарайсыз!\n\n"

                fact_link = row.get('Факт') or row.get('ФАКТ') or "Сілтеме табылмады"
                msg += (
                    f"🖇 <b>ФАКТ ДОКС:</b>\n{fact_link}\n\n"
                    f"<b>Бағалаумен келісесіз бе? Кері байланыс беру үшін төмендегі батырманы басу қажет 🫶</b>"
                )

                # ТҮЗЕТІЛДІ: {current_manager_id} орнына {manager_id} қолданылды
                ikb = InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✅ Келісемін", callback_data=f"ok_{manager_id}"),
                    InlineKeyboardButton("❌ Келіспеймін", callback_data=f"no_{manager_id}")
                )

                try:
                    sent_msg = bot.send_message(tid, msg, parse_mode="HTML", reply_markup=ikb,
                                                disable_web_page_preview=True)
                    sent += 1
                    pending_responses[tid] = sent_msg.message_id
                    t = threading.Thread(target=send_reminder, args=(tid, name, manager_id, sent_msg.message_id))
                    t.daemon = True
                    t.start()
                    time.sleep(0.3)
                except:
                    continue

        bot.edit_message_text(f"✅ Дайын! {sent} адамға бағалау жіберілді.", call.message.chat.id, st_msg.message_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Қате орын алды: {e}")


# --- МӘЗІРЛЕР ---
def admin_main_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("SMART / GENIUS / JUNIOR", callback_data="main_sapa"),
        InlineKeyboardButton("БМ РЕЙТИНГ", callback_data="send_rating_BM"),
        InlineKeyboardButton("ТМ РЕЙТИНГ", callback_data="send_rating_TM")
    )
    return markup


def user_extra_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("РЕГЛАМЕНТ", callback_data="main_kitapsha"),
        InlineKeyboardButton("АНОНИМДІ ХАБАРЛАМА", callback_data="anon_msg")
    )
    return markup


# --- ХЕНДЛЕРЛЕР ---

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    welcome_text = (
        f"Сәлеметсіз бе, <b>{name}</b>!\n"
        f"Сапа бөлімінің ботына қош келдіңіз ✨\n\n"
        f"Сіздің ID: <code>{uid}</code>\n"
        f"<b>Жалғастыру үшін керекті бөлімді таңдаңыз:</b>"
    )
    if uid in ALLOWED_USERS:
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=admin_main_menu())
    else:
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=user_extra_menu())


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    d = call.data
    uid = call.from_user.id

    if d.startswith("send_rating_"):
        r_type = d.replace("send_rating_", "")
        process_rating_delivery(call, r_type)

    elif d == "main_kitapsha":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("ЕСЕП ПӘН СТ РЕГЛАМЕНТІ", callback_data="file_ESEP"),
            InlineKeyboardButton("АУЫЗША ПӘН СТ РЕГЛАМЕНТІ", callback_data="file_AUYZ"),
            InlineKeyboardButton("⬅️", callback_data="back")
        )
        bot.edit_message_text("РЕГЛАМЕНТТІ ТАҢДАҢЫЗ👇", call.message.chat.id, call.message.message_id,
                              reply_markup=markup)

    elif d.startswith("file_"):
        ftype = d.replace("file_", "")
        files = {
            "ESEP": ("ЕСЕП СТ РЕГЛАМЕНТ.pdf", "<b>ЕСЕП ПӘН СТ РЕГЛАМЕНТІ</b>"),
            "AUYZ": ("АУЫЗША СТ РЕГЛАМЕНТ.pdf", "<b>АУЫЗША ПӘН СТ РЕГЛАМЕНТІ</b>"),
        }
        fname, caption_text = files.get(ftype, (None, None))
        if fname and os.path.exists(fname):
            with open(fname, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption=caption_text, parse_mode="HTML")
        else:
            bot.answer_callback_query(call.id, "❌ Файл табылмады!", show_alert=True)

    elif d.startswith("no_"):
        bot.answer_callback_query(call.id, "Менеджерге хабарланды!")
        manager_id = d.replace("no_", "")
        if uid in pending_responses: del pending_responses[uid]
        report_text = f"<b>❌ Келіспеушілік!</b>\n\n<b>Куратор:</b> {call.from_user.first_name}\n<b>ID:</b> <code>{uid}</code>\n\n<i>Нәтижемен келіспеді.</i>"
        try:
            bot.send_message(manager_id, report_text, parse_mode="HTML")
        except:
            pass
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    elif d.startswith("ok_"):
        bot.answer_callback_query(call.id, "Рақмет!")
        manager_id = d.replace("ok_", "")
        if uid in pending_responses: del pending_responses[uid]
        report_text = f"<b>✅ Келісім берілді!</b>\n\n<b>Куратор:</b> {call.from_user.first_name}\n<b>ID:</b> <code>{uid}</code>\n\n<i>Бағалаумен келісті.</i>"
        try:
            bot.send_message(manager_id, report_text, parse_mode="HTML")
        except:
            pass
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    elif d == "anon_msg":
        msg = bot.send_message(call.message.chat.id, "Хабарламаңызды жазыңыз:")
        bot.register_next_step_handler(msg, send_anon)

    elif d == "back":
        if uid in ALLOWED_USERS:
            bot.edit_message_text("Бөлімді таңдаңыз:", call.message.chat.id, call.message.message_id,
                                  reply_markup=admin_main_menu())
        else:
            bot.edit_message_text("Қосымша мәзір:", call.message.chat.id, call.message.message_id,
                                  reply_markup=user_extra_menu())

    elif d == "main_sapa":
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("SMART БӨЛІМІ", callback_data="m_SMART"),
            InlineKeyboardButton("GENIUS БӨЛІМІ", callback_data="m_GENIUS"),
            InlineKeyboardButton("JUNIOR БӨЛІМІ", callback_data="m_JUNIOR"),
            InlineKeyboardButton("⬅️", callback_data="back")
        )
        bot.edit_message_text("Бөлімді таңдаңыз:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif d.startswith("m_"):
        cat = d.replace("m_", "")
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("АУЫЗША", callback_data=f"l_{cat}_AUYZ"),
            InlineKeyboardButton("ЕСЕП", callback_data=f"l_{cat}_ESEP")
        ).add(InlineKeyboardButton("⬅", callback_data="back"))
        bot.edit_message_text(f"{cat} бағыты:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif d.startswith("l_"):
        p = d.split("_")
        cat, mode = p[1], p[2]
        subs = AUYZ_SUBS if mode == "AUYZ" else ESEP_SUBS
        markup = InlineKeyboardMarkup(row_width=3).add(
            *[InlineKeyboardButton(s, callback_data=f"p_{cat}_{mode}_{s}") for s in subs]).add(
            InlineKeyboardButton("⬅", callback_data="back"))
        bot.edit_message_text("Пәнді таңдаңыз:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif d.startswith("p_"):
        p = d.split("_")
        cat, mode, pan = p[1], p[2], p[3]
        path = f"send_{cat}_{mode}_{pan}"
        potoks = ["gen-1", "gen-2", "gen-3"] if cat == "GENIUS" else ["11", "21", "31", "41", "51", "61", "71"]
        markup = InlineKeyboardMarkup(row_width=3).add(
            *[InlineKeyboardButton(f"{i}-п", callback_data=f"{path}_{i}") for i in potoks]).add(
            InlineKeyboardButton("⬅", callback_data="back"))
        bot.edit_message_text("Поток:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif d.startswith("send_"):
        process_delivery(call)


if __name__ == "__main__":
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] БОТ іске қосылды")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)