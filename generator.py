import requests
import json
import os
import shutil
from datetime import datetime

# MILLORA 8: Seguretat (Secrets)
API_URL = os.environ.get("API_URL")
MEMORY_FILE = "memoria_partits.json"
BACKUP_FILE = "memoria_backup.json"
TEMPLATE_FILE = "template.html"

def get_sport_name(api_key):
    names = {
        "Soccer": "FOOTBALL ⚽", 
        "NBA": "BASKETBALL (NBA) 🏀", 
        "NFL": "NFL 🏈",
        "NHL": "HOCKEY (NHL) 🏒", 
        "MLB": "BASEBALL ⚾", 
        "F1": "FORMULA 1 🏎️",
        "MotoGP": "MOTOGP 🏍️", 
        "Tennis": "TENNIS 🎾", 
        "Boxing": "BOXING 🥊",
        "Rugby": "RUGBY 🏉"
    }
    return names.get(api_key, api_key.upper())

# MILLORA 6: Sistema de Backup de Memòria
def load_memory():
    # Intent 1: Llegir fitxer principal
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error llegint memòria principal: {e}")
            # Intent 2: Llegir backup si el principal falla
            if os.path.exists(BACKUP_FILE):
                try:
                    print("Recuperant des del Backup...")
                    with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return {}
    return {}

def save_memory(data):
    # Abans de guardar, fem còpia de seguretat del que hi ha ara
    if os.path.exists(MEMORY_FILE):
        try:
            shutil.copy(MEMORY_FILE, BACKUP_FILE)
        except:
            pass
    # Guardem el nou
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def clean_old_events(events_dict):
    updated_events = {}
    now = datetime.utcnow()

    for game_id, match in events_dict.items():
        if match.get('status', '').lower() == 'finished':
            continue

        sport = match.get('custom_sport_cat', 'Other')
        # Límits personalitzats per esport
        limit_hours = 4
        if sport == 'Soccer': limit_hours = 2.5
        elif sport == 'NBA': limit_hours = 3.5
        elif sport == 'F1': limit_hours = 3
        
        start_str = match.get('start') 
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                diff = now - start_dt
                
                if diff.total_seconds() > limit_hours * 3600:
                    continue
                if diff.total_seconds() < -24 * 3600: # Filtre errors futurs
                    continue
            except ValueError:
                pass 
        
        updated_events[game_id] = match
    return updated_events

def main():
    try:
        print("1. Loading memory...")
        memory = load_memory()
        
        print("2. Fetching API data...")
        if not API_URL:
            print("ERROR: Falta el secret API_URL")
            return

        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(API_URL, headers=headers, timeout=15)
            data_api = response.json()
            all_sports_api = data_api.get("cdn-live-tv", {})
        except Exception as e:
            print(f"API Error: {e}. Using memory.")
            all_sports_api = {}

        # 3. MERGE
        for sport, event_list in all_sports_api.items():
            if not isinstance(event_list, list): continue
            for match in event_list:
                game_id = match.get('gameID')
                if game_id:
                    if match.get('status', '').lower() == 'finished':
                        if game_id in memory: del memory[game_id]
                        continue
                    match['custom_sport_cat'] = sport 
                    memory[game_id] = match

        # 4. CLEAN & SAVE
        clean_memory = clean_old_events(memory)
        save_memory(clean_memory)
        
        # 5. GENERATE HTML
        events_by_cat = {}
        for game_id, match in clean_memory.items():
            cat = match.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            events_by_cat[cat].append(match)

        for cat in events_by_cat:
            events_by_cat[cat].sort(key=lambda x: x.get('start', '0000-00-00 00:00')) # Ordenem per data real UTC

        active_sports = list(events_by_cat.keys())
        
        # Generar Navbar HTML
        navbar_html = ""
        if not active_sports:
            navbar_html = '<span style="color:#666;">OFFLINE</span>'
        else:
            for sport in active_sports:
                nice_name = get_sport_name(sport)
                navbar_html += f'<a href="#{sport}" class="nav-btn">{nice_name}</a>'

        # Generar Cards HTML
        content_html = ""
        if not active_sports:
            content_html = """
            <div style="text-align:center; margin-top:15vh;">
                <div style="font-size:3em;">😴</div>
                <h3 style="color:#888;">No live events</h3>
            </div>"""

        for sport in active_sports:
            match_list = events_by_cat[sport]
            nice_name = get_sport_name(sport)
            
            content_html += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice_name}</div><div class="grid">'

            for match in match_list:
                home = match.get('homeTeam', 'Home')
                away = match.get('awayTeam', 'Away')
                
                # MILLORA 3: Passem la data 'start' directament (UTC) perquè la processi el JS
                utc_start = match.get('start', '') # Ex: "2026-02-01 20:30"
                
                is_live = match.get('status', '').lower() == 'live'
                live_html = '<span class="live-badge">LIVE</span>' if is_live else ''
                
                content_html += f"""
                <div class="card">
                    <div class="header">
                        <span class="time" data-utc="{utc_start}">--:--</span>{live_html}
                        <span class="teams">{home} vs {away}</span>
                    </div>
                    <div class="channels">
                """
                
                for channel in match.get('channels', []):
                    name = channel.get('channel_name', 'Channel')
                    url = channel.get('url', '#')
                    code = channel.get('channel_code', 'xx').lower()
                    flag = f"https://flagcdn.com/24x18/{code}.png"
                    
                    content_html += f"""<a href="{url}" class="btn"><img src="{flag}" class="flag-img" onerror="this.style.display='none'"> {name}</a>"""
                
                content_html += "</div></div>"
            content_html += '</div></div>'

        # 6. INJECTAR A LA PLANTILLA
        if os.path.exists(TEMPLATE_FILE):
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                template = f.read()
            
            final_html = template.replace('', navbar_html)
            final_html = final_html.replace('', content_html)
            
            with open("index.html", "w", encoding="utf-8") as f:
                f.write(final_html)
            print("SUCCESS: index.html updated from template.")
        else:
            print("ERROR: template.html not found.")

    except Exception as e:
        print(f"Error Global: {e}")

if __name__ == "__main__":
    main()