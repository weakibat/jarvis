"""
Jarvis: personal Telegram bot.
Modes (python bot.py <mode>):
digest -> morning summary of football + CS
matches in the next 24h
remind -> ping for matches starting in ~20-30
min (run every 10 min)
news -> gaming/tech headlines from the last
hour that match KEYWORDS (run hourly)
No external dependencies, only the Python standard
library.
"""
import os
import sys
import json
import html
import urllib.request
import datetime as dt
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
TZ = ZoneInfo("Asia/Tehran")
NOW = dt.datetime.now(dt.timezone.utc)
TG_TOKEN = os.environ["TELEGRAM_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
FOOTBALL_KEY = os.environ.get("FOOTBALL_DATA_KEY")
PANDA_KEY = os.environ.get("PANDASCORE_KEY")
# ---------------- EDIT THESE ----------------
# football-data.org free competitions: PL, CL, PD
COMPETITIONS = "PL,CL,PD,SA,BL1,FL1,WC,EC"
ALWAYS_SHOW = {"CL", "WC", "EC"} # always
shown
FAVORITE_TEAMS = [] # e.g.
["Barcelona", "Real Madrid"]; empty = all league
matches
CS_TIERS = {"s", "a"} #
PandaScore tournament tiers to include
CS_FAVORITES = ["Vitality", "FURIA"] #
always shown, any tier
FEEDS = [
"https://feeds.ign.com/ign/news",
"https://www.theverge.com/rss/index.xml",
"https://www.eurogamer.net/feed",
]
KEYWORDS = [
"gta", "ps6", "playstation 6", "switch 2",
"xbox", "nintendo", "steam", "valve",
"counter-strike", "cs2", "nvidia", "rtx",
"amd", "release date", "announced",
"layoffs", "acquires", "acquisition",
"openai", "anthropic", "apple", "iphone",
"elden ring", "hollow knight", "witcher",
"cyberpunk", "battlefield", "call of duty",
]
# --------------------------------------------
def http_json(url, headers=None):
req = urllib.request.Request(url,
headers=headers or {})
with urllib.request.urlopen(req, timeout=30)
as r:
return json.load(r)
def parse_iso(s):
return
dt.datetime.fromisoformat(s.replace("Z",
"+00:00"))
def send(text):
data = json.dumps({
"chat_id": TG_CHAT,
"text": text,
"parse_mode": "HTML",
"disable_web_page_preview": True,
}).encode()
req = urllib.request.Request(
f"https://api.telegram.org/bot{TG_TOKEN}/sendMessa
ge",
data=data,
headers={"Content-Type":
"application/json"},
)
urllib.request.urlopen(req, timeout=30).read()
def football_matches():
if not FOOTBALL_KEY:
return []
d1 = NOW.date().isoformat()
d2 = (NOW +
dt.timedelta(days=2)).date().isoformat()
url = (f"https://api.footballdata.org/v4/matches?dateFrom={d1}&dateTo={d2}"
f"&competitions={COMPETITIONS}")
out = []
for m in http_json(url, {"X-Auth-Token":
FOOTBALL_KEY}).get("matches", []):
code = m["competition"].get("code", "")
home, away = m["homeTeam"]["name"],
m["awayTeam"]["name"]
if code not in ALWAYS_SHOW and
FAVORITE_TEAMS:
if not any(t.lower() in (home +
away).lower() for t in FAVORITE_TEAMS):
continue
out.append({
"start": parse_iso(m["utcDate"]),
"title": f"{home} vs {away}",
"comp": m["competition"]["name"],
"icon": "⚽",
})
return out
def cs_matches():
if not PANDA_KEY:
return []
url =
"https://api.pandascore.co/csgo/matches/upcoming?
sort=begin_at&page[size]=50"
out = []
for m in http_json(url, {"Authorization":
f"Bearer {PANDA_KEY}"}):
if not m.get("begin_at"):
continue
names = [o["opponent"]["name"] for o in
m.get("opponents", []) if o.get("opponent")]
title = " vs ".join(names) if names else
m.get("name", "TBD")
tier = ((m.get("tournament") or
{}).get("tier") or "").lower()
fav = any(f.lower() in title.lower() for f
in CS_FAVORITES)
if tier not in CS_TIERS and not fav:
continue
league = (m.get("league") or
{}).get("name", "")
serie = (m.get("serie") or
{}).get("full_name", "")
out.append({
"start": parse_iso(m["begin_at"]),
"title": title,
"comp": f"{league} {serie}".strip(),
"icon": "🎮",
})
return out
def upcoming(hours):
items = []
for fn in (football_matches, cs_matches):
try:
items += fn()
except Exception as e: # one broken
source shouldn't kill the rest
print(f"{fn.__name__} failed: {e}",
file=sys.stderr)
items = [i for i in items if NOW <= i["start"]
<= NOW + dt.timedelta(hours=hours)]
return sorted(items, key=lambda i: i["start"])
def fmt(i):
t =
i["start"].astimezone(TZ).strftime("%H:%M")
return f'{i["icon"]} <b>
{html.escape(i["title"])}</b>\n {t} (Tehran) ·
{html.escape(i["comp"])}'
def digest():
items = upcoming(24)
if not items:
حبص ریخب �� وت ۲۴ تعاس آینده بازی یمهم ندارم")send
(".برات
return
+ "n\n\:حبص ریخب ️☀ همانرب ۲۴ تعاس آینده")send
"\n\n".join(fmt(i) for i in items))
def remind():
for i in upcoming(1):
mins = (i["start"] - NOW).total_seconds()
/ 60
if 20 < mins <= 30:
+ "n\n\:مین تعاس هگید شروع هشیم ⏰")send
fmt(i))
def feed_items(url):
root = ET.fromstring(urllib.request.urlopen(
urllib.request.Request(url, headers=
{"User-Agent": "jarvis-bot"}), timeout=30).read())
ns = "{http://www.w3.org/2005/Atom}"
for it in root.iter("item"): # RSS
d = it.findtext("pubDate")
if d:
yield it.findtext("title", ""),
it.findtext("link", ""), parsedate_to_datetime(d)
for it in root.iter(ns + "entry"): # Atom
d = it.findtext(ns + "published") or
it.findtext(ns + "updated")
link = it.find(ns + "link")
if d:
yield it.findtext(ns + "title", ""),
(link.get("href") if link is not None else ""),
parse_iso(d)
def news():
seen, hits = set(), []
for url in FEEDS:
try:
for title, link, when in
feed_items(url):
if when.tzinfo is None:
when =
when.replace(tzinfo=dt.timezone.utc)
if NOW - when >
dt.timedelta(minutes=65) or title in seen:
continue
if any(k in title.lower() for k in
KEYWORDS):
seen.add(title)
hits.append((title, link))
except Exception as e:
print(f"feed {url} failed: {e}",
file=sys.stderr)
for title, link in hits[:8]:
send(f'📰 <b>{html.escape(title)}
</b>\n{link}')
if __name__ == "__main__":
mode = sys.argv[1] if len(sys.argv) > 1 else
"digest"
{"digest": digest, "remind": remind, "news":
news}[mode]()
