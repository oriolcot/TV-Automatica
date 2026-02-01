import requests
import json
import os
import shutil
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL")      # Font 1 (CDN-Live)
API_URL_PPV = os.environ.get("API_URL_PPV")  # Font 2 (PPV.to)

MEMORY_FILE = "memoria_partits.json"
BACKUP_FILE = "memoria_backup.json"
TEMPLATE_FILE = "template.html"

# Mapeig de categories de PPV.to cap a les nostres
CAT_MAP_PPV = {
    "Football": "Soccer",
    "American Football": "NFL",
    "Basketball": "NBA",
    "Hockey": "NHL",
    "Baseball": "MLB",
    "Motor Sports": "F1",
    "Fighting": "Boxing",
    "Tennis": "Tennis"
}

def get_sport_name(api_key):
    names = {
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈",
        "NHL": "HOQUEI (NHL) 🏒", "MLB": "BEISBOL ⚾", "F1": "FÓRMULA 1 🏎️",
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊",
        "Rugby": "RUGBI 🏉", "Darts": "DARTS 🎯", "Snooker": "SNOOKER 🎱"
    }
    return names.get(api_key, api_key.upper())

# --- UTILITATS DE FUSIÓ ---

def normalize_name(name):
    """Neteja noms per comparar-los millor"""
    if not name: return ""
    # Treiem FC, CF, paraules comunes i passem a minúscules
    garbage = ["fc", "cf", "ud", "ca", "sc", "basketball", "football"]
    clean = name.lower()
    for g in garbage:
        clean = clean.replace(f" {g} ", " ").replace(f"{g} ", "").replace(f" {g}", "")
    return clean.strip()

def are_same_match(m1, m2):
    """
    Compara dos partits. Retorna True si semblen el mateix.
    Criteri: Mateixa categoria + Mateixa hora (aprox) + Equips semblants.
    """
    # 1. Mateix Esport?
    if m1.get('custom_sport_cat') != m2.get('custom_sport_cat'):
        return False

    # 2. Mateixa Hora? (Marge de 45 minuts per si un posa prèvia)
    try:
        t1 = datetime.strptime(m1['start'], "%Y-%m-%d %H:%M")
        t2 = datetime.strptime(m2['start'], "%Y-%m-%d %H:%M")
        diff_minutes = abs((t1 - t2).total_seconds()) / 60
        if diff_minutes > 45:
            return False
    except:
        return False # Si fallen les dates, no arrisquem

    # 3. Noms semblants? (Fuzzy Logic)
    h1 = normalize_name(m1.get('homeTeam'))
    a1 = normalize_name(m1.get('awayTeam'))
    h2 = normalize_name(m2.get('homeTeam'))
    a2 = normalize_name(m2.get('awayTeam'))

    # Comparem text complet "Home vs Away"
    str1 = f"{h1} {a1}"
    str2 = f"{h2} {a2}"
    
    ratio = SequenceMatcher(None, str1, str2).ratio()
    
    # Si s'assemblen més d'un 70%, és el mateix partit
    return ratio > 0.70

# --- FETCHERS ---

def fetch_cdn_live():
    """Baixa dades de la Font 1 (CDN-Live)"""
    print("Fetching CDN-Live...")
    matches = []
    if not API_URL_CDN: return matches
    
    try:
        resp = requests.get(API_URL_CDN, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json().get("cdn-live-tv", {})
        for sport, event_list in data.items():
            if isinstance(event_list, list):
                for m in event_list:
                    m['custom_sport_cat'] = sport
                    m['provider'] = 'CDN'
                    matches.append(m)
    except Exception as e:
        print(f"Error CDN-Live: {e}")
    return matches

def fetch_ppv_to():
    """Baixa dades de la Font 2 (PPV.to) i les adapta al nostre format"""
    print("Fetching PPV.to...")
    matches = []
    if not API_URL_PPV: return matches

    try:
        resp = requests.get(API_URL_PPV, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        data = resp.json()
        
        # Iterem categories
        for cat_group in data.get('streams', []):
            cat_name = cat_group.get('category_name', 'Other')
            # Mapegem el nom (Ex: 'American Football' -> 'NFL')
            my_cat = CAT_MAP_PPV.get(cat_name)
            
            # Només importem els esports que ens interessen (els que tenim al mapa)
            if not my_cat: continue 

            for s in cat_group.get('streams', []):
                # 1. Convertir Timestamp a String UTC
                ts = s.get('starts_at')
                try:
                    dt = datetime.utcfromtimestamp(int(ts))
                    start_str = dt.strftime("%Y-%m-%d %H:%M")
                    time_str = dt.strftime("%H:%M")
                except:
                    continue # Si no té data, fora

                # 2. Extreure equips del nom "Equip A vs. Equip B"
                full_name = s.get('name', '')
                teams = full_name.split(' vs. ')
                if len(teams) < 2: teams = full_name.split(' v ')
                if len(teams) < 2: teams = full_name.split(' - ')
                
                home = teams[0].strip() if len(teams) > 0 else "Unknown"
                away = teams[1].strip() if len(teams) > 1 else "Unknown"

                # 3. Crear objecte partit compatible
                match = {
                    "gameID": str(s.get('id')),
                    "homeTeam": home,
                    "awayTeam": away,
                    "time": time_str,
                    "start": start_str,
                    "custom_sport_cat": my_cat,
                    "status": "upcoming", # PPV no sol dir 'live', assumim upcoming
                    "provider": "PPV",
                    "channels": [{
                        "channel_name": f"{s.get('tag', 'Link')} (HD)",
                        "channel_code": "ppv", # Codi fictici per icona
                        "url": s.get('iframe', '#'),
                        "priority": 5 # Prioritat mitjana
                    }]
                }
                matches.append(match)
                
    except Exception as e:
        print(f"Error PPV.to: {e}")
    
    return matches

# --- MAIN LOGIC ---

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f: return json.load(f)
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
        
        # 1. Baixar TOTES les dades
        list_cdn = fetch_cdn_live()
        list_ppv = fetch_ppv_to()
        
        # 2. Fusionar PPV dins de CDN (Estratègia: CDN és la base, PPV enriqueix)
        # Primer, convertim la llista CDN en un diccionari temporal per treballar
        merged_pool = list_cdn # Comencem amb CDN
        
        print(f"Fusionant: {len(list_cdn)} partits CDN + {len(list_ppv)} partits PPV...")
        
        for ppv_match in list_ppv:
            found = False
            # Busquem si aquest partit ja existeix a la llista de CDN
            for existing in merged_pool:
                if are_same_match(existing, ppv_match):
                    # BINGO! És el mateix partit.
                    # Afegim el canal de PPV a la llista de canals existent
                    existing['channels'].extend(ppv_match['channels'])
                    found = True
                    break
            
            # Si no l'hem trobat a CDN, l'afegim com a partit nou
            if not found:
                merged_pool.append(ppv_match)

        # 3. Actualitzar Memòria (Persistent)
        current_ids = set()
        for m in merged_pool:
            # Generar ID consistent si no en té (per als de PPV nous)
            if 'gameID' not in m or m['provider'] == 'PPV':
                # ID basat en dades per evitar duplicats futurs
                slug = f"{m['custom_sport_cat']}{m['homeTeam']}{m['awayTeam']}{m['start']}"
                m['gameID'] = str(abs(hash(slug)))
            
            gid = m['gameID']
            
            # Filtre 'Finished'
            if m.get('status', '').lower() == 'finished':
                if gid in memory: del memory[gid]
                continue
                
            memory[gid] = m
            current_ids.add(gid)

        # 4. Neteja per temps (Smart Cleaning)
        final_memory = {}
        now = datetime.utcnow()
        for gid, m in memory.items():
            sport = m.get('custom_sport_cat', 'Other')
            limit = 3.5 if sport == 'NBA' else 2.5 # Hores de vida
            
            try:
                start_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                diff = (now - start_dt).total_seconds()
                if diff > limit * 3600: continue # Massa vell
                if diff < -24 * 3600: continue # Futur error
            except: pass
            
            final_memory[gid] = m

        save_memory(final_memory)

        # 5. Generar HTML
        # Agrupar per esport
        events_by_cat = {}
        for m in final_memory.values():
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            
            # Ordenar canals: Primer Espanyol, després PPV (HD), després la resta
            def channel_score(ch):
                code = ch.get('channel_code', '').lower()
                name = ch.get('channel_name', '').lower()
                if code in ['es', 'mx', 'ar']: return 10
                if 'ppv' in code: return 5 # PPV té prioritat mitjana
                return 1
            
            m['channels'].sort(key=channel_score, reverse=True)
            events_by_cat[cat].append(m)

        # Ordenar Categories i Partits
        active_sports = sorted(list(events_by_cat.keys()))
        
        # HTML Rendering
        navbar = ""
        content = ""
        
        if not active_sports:
            content = "<div style='text-align:center; margin-top:50px;'>😴 No events</div>"
        
        for sport in active_sports:
            nice_name = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'
            
            # Sort matches by time
            matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice_name}</div><div class="grid">'
            
            for m in matches:
                utc = m.get('start', '')
                is_live = m.get('status', '').lower() == 'live'
                # Si té canal PPV, posem badge HD
                has_hd = any('ppv' in ch['channel_code'] for ch in m['channels'])
                
                badges = ""
                if is_live: badges += '<span class="live-badge">LIVE</span> '
                if has_hd: badges += '<span class="live-badge" style="background:#007aff;">HD</span>'

                content += f"""
                <div class="card">
                    <div class="header">
                        <span class="time" data-utc="{utc}">--:--</span>
                        {badges}
                        <span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span>
                    </div>
                    <div class=\"channels\">
                """
                
                for ch in m['channels']:
                    name = ch.get('channel_name', 'Link')
                    url = ch.get('url')
                    code = ch.get('channel_code', 'xx').lower()
                    
                    # Icona especial per PPV
                    if code == 'ppv':
                        img = "https://fav.farm/📺" # Icona TV generica
                    else:
                        img = f"https://flagcdn.com/24x18/{code}.png"

                    content += f"""<a href="{url}" class="btn"><img src="{img}" class="flag-img" onerror="this.style.display='none'"> {name}</a>"""
                
                content += "</div></div>"
            content += "</div></div>"

        # Injectar
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f: template = f.read()
            html = template.replace('', navbar).replace('', content)
            with open("index.html", "w", encoding="utf-8") as f: f.write(html)
            print("Web Generated (Merged CDN + PPV)!")
        else:
            print("Template not found!")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()