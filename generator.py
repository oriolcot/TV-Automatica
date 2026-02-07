import requests
import json
import os
import shutil
import base64
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL") # https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free
API_URL_PPV = os.environ.get("API_URL_PPV")

MEMORY_FILE = "memoria_partits.json"
BACKUP_FILE = "memoria_backup.json"
TEMPLATE_FILE = "template.html"

# HEADERS CRÍTICS PER ENGANYAR L'API
HEADERS_CDN = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8,ca;q=0.7",
    "Referer": "https://cdn-live.tv/",
    "Origin": "https://cdn-live.tv",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Connection": "keep-alive"
}

def get_sport_name(api_key):
    names = { "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈", "NHL": "HOQUEI (NHL) 🏒", "MLB": "BEISBOL ⚾", "F1": "FÓRMULA 1 🏎️", "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊", "Rugby": "RUGBI 🏉" }
    return names.get(api_key, api_key.upper())

def normalize_name(name):
    if not name: return ""
    garbage = ["fc", "cf", "ud", "ca", "sc", "basketball", "football"]
    clean = name.lower()
    for g in garbage: clean = clean.replace(f" {g} ", " ").replace(f"{g} ", "").replace(f" {g}", "")
    return clean.strip()

def are_same_match(m1, m2):
    if m1.get('custom_sport_cat') != m2.get('custom_sport_cat'): return False
    try:
        t1 = datetime.strptime(m1['start'], "%Y-%m-%d %H:%M")
        t2 = datetime.strptime(m2['start'], "%Y-%m-%d %H:%M")
        if abs((t1 - t2).total_seconds()) / 60 > 60: return False
    except: return False
    h1, a1 = normalize_name(m1.get('homeTeam')), normalize_name(m1.get('awayTeam'))
    h2, a2 = normalize_name(m2.get('homeTeam')), normalize_name(m2.get('awayTeam'))
    return SequenceMatcher(None, f"{h1}{a1}", f"{h2}{a2}").ratio() > 0.60

def fetch_cdn_live():
    print(f"📡 Connectant a CDN-Live: {API_URL_CDN} ...")
    matches = []
    if not API_URL_CDN:
        print("❌ ERROR: API_URL no definida.")
        return matches
    
    try:
        # Peticions amb els headers específics
        resp = requests.get(API_URL_CDN, headers=HEADERS_CDN, timeout=30)
        
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                raw_data = resp.json()
                # Debug: Imprimim les claus que trobem per si han canviat el nom
                print(f"Claus trobades al JSON: {list(raw_data.keys())}")
                
                # Intentem extreure 'cdn-live-tv' o usem el JSON sencer si no hi és
                data = raw_data.get("cdn-live-tv", raw_data)
                
                # Si 'data' no és un diccionari, potser és una llista directament
                if not isinstance(data, dict):
                     print("⚠️ L'estructura no és un diccionari d'esports. Intentant parsejar...")
                
                count = 0
                if isinstance(data, dict):
                    for sport, event_list in data.items():
                        if isinstance(event_list, list):
                            for m in event_list:
                                m['custom_sport_cat'] = sport
                                m['provider'] = 'CDN'
                                matches.append(m)
                                count += 1
                
                print(f"✅ CDN: {count} events extrets.")
                
                if count == 0:
                    print(f"⚠️ ALERTA: JSON vàlid però 0 events. Resposta parcial: {str(resp.text)[:500]}")

            except json.JSONDecodeError:
                print(f"❌ Error decodificant JSON. Resposta text: {resp.text[:200]}")
        else:
            print(f"❌ Error HTTP {resp.status_code}. Possible bloqueig.")
            print(f"Resposta: {resp.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error CRÍTIC CDN: {e}")
        
    return matches

def fetch_ppv_to():
    # Funció simplificada per no distreure, mantenim la lògica anterior
    print("Fetching PPV.to...")
    matches = []
    if not API_URL_PPV: return matches
    try:
        resp = requests.get(API_URL_PPV, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            for cat_group in data.get('streams', []):
                 for s in cat_group.get('streams', []):
                    try:
                        dt = datetime.utcfromtimestamp(int(s.get('starts_at')))
                        start_str = dt.strftime("%Y-%m-%d %H:%M")
                        match = {
                            "homeTeam": s.get('name', '').split(' vs ')[0],
                            "awayTeam": s.get('name', '').split(' vs ')[-1],
                            "start": start_str,
                            "custom_sport_cat": cat_group.get('category_name', 'Other'),
                            "status": "upcoming",
                            "provider": "PPV",
                            "channels": [{"channel_name": "Link", "url": s.get('iframe', '#'), "channel_code": "ppv"}]
                        }
                        matches.append(match)
                    except: continue
    except: pass
    return matches

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def save_memory(data):
    if os.path.exists(MEMORY_FILE):
        try: shutil.copy(MEMORY_FILE, BACKUP_FILE)
        except: pass
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def main():
    try:
        memory = load_memory()
        list_cdn = fetch_cdn_live()
        list_ppv = fetch_ppv_to() # PPV mantingut com a secundari
        
        merged = list_cdn
        # Afegim PPV només si no hi són
        for p_match in list_ppv:
            merged.append(p_match)

        # Processament i IDs
        for m in merged:
            if 'gameID' not in m or m['provider'] == 'PPV':
                slug = f"{m.get('custom_sport_cat')}{m.get('homeTeam')}{m.get('awayTeam')}{m.get('start')}"
                m['gameID'] = str(abs(hash(slug)))
            
            gid = m['gameID']
            if m.get('status', '').lower() == 'finished':
                if gid in memory: del memory[gid]
                continue
            memory[gid] = m

        # Neteja per temps (5 hores)
        final_mem = {}
        now = datetime.utcnow()
        for gid, m in memory.items():
            try:
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                if (now - s_dt).total_seconds() < 5 * 3600:
                    final_mem[gid] = m
            except: pass
        
        save_memory(final_mem)

        # Generació HTML
        events_by_cat = {}
        for m in final_mem.values():
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            if 'channels' not in m: m['channels'] = []
            m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        active_sports = sorted(list(events_by_cat.keys()))
        navbar = ""
        content = ""
        
        if not active_sports:
            content = "<div style='text-align:center; padding:50px; color:#94a3b8;'>😴 Cap partit trobat (Revisa logs API).</div>"
        
        for sport in active_sports:
            nice = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice}</div><div class="grid">'
            for m in matches:
                utc = m.get('start', '')
                is_live = m.get('status', '').lower() == 'live'
                badges = '<span class="live-badge">LIVE</span> ' if is_live else ''
                content += f"""<div class="card"><div class="header"><span class="time" data-utc="{utc}">--:--</span>{badges}<span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span></div><div class="channels">"""
                for ch in m['channels']:
                    name = ch.get('channel_name', 'Link')
                    try: enc = base64.b64encode(ch.get('url', '#').encode('utf-8')).decode('utf-8')
                    except: enc = ""
                    code = ch.get('channel_code', 'xx').lower()
                    img = "https://fav.farm/📺" if code == 'ppv' else f"https://flagcdn.com/24x18/{code}.png"
                    content += f"""<div class="btn" data-link="{enc}" onclick="openLink(this)"><img src="{img}" class="flag-img" onerror="this.style.display='none'"> {name}</div>"""
                content += "</div></div>"
            content += "</div></div>"

        # INSERCIÓ AL TEMPLATE
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f: template = f.read()
            html = template.replace('', navbar)
            html = html.replace('', content)
            
            # Timestamp footer
            html = html.replace('', datetime.now().strftime("%H:%M:%S UTC"))
            
            with open("index.html", "w", encoding="utf-8") as f: f.write(html)
            print("✅ Web generada correctament.")
        else:
            print("❌ ERROR: template.html no trobat.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()