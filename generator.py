import requests
import json
import os

# URL de l'API
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

def main():
    try:
        print("Connectant a l'API...")
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        
        # Mirem els partits de futbol (pots afegir bucles per altres esports si vols)
        # Segons l'estructura que vam veure:
        matches = data.get("cdn-live-tv", {}).get("Soccer", [])
        
        content = "#EXTM3U\n"
        
        for match in matches:
            home = match.get('homeTeam', 'Home')
            away = match.get('awayTeam', 'Away')
            img = match.get('homeTeamIMG', '')
            time = match.get('time', '')
            
            # Iterem pels canals
            for channel in match.get('channels', []):
                name = channel.get('channel_name', 'Canal')
                url = channel.get('url', '')
                
                # Creem l'entrada M3U
                # CloudStream fa servir group-title per les categories
                content += f'#EXTINF:-1 tvg-logo="{img}" group-title="Futbol Directe", {time} | {home} vs {away} ({name})\n'
                content += f'{url}\n'

        # Guardem l'arxiu que llegirà la TV
        with open("llista.m3u", "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Llista generada amb {len(matches)} partits.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()