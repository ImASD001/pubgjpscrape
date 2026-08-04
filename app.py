from flask import Flask, Response, request, render_template_string
import requests
from bs4 import BeautifulSoup
import json
import concurrent.futures
import re

app = Flask(__name__)

# --- 1. Dashboard UI Route ---
@app.route('/')
def home():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PUBG Scraper API</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 2rem; max-width: 800px; margin: auto; background: #121212; color: #e0e0e0; }
            h1 { color: #ffaa01; }
            a { color: #60a5fa; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
            .box { background: #1e1e1e; padding: 1.5rem; border-radius: 8px; border: 1px solid #333; margin-bottom: 1rem; }
        </style>
    </head>
    <body>
        <h1>PUBG Team Scraper is Live!</h1>
        <p>This is your API dashboard. Your other platform can now fetch the raw JSON data using the endpoints below.</p>
        
        <div class="box">
            <h3>Fetch All Teams (131 to 178)</h3>
            <p><strong>Endpoint:</strong> <a href="/api/teams" target="_blank">/api/teams</a></p>
            <p style="font-size: 0.9em; color: #888;">*Note: Scraping 48 pages at once may hit Vercel's 10-second timeout limit.</p>
        </div>

        <div class="box">
            <h3>Fetch Specific Range (Recommended)</h3>
            <p>You can pass start and end parameters in the URL to fetch data in batches and prevent timeouts.</p>
            <p><strong>Example (131 to 140):</strong> <a href="/api/teams?start=131&end=140" target="_blank">/api/teams?start=131&end=140</a></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# --- 2. Scraping Logic ---
def scrape_team(team_id):
    url = f"https://pubgmobile-esports.jp/teams/{team_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return {"team_id": team_id, "error": f"HTTP {response.status_code}"}
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        team_data = {
            "team_name": None,
            "players": [],
            "profile_info": {},
            "official_links": []
        }

        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            if h1.text.strip() != "TEAMS":
                team_data["team_name"] = h1.text.strip()
                break
                
        if not team_data["team_name"]:
            return {"team_id": team_id, "error": "No team name found"}

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

        profile_div = soup.find('div', class_=re.compile(r'style_post__'))
        if profile_div:
            for p in profile_div.find_all('p'):
                text = p.text.strip()
                if '〈' in text and '〉' in text:
                    parts = text.split('〉')
                    if len(parts) >= 2:
                        team_data["profile_info"][parts[0].replace('〈', '').strip()] = parts[1].strip()

        player_links = [p.get("x_account") for p in team_data["players"] if p.get("x_account")]
        for link in soup.find_all('a', target='_blank'):
            href = link.get('href', '')
            if href and href not in player_links:
                if 'pubgmobile' not in href and 'forms.gle' not in href and 'twitter.com/PMJL' not in href:
                    if href not in team_data["official_links"]:
                        team_data["official_links"].append(href)

        return team_data
        
    except Exception as e:
        return {"team_id": team_id, "error": str(e)}

# --- 3. JSON API Route ---
@app.route('/api/teams')
def get_teams_api():
    # Allow URL parameters (e.g., ?start=131&end=140), default to full range
    start_id = int(request.args.get('start', 131))
    end_id = int(request.args.get('end', 178))
    
    team_ids = range(start_id, end_id + 1)
    results_list = []
    
    # Scrape concurrently to beat Vercel's timeout
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(scrape_team, team_ids)
        
        for result in results:
            # We no longer drop failed ones silently, so you can see if the site blocks Vercel
            if result is not None and "error" not in result:
                results_list.append(result)
                
    json_output = json.dumps(results_list, indent=4, ensure_ascii=False)
    
    return Response(json_output, mimetype='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
