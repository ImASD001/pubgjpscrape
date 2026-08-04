from flask import Flask, Response, request, render_template_string
import requests
from bs4 import BeautifulSoup
import json
import concurrent.futures
import re

app = Flask(__name__)

# --- 1. Dashboard UI Route (Home) ---
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
        <h1>PUBG Team Scraper API</h1>
        <p>This is your API dashboard. Your other platform can fetch the raw JSON data, or you can view the visualizer.</p>
        
        <div class="box">
            <h3>👁️ View Visualizer (New)</h3>
            <p>View the scraped JSON data rendered as esports team cards.</p>
            <p><strong>Link:</strong> <a href="/visualize">/visualize</a></p>
        </div>

        <div class="box">
            <h3>Fetch All Teams (131 to 178)</h3>
            <p><strong>Endpoint:</strong> <a href="/api/teams" target="_blank">/api/teams</a></p>
            <p style="font-size: 0.9em; color: #888;">*Note: Scraping all 48 pages at once may hit Vercel's 10-second timeout limit.</p>
        </div>

        <div class="box">
            <h3>Fetch Specific Range (Recommended)</h3>
            <p>You can pass start and end parameters in the URL to fetch data in smaller batches.</p>
            <p><strong>Example (131 to 135):</strong> <a href="/api/teams?start=131&end=135" target="_blank">/api/teams?start=131&end=135</a></p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

# --- 2. New Visualization Route ---
@app.route('/visualize')
def visualize():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PUBG Teams Visualizer</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #121212; color: #e0e0e0; }
            .accent { color: #ffaa01; }
            .bg-card { background-color: #1e1e1e; border: 1px solid #333; }
            .scrollbar-hide::-webkit-scrollbar { display: none; }
        </style>
    </head>
    <body class="p-6 md:p-12 font-sans">
        
        <div class="max-w-7xl mx-auto">
            <div class="flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
                <div>
                    <h1 class="text-4xl font-bold accent tracking-wider font-mono">TEAM ROSTERS</h1>
                    <p class="text-gray-400 mt-2">Visualizing scraped JSON data from the API</p>
                </div>
                
                <div class="flex gap-3 items-center bg-[#1a1a1a] p-4 rounded-lg border border-gray-800">
                    <div>
                        <label class="text-xs text-gray-500 block">Start ID</label>
                        <input type="number" id="startId" value="131" class="w-20 bg-black border border-gray-700 rounded px-2 py-1 text-white">
                    </div>
                    <div>
                        <label class="text-xs text-gray-500 block">End ID</label>
                        <input type="number" id="endId" value="135" class="w-20 bg-black border border-gray-700 rounded px-2 py-1 text-white">
                    </div>
                    <button onclick="fetchAndRender()" id="fetchBtn" class="ml-2 bg-[#ffaa01] hover:bg-orange-500 text-black font-bold py-2 px-4 rounded transition">
                        Fetch Teams
                    </button>
                </div>
            </div>

            <div id="status" class="text-blue-400 mb-6 font-mono hidden">Fetching data from API... Please wait.</div>
            
            <div id="teams-container" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Cards will be injected here via JS -->
            </div>
        </div>

        <script>
            async function fetchAndRender() {
                const start = document.getElementById('startId').value;
                const end = document.getElementById('endId').value;
                const container = document.getElementById('teams-container');
                const status = document.getElementById('status');
                const btn = document.getElementById('fetchBtn');

                container.innerHTML = '';
                status.classList.remove('hidden');
                status.innerText = `Scraping IDs ${start} to ${end} from API...`;
                btn.disabled = true;
                btn.classList.add('opacity-50', 'cursor-not-allowed');

                try {
                    const response = await fetch(`/api/teams?start=${start}&end=${end}`);
                    const teams = await response.json();
                    
                    status.classList.add('hidden');
                    
                    if (teams.length === 0) {
                        container.innerHTML = '<p class="text-red-400">No teams found in this range. Pages might be empty or 404.</p>';
                        return;
                    }

                    teams.forEach(team => {
                        const card = document.createElement('div');
                        card.className = 'bg-card rounded-xl p-6 shadow-xl';
                        
                        // Generate players HTML
                        let playersHtml = '';
                        team.players.forEach(p => {
                            playersHtml += `
                                <div class="bg-black/50 p-3 rounded-lg border border-gray-800">
                                    <div class="flex justify-between items-center mb-2">
                                        <span class="font-bold text-lg text-white">${p.name}</span>
                                        <span class="text-xs px-2 py-1 bg-gray-800 rounded text-gray-300">${p.country || 'N/A'}</span>
                                    </div>
                                    <div class="flex justify-between text-sm text-gray-400">
                                        <div><span class="block text-[10px] text-gray-500">KILLS</span> ${p.stats ? p.stats['AVG.KILL'] || '-' : '-'}</div>
                                        <div><span class="block text-[10px] text-gray-500">DMG</span> ${p.stats ? p.stats['AVG.DAMAGE'] || '-' : '-'}</div>
                                        <div><span class="block text-[10px] text-gray-500">TIME</span> ${p.stats ? p.stats['AVG.SURVIVE TIME'] || '-' : '-'}</div>
                                    </div>
                                </div>
                            `;
                        });

                        // Assemble Card
                        card.innerHTML = `
                            <div class="flex justify-between items-start mb-6 border-b border-gray-700 pb-4">
                                <h2 class="text-3xl font-bold uppercase tracking-wide text-white">${team.team_name}</h2>
                            </div>
                            
                            <h3 class="text-sm font-bold text-gray-500 mb-3 tracking-widest">ROSTER</h3>
                            <div class="grid grid-cols-2 gap-3 mb-6">
                                ${playersHtml}
                            </div>
                            
                            <h3 class="text-sm font-bold text-gray-500 mb-2 tracking-widest">LINKS</h3>
                            <div class="flex flex-wrap gap-2">
                                ${team.official_links.map(link => `<a href="${link}" target="_blank" class="text-xs bg-gray-800 hover:bg-gray-700 text-blue-400 px-3 py-1 rounded transition truncate max-w-[200px]">${link.replace('https://', '')}</a>`).join('')}
                            </div>
                        `;
                        container.appendChild(card);
                    });
                    
                } catch (error) {
                    status.innerText = 'Error fetching data from API.';
                    status.classList.add('text-red-500');
                    console.error(error);
                } finally {
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

# --- 3. Scraping Logic (Remains unchanged) ---
def scrape_team(team_id):
    url = f"https://pubgmobile-esports.jp/teams/{team_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code != 200:
            return None
            
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
            return None

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
        
    except Exception:
        return None

# --- 4. JSON API Route (Remains unchanged) ---
@app.route('/api/teams')
def get_teams_api():
    start_id = int(request.args.get('start', 131))
    end_id = int(request.args.get('end', 178))
    
    team_ids = range(start_id, end_id + 1)
    results_list = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(scrape_team, team_ids)
        
        for result in results:
            if result is not None:
                results_list.append(result)
                
    json_output = json.dumps(results_list, indent=4, ensure_ascii=False)
    return Response(json_output, mimetype='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
