import requests
import json
import os
import sys
import base64
from datetime import datetime
from difflib import SequenceMatcher

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL")
MEMORY_FILE = "memoria_partits.json"

# --- PLANTILLA WEB (DISSENY FINAL) ---
INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MatchDay Hub ⚽</title>
<link rel="icon" href="https://fav.farm/⚽">
<style>
    :root { --bg: #111827; --card: #1f2937; --text: #f3f4f6; --accent: #3b82f6; --live: #ef4444; --border: #374151; }
    body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; padding-bottom: 60px; }
    
    .navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; margin-bottom: 30px; scrollbar-width: none; }
    .nav-btn { 
        background: var(--card); color: #9ca3af; padding: 10px 20px; border-radius: 99px; 
        text-decoration: none; border: 1px solid var(--border); white-space: nowrap; font-weight: 600; font-size: 0.9rem; transition: all 0.2s; 
    }
    .nav-btn:hover, .nav-btn.active { background: var(--accent); color: white; border-color: var(--accent); transform: translateY(-2px); }
    
    .sport-section { margin-bottom: 40px; animation: fadeIn 0.5s ease-in; }
    .sport-title { font-size: 1.8rem; font-weight: 800; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; color: white; }
    .sport-icon { background: var(--accent); width: 4px; height: 24px; border-radius: 2px; display: inline-block; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
    
    .card { 
        background: var(--card); border-radius: 16px; overflow: hidden; border: 1px solid var(--border); 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); transition: transform 0.2s; display: flex; flex-direction: column;
    }
    .card:hover { transform: translateY(-3px); border-color: #60a5fa; }
    
    .header { padding: 16px; background: rgba(0,0,0,0.2); border-bottom: 1px solid var(--border); }
    .meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .utc-time { font-family: monospace; color: #94a3b8; font-size: 0.85rem; background: rgba(255,255,255,0.05); padding: 4px 8px; border-radius: 6px; }
    .live-badge { background: var(--live); color: white; padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; animation: pulse 2s infinite; display: flex; align-items: center; gap: 4px; }
    .live-dot { width: 6px; height: 6px; background: white; border-radius: 50%; }
    
    .match-info { text-align: center; padding: 5px 0; }
    .teams { font-size: 1.1rem; font-weight: 700; line-height: 1.4; color: white; }
    .versus { color: #6b7280; font-size: 0.9rem; margin: 0 8px; font-weight: 400; }

    .channels { padding: 16px; display: flex; flex-wrap: wrap; gap: 10px; background: #1a222e; flex-grow: 1; align-content: flex-start; }
    .btn { 
        background: #374151; color: #e5e7eb; padding: 8px 14px; border-radius: 8px; 
        font-size: 0.9rem; cursor: pointer; display: flex; align-items: center; gap: 8px; 
        transition: all 0.2s; user-select: none; border: 1px solid transparent; text-decoration: none; width: 100%; justify-content: flex-start;
    }
    .btn:hover { background: var(--accent); color: white; border-color: #93c5fd; }
    .flag-img { width: 20px; height: 15px; object-fit: cover; border-radius: 3px; box-shadow: 0 1px 2px rgba(0,0,0,0.3); }

    .footer { text-align: center; margin-top: 60px; color: #6b7280; font-size: 0.9rem; border-top: 1px solid var(--border); padding-top: 30px; }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
</style>
</head>
<body>
    <div class="navbar">{{NAVBAR}}</div>
    <div id="content">{{CONTENT}}</div>
    <div class="footer">
        Última actualització: <span style="color:var(--text); font-weight:bold;">{{DATE}}</span><br>
        <small>Hora local detectada automàticament</small>
    </div>

    <script>
        function openLink(el) { 
            try { 
                const raw = el.getAttribute('data-link');
                const url = atob(raw);
                window.open(url, '_blank'); 
            } catch(e){ console.error("Error link", e); } 
        }

        document.querySelectorAll('.utc-time').forEach(el => {
            const raw = el.getAttribute('data-ts');
            if(raw) {
                const d = new Date(raw.replace(' ', 'T')+'Z');
                el.innerText = d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
            }
        });
    </script>
</body>
</html>"""

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://cdn-live.tv/",
    "Origin": "https://cdn-live.tv"
}

def log(msg):
    sys.stderr.write(f"[LOG] {msg}\n")

def get_sport_name(key):
    names = { 
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET 🏀", "NFL": "NFL 🏈", "F1": "FÓRMULA 1 🏎️", 
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊", "Rugby": "RUGBI 🏉",
        "Hockey": "HOQUEI 🏒", "Baseball": "BEISBOL ⚾"
    }
    return names.get(key, key.upper())

def normalize_name(name):
    if not name: return ""
    # Eliminem paraules comunes que causen duplicats
    garbage = ["fc", "cf", "ud", "ca", "sc", "basketball", "football", "club", "real", "city", "united"]
    clean = name.lower()
    for g in garbage:
        clean = clean.replace(f" {g} ", " ").replace(f"{g} ", "").replace(f" {g}", "")
    return clean.strip()

def are_same_match(m1, m2):
    # 1. Mateix esport?
    if m1.get('custom_sport_cat') != m2.get('custom_sport_cat'): return False
    
    # 2. Hora similar? (Marge de 45 minuts)
    try:
        t1 = datetime.strptime(m1['start'], "%Y-%m-%d %H:%M")
        t2 = datetime.strptime(m2['start'], "%Y-%m-%d %H:%M")
        diff_minutes = abs((t1 - t2).total_seconds()) / 60
        if diff_minutes > 45: return False
    except: return False
    
    # 3. Noms semblants?
    h1, a1 = normalize_name(m1.get('homeTeam')), normalize_name(m1.get('awayTeam'))
    h2, a2 = normalize_name(m2.get('homeTeam')), normalize_name(m2.get('awayTeam'))
    
    # Comparem la cadena completa "equip1equip2"
    ratio = SequenceMatcher(None, f"{h1}{a1}", f"{h2}{a2}").ratio()
    return ratio > 0.65 # Si s'assemblen més d'un 65%, són el mateix

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def fetch_cdn_live():
    matches = []
    if not API_URL_CDN:
        return matches
    try:
        resp = requests.get(API_URL_CDN, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json().get("cdn-live-tv", {})
            for sport, event_list in data.items():
                if isinstance(event_list, list):
                    for m in event_list:
                        m['custom_sport_cat'] = sport
                        m['provider'] = 'CDN'
                        matches.append(m)
    except: pass
    return matches

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')

        memory = load_memory()
        new_matches = fetch_cdn_live()
        
        # --- FUSIÓ INTEL·LIGENT (NOU) ---
        for new_m in new_matches:
            found = False
            # Mirem si ja tenim aquest partit a la memòria
            for existing_id, existing_m in memory.items():
                if are_same_match(existing_m, new_m):
                    # FUSIONEM: Afegim els canals nous al partit vell
                    existing_channels = existing_m.get('channels', [])
                    new_channels = new_m.get('channels', [])
                    
                    # Evitem duplicar enllaços exactes
                    existing_urls = {c['url'] for c in existing_channels if 'url' in c}
                    for nc in new_channels:
                        if nc.get('url') not in existing_urls:
                            existing_channels.append(nc)
                    
                    memory[existing_id]['channels'] = existing_channels
                    found = True
                    break
            
            # Si no l'hem trobat, l'afegim com a nou
            if not found:
                slug = f"{new_m.get('custom_sport_cat')}{new_m.get('homeTeam')}{new_m.get('awayTeam')}{new_m.get('start')}"
                gid = str(abs(hash(slug)))
                new_m['gameID'] = gid
                memory[gid] = new_m

        # --- NETEJA I FILTRATGE ---
        clean_memory = {}
        now = datetime.utcnow()
        display_matches = []

        for gid, m in memory.items():
            try:
                if m.get('provider') == 'PPV': continue
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                diff_hours = (now - s_dt).total_seconds() / 3600
                
                if diff_hours < 5.0:
                    clean_memory[gid] = m
                    
                # NOMÉS MOSTREM SI: 1. És futur/recent I 2. TÉ CANALS (Filtre anti-buits)
                if diff_hours < 4.0 and len(m.get('channels', [])) > 0:
                    display_matches.append(m)
            except: pass
        
        save_memory(clean_memory)

        # --- GENERACIÓ HTML ---
        events_by_cat = {}
        for m in display_matches:
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            if 'channels' in m:
                m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        navbar_html = ""
        content_html = ""
        sorted_cats = sorted(events_by_cat.keys())
        
        if not events_by_cat:
            content_html = "<div style='text-align:center; padding:80px; color:#6b7280;'><h2>😴 No hi ha partits disponibles.</h2></div>"

        navbar_html += f'<a href="#" class="nav-btn active">Inici</a>'

        for sport in sorted_cats:
            nice_name = get_sport_name(sport)
            navbar_html += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'
            sport_matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content_html += f'<div id="{sport}" class="sport-section">'
            content_html += f'<div class="sport-title"><span class="sport-icon"></span>{nice_name}</div>'
            content_html += '<div class="grid">'
            
            for m in sport_matches:
                utc = m.get('start')
                is_live = m.get('status', '').lower() == 'live'
                live_tag = '<span class="live-badge"><div class="live-dot"></div> EN VIU</span>' if is_live else ''
                
                btns_html = ""
                for ch in m.get('channels', []):
                    try: link_b64 = base64.b64encode(ch.get('url', '#').encode()).decode()
                    except: link_b64 = ""
                    code = ch.get('channel_code', 'xx').lower()
                    flag = f"https://flagcdn.com/20x15/{code}.png"
                    name = ch.get('channel_name', 'Link')
                    btns_html += f"""<div class="btn" data-link="{link_b64}" onclick="openLink(this)"><img src="{flag}" class="flag-img" onerror="this.style.display='none'"> {name}</div>"""

                content_html += f"""
                <div class="card">
                    <div class="header">
                        <div class="meta"><span class="utc-time" data-ts="{utc}">{utc}</span>{live_tag}</div>
                        <div class="match-info"><div class="teams">{m['homeTeam']} <span class="versus">vs</span> {m['awayTeam']}</div></div>
                    </div>
                    <div class="channels">{btns_html}</div>
                </div>"""
            content_html += "</div></div>"

        final = INTERNAL_TEMPLATE.replace('{{NAVBAR}}', navbar_html)
        final = final.replace('{{CONTENT}}', content_html)
        final = final.replace('{{DATE}}', datetime.now().strftime("%d/%m/%Y %H:%M UTC"))
        
        print(final)

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()