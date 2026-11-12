# Jarvis bot
# python bot.py digest | remind | news
import os
import sys
import json
import html
import urllib.request as ur
import datetime as dt
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
TZ = ZoneInfo("Asia/Tehran")
UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC)
HOUR = dt.timedelta(hours=1)
TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]
FB_KEY = os.environ.get("FOOTBALL_DATA_KEY")
PS_KEY = os.environ.get("PANDASCORE_KEY")
# ---- SETTINGS ----
# Leagues: PL CL PD SA BL1 FL1 WC EC
LEAGUES = "PL,CL,PD,SA,BL1,FL1,WC,EC"
# Always shown
ALWAYS = {"CL", "WC", "EC"}
# Favorite teams, empty = all
TEAMS = []
# CS tiers
TIERS = {"s", "a"}
# CS teams always shown
CS_TEAMS = ["Vitality", "FURIA"]
FEEDS = [
"https://feeds.ign.com/ign/news",
"https://www.theverge.com/rss/index.xml",
"https://www.eurogamer.net/feed",
]
WORDS = [
"gta", "ps6", "playstation 6",
"switch 2", "xbox", "nintendo",
"steam", "valve", "counter-strike",
"cs2", "nvidia", "rtx", "amd",
"release date", "announced",
"layoffs", "acquires", "openai",
"anthropic", "apple", "iphone",
"elden ring", "hollow knight",
"witcher", "cyberpunk",
"battlefield", "call of duty",
]
# ---- END SETTINGS ----
def get_json(url, headers):
req = ur.Request(url, headers=headers)
with ur.urlopen(req, timeout=30) as r:
return json.load(r)
def iso(s):
s = s.replace("Z", "+00:00")
return dt.datetime.fromisoformat(s)
def send(text):
body = {
"chat_id": CHAT,
"text": text,
"parse_mode": "HTML",
"disable_web_page_preview": True,
}
url = "https://api.telegram.org/bot"
url = url + TOKEN + "/sendMessage"
req = ur.Request(
url,
data=json.dumps(body).encode(),
headers={
"Content-Type": "application/json"
},
)
ur.urlopen(req, timeout=30).read()
def football():
if not FB_KEY:
return []
d1 = NOW.date().isoformat()
end = NOW + dt.timedelta(days=2)
d2 = end.date().isoformat()
url = (
"https://api.football-data.org"
"/v4/matches?dateFrom=" + d1
+ "&dateTo=" + d2
+ "&competitions=" + LEAGUES
)
hdr = {"X-Auth-Token": FB_KEY}
data = get_json(url, hdr)
out = []
for m in data.get("matches", []):
comp = m["competition"]
code = comp.get("code", "")
home = m["homeTeam"]["name"]
away = m["awayTeam"]["name"]
names = (home + away).lower()
if code not in ALWAYS and TEAMS:
if not any(
t.lower() in names
for t in TEAMS
):
continue
out.append({
"start": iso(m["utcDate"]),
"title": home + " vs " + away,
"comp": comp["name"],
"icon": "⚽",
})
return out
def cs():
if not PS_KEY:
return []
url = (
"https://api.pandascore.co"
"/csgo/matches/upcoming"
"?sort=begin_at&page[size]=50"
)
hdr = {"Authorization": "Bearer " + PS_KEY}
out = []
for m in get_json(url, hdr):
if not m.get("begin_at"):
continue
opps = m.get("opponents", [])
names = [
o["opponent"]["name"]
for o in opps
if o.get("opponent")
]
if names:
title = " vs ".join(names)
else:
title = m.get("name", "TBD")
tour = m.get("tournament") or {}
tier = (tour.get("tier") or "").lower()
low = title.lower()
fav = any(
f.lower() in low
for f in CS_TEAMS
)
if tier not in TIERS and not fav:
continue
lg = m.get("league") or {}
se = m.get("serie") or {}
comp = lg.get("name", "")
comp = comp + " " + se.get("full_name",
"")
out.append({
"start": iso(m["begin_at"]),
"title": title,
"comp": comp.strip(),
"icon": "🎮",
})
return out
def upcoming(hours):
items = []
for fn in (football, cs):
try:
items += fn()
except Exception as e:
print(fn.__name__, e, file=sys.stderr)
end = NOW + hours * HOUR
items = [
i for i in items
if NOW <= i["start"] <= end
]
return sorted(items, key=lambda i: i["start"])
def fmt(i):
t = i["start"].astimezone(TZ)
t = t.strftime("%H:%M")
title = html.escape(i["title"])
comp = html.escape(i["comp"])
line1 = i["icon"] + " <b>" + title + "</b>"
line2 = " " + t + " (Tehran) - " + comp
return line1 + "\n" + line2
def digest():
items = upcoming(24)
if not items:
send(" بازی مهمی نداری 😴 (".صبح بخیر
return
text = "\n\n".join(fmt(i) for i in items)
send(" برنامه ۲۴ ساعت آینده ☀️ صبح بخیر :\n\n" + text)
def remind():
for i in upcoming(1):
secs = (i["start"] - NOW).total_seconds()
mins = secs / 60
if 20 < mins <= 30:
msg = "⏰ ":نیم ساعت دیگه شروع میشه
send(msg + "\n\n" + fmt(i))
def feed_items(url):
req = ur.Request(
url,
headers={"User-Agent": "jarvis"},
)
raw = ur.urlopen(req, timeout=30).read()
root = ET.fromstring(raw)
ns = "{http://www.w3.org/2005/Atom}"
for it in root.iter("item"):
d = it.findtext("pubDate")
if d:
yield (
it.findtext("title", ""),
it.findtext("link", ""),
parsedate_to_datetime(d),
)
for it in root.iter(ns + "entry"):
d = it.findtext(ns + "published")
d = d or it.findtext(ns + "updated")
link = it.find(ns + "link")
href = ""
if link is not None:
href = link.get("href")
if d:
title = it.findtext(ns + "title", "")
yield title, href, iso(d)
def news():
seen = set()
hits = []
maxage = dt.timedelta(minutes=65)
for url in FEEDS:
try:
for title, link, when in
feed_items(url):
if when.tzinfo is None:
when =
when.replace(tzinfo=UTC)
if NOW - when > maxage:
continue
if title in seen:
continue
low = title.lower()
if any(k in low for k in WORDS):
seen.add(title)
hits.append((title, link))
except Exception as e:
print("feed failed", e,
file=sys.stderr)
for title, link in hits[:8]:
t = html.escape(title)
send("📰 <b>" + t + "</b>\n" + link)
if __name__ == "__main__":
mode = "digest"
if len(sys.argv) > 1:
mode = sys.argv[1]
modes = {
"digest": digest,
"remind": remind,
"news": news,
}
modes[mode]()
