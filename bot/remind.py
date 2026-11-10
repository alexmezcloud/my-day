"""Напоминания «Мой день» в Telegram.

Запускается из GitHub Actions по расписанию (утро и вечер).
Ключ бота и номер чата берутся из секретов репозитория:
TELEGRAM_TOKEN и TELEGRAM_CHAT_ID — в коде их нет.
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

APP_URL = "https://alexmezcloud.github.io/my-day/"
START = dt.date(2026, 11, 9)  # понедельник, неделя 1
MSK = dt.timezone(dt.timedelta(hours=3))

DOW = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MON = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
       "августа", "сентября", "октября", "ноября", "декабря"]

# Ужин по дням недели (0 = понедельник)
DINNER = {
    0: "куриные бёдра + брокколи",
    1: "лосось или скумбрия + мексиканская смесь",
    2: "креветки + стручковая фасоль",
    3: "куриная грудка + кабачок и перец",
    4: "котлеты из индейки + цветная капуста",
    5: "свободный ужин (один раз в неделю)",
    6: "запеканка + рыба",
}
WORKOUT = {
    "А": "жим ногами, жим гантелей лёжа, тяга верхнего блока, румынская тяга, планка",
    "Б": "выпады, жим гантелей сидя, тяга гантели, сгибание ног, подъём ног",
}


def week_no(d):
    return max(1, (d - START).days // 7 + 1)


def gym(d):
    idx = {0: 0, 2: 1, 4: 2}.get(d.weekday())
    if idx is None:
        return None
    return (["А", "Б", "А"] if week_no(d) % 2 else ["Б", "А", "Б"])[idx]


def retinol(d):
    w, k = d.weekday(), week_no(d)
    if k <= 2:
        return w in (1, 5)        # вт, сб
    if k <= 4:
        return w in (0, 2, 4)     # пн, ср, пт
    return (d - START).days % 2 == 0  # через день


def morning(d):
    g = gym(d)
    lines = [f"☀️ Доброе утро! {DOW[d.weekday()].capitalize()}, {d.day} {MON[d.month - 1]} · неделя {week_no(d)}"]
    lines.append(f"🏋️ Зал, тренировка {g}: {WORKOUT[g]}" if g else "🚶 Сегодня без зала — 8 000+ шагов")
    lines.append(f"🍽 Ужин: {DINNER[d.weekday()]}")
    lines.append("🧴 Ретинол вечером: да" if retinol(d) else "🧴 Ретинол вечером: нет")
    todo = {6: "📏 Натощак: вес и талия. В 12:00 — готовка на Пн–Ср",
            2: "🍳 Вечером — готовка на Чт–Пт",
            5: "🛒 Заказать продукты по списку"}.get(d.weekday())
    if todo:
        lines.append(todo)
    lines.append(f"Отметки: {APP_URL}")
    return "\n".join(lines)


def evening(d):
    lines = ["🌙 Через час отбой — ляг до 00:00."]
    lines.append("🧴 Ретинол сегодня: да (гель → сыворотка → крем)" if retinol(d)
                 else "🧴 Ретинол сегодня: нет (гель → крем)")
    if d.weekday() == 5:
        lines.append("📏 Завтра утром натощак — вес и талия")
    lines.append(f"Отметить день: {APP_URL}")
    return "\n".join(lines)


def send(text):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        sys.exit("Нет секрета TELEGRAM_TOKEN или TELEGRAM_CHAT_ID в настройках репозитория")
    data = urllib.parse.urlencode({"chat_id": chat, "text": text,
                                   "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            body = json.load(e)
        except Exception:
            body = {"ok": False, "error_code": e.code, "description": ""}
    if body.get("ok"):
        return
    code, desc = body.get("error_code"), body.get("description", "")
    hint = {
        401: "ключ бота неверный — проверьте секрет TELEGRAM_TOKEN (весь ключ от BotFather, с двоеточием)",
        404: "ключ бота неверный — проверьте секрет TELEGRAM_TOKEN",
        400: "Telegram не знает такой чат — проверьте TELEGRAM_CHAT_ID (только цифры из @userinfobot) и что вы нажали Start у своего бота",
        403: "бот не может вам писать — откройте своего бота и нажмите Start",
    }.get(code, "")
    sys.exit(f"Telegram ответил ошибкой {code}: {desc}. {hint}")


if __name__ == "__main__":
    now = dt.datetime.now(MSK)
    kind = (sys.argv[1] if len(sys.argv) > 1 else "auto").strip()
    if kind == "auto":
        kind = "morning" if now.hour < 15 else "evening"
    text = morning(now.date()) if kind == "morning" else evening(now.date())
    if os.environ.get("DRY_RUN"):
        print(text)
    else:
        send(text)
        print("Отправлено:", kind)
