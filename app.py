from flask import Flask, Response
import requests
from bs4 import BeautifulSoup
import json
import concurrent.futures

app = Flask(__name__)

def scrape_team(team_id):
    url = f"https://pubgmobile-esports.jp/teams/{team_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        team_data = {
            "team_name": None,
            "players": [],
            "profile_info": {},
            "official_links": []
        }

        # Extract Team Name
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            if h1.text.strip() != "TEAMS":
                team_data["team_name"] = h1.text.strip()
                break
                
        if not team_data["team_name"]:
            return None

        # Extract Players
        import re
        names = soup.find_all('h3', class_=re.compile(r'style_playerProfile__name__'))
        for name_tag in names:
            player_dict = {"name": name_tag.text.strip()}
            header_wrap = name_tag.parent.parent
            
            country_tag = header_wrap.find('div', class_=re.compile(r'style_playerProfile__country'))
            if country_tag: 
                player_dict["country"] = country_tag.text.strip()
                
            x_tag = header_wrap.find('a', href=re.compile(r'x\.com'))
            if x_tag: 
                player_dict["x_account"] = x_tag['href']
                
            main_card = header_wrap.parent.parent
            stats = {}
            stat_titles = main_card.find_all('p', class_=re.compile(r'style_statTitle'))
            stat_values = main_card.find_all('p', class_=re.compile(r'style_statValue'))
            
            for t, v in zip(stat_titles, stat_values):
                stats[t.text.strip()] = v.text.strip()
            
            if stats:
                player_dict["stats"] = stats
                
            team_data["players"].append(player_dict)

        # Extract Profile Info
        profile_div = soup.find('div', class_=re.compile(r'style_post__'))
        if profile_div:
            for p in profile_div.find_all('p'):
                text = p.text.strip()
                if '〈' in text and '〉' in text:
                    parts = text.split('〉')
                    if len(parts) >= 2:
                        team_data["profile_info"][parts[0].replace('〈', '').strip()] = parts[1].strip()

        # Extract Official Links
        player_links = [p.get("x_account") for p in team_data["players"] if p.get("x_account")]
        for link in soup.find_all('a', target='_blank'):
            href = link.get('href', '')
            if href and href not in player_links:
                if 'pubgmobile' not in href and 'forms.gle' not in href and 'twitter.com/PMJL' not in href:
                    if href not in team_data["official_links"]:
                        team_data["official_links"].append(href)

        return team_data
        
    except Exception:
        return None

@app.route('/')
def get_teams():
    start_id = 131
    end_id = 178
    team_ids = range(start_id, end_id + 1)
    valid_teams = []
    
    # Use ThreadPoolExecutor to scrape multiple pages at once.
    # This bypasses the need for delays and finishes in a few seconds.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(scrape_team, team_ids)
        
        for result in results:
            if result is not None:
                valid_teams.append(result)
                
    # Format the output as a pure JSON array/object exactly as requested
    json_output = json.dumps(valid_teams, indent=4, ensure_ascii=False)
    
    # Return as application/json so other platforms can consume it directly
    return Response(json_output, mimetype='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)