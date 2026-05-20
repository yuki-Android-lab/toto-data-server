import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys
import os

def get_current_toto_teams():
    toto_teams = []
    match_date = "5/23" 
    hold_id = 0         
    url = "https://toto.yahoo.co.jp/toto/?holdId=1631"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        
        tab_txt_tag = soup.find("span", class_="toto_tab_txtArea")
        if tab_txt_tag:
            tab_text = tab_txt_tag.text.strip()
            num_match = re.search(r'\d+', tab_text)
            if num_match:
                hold_id = int(num_match.group())
                print(f"--- [INFO] HTMLから取得したtoto回数: 第{hold_id}回 ---")
        
        sub_date_tag = soup.find("span", class_="sub_date")
        if sub_date_tag:
            date_text = sub_date_tag.text.strip()
            if "〜" in date_text:
                after_wave = date_text.split("〜")[1].strip()
                match_date = after_wave.split(" ")[0].strip()
                print(f"--- [INFO] HTMLから取得した開催日: {match_date} ---")

        for game_idx in range(13):
            row = soup.find("tr", attrs={"my-game": str(game_idx)})
            if row:
                home_td = row.find("td", attrs={"class": "team_btn", "poll_v": "1"})
                away_td = row.find("td", attrs={"class": "team_btn", "poll_v": "2"})
                
                if home_td and away_td:
                    home_span = home_td.find("span")
                    away_span = away_td.find("span")
                    
                    if home_span and away_span:
                        home_name = home_span.text.strip().replace(" ", "").replace("　", "")
                        away_name = away_span.text.strip().replace(" ", "").replace("　", "")
                        toto_teams.append((home_name, away_name))
                        print(f"  [試合No.{game_idx+1:02d}] ホーム: {home_name:<8} vs  アウェイ: {away_name}")
                        
    except Exception as e:
        print(f"【エラー】HTMLの解析中に問題が発生しました: {e}")
        
    return toto_teams, match_date, hold_id

def fetch_missing_players_count(team_name, api_key=None):
    api_team_map = {
        "福岡": "Avispa Fukuoka", "神戸": "Vissel Kobe", "鹿島": "Kashima Antlers", 
        "FC東京": "FC Tokyo", "名古屋": "Nagoya Grampus", "広島": "Sanfrecce Hiroshima",
        "札幌": "Consadole Sapporo", "柏": "Kashiwa Reysol", "浦和": "Urawa Red Diamonds",
        "東京V": "Tokyo Verdy", "町田": "FC Machida Zelvia", "川崎F": "Kawasaki Frontale",
        "横浜FM": "Yokohama F. Marinos", "湘南": "Shonan Bellmare", "新潟": "Albirex Niigata",
        "磐田": "Jubilo Iwata", "G大阪": "Gamba Osaka", "C大阪": "Cerezo Osaka",
        "鳥栖": "Sagan Tosu", "京都": "Kyoto Sanga",
        "清水": "Shimizu S-Pulse", "横浜FC": "Yokohama FC", "長崎": "V-Varen Nagasaki",
        "仙台": "Vegalta Sendai", "山形": "Montedio Yamagata", "千葉": "JEF United Chiba",
        "水戸": "Mito HollyHock", "徳島": "Tokushima Vortis",
        "今治": "FC Imabari", "藤枝": "Fujieda MYFC", "いわき": "Iwaki FC", "岡山": "Fagiano Okayama",
        "マンC": "Manchester City", "マンU": "Manchester United", "アーセナル": "Arsenal",
        "リバプール": "Liverpool", "チェルシー": "Chelsea", "トッテナム": "Tottenham Hotspur",
        "フランクフ": "Eintracht Frankfurt", "バイエルン": "Bayern Munich", "ドルトムント": "Borussia Dortmund"
    }
    
    english_name = api_team_map.get(team_name, None)
    if not english_name:
        return 0
        
    if not api_key:
        import random
        return random.randint(0, 2)

    try:
        url = f"https://api-football-v1.p.rapidapi.com/v3/injuries?team={english_name}"
        req = urllib.request.Request(url)
        req.add_header("X-RapidAPI-Key", api_key)
        req.add_header("X-RapidAPI-Host", "api-football-v1.p.rapidapi.com")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8', errors='ignore')
            data = json.loads(res_body)
            injuries_list = data.get("response", [])
            return len(injuries_list)
    except Exception:
        return 0

def get_official_standings():
    raw_data = {}
    urls = {
        "J1": "https://soccer.yahoo.co.jp/jleague/category/j1ss/standings",
        "J2": "https://soccer.yahoo.co.jp/jleague/category/j2/standings",
        "J3": "https://soccer.yahoo.co.jp/jleague/category/j3/standings",
        "プレミア": "https://soccer.yahoo.co.jp/ws/category/eng/standings",
        "ブンデス": "https://soccer.yahoo.co.jp/ws/category/ger/standings"
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    target_teams = [
        "福岡", "神戸", "鹿島", "FC東京", "名古屋", "広島", "札幌", "柏", "浦和", 
        "東京V", "町田", "川崎F", "横浜FM", "湘南", "新潟", "磐田", "G大阪", "C大阪", 
        "鳥栖", "京都", "清水", "横浜FC", "長崎", "仙台", "山形", "千葉", "岡山", "水戸",
        "徳島", "今治", "藤枝", "いわき", "マンC", "マンU", "アーセナル", "リバプール"
    ]
    
    for category, url in urls.items():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 各テーブルごとにヘッダー（th）を解析して「得点」列の位置を特定する
            tables = soup.find_all('table')
            for table in tables:
                # ヘッダー行を探す
                headers_tr = table.find('tr')
                goals_idx = -1
                if headers_tr:
                    ths = [th.text.strip() for th in headers_tr.find_all(['th', 'td'])]
                    for idx, th_text in enumerate(ths):
                        if '得点' in th_text or '得' in th_text:
                            goals_idx = idx
                            break
                
                # テーブル内のデータ行をパース
                for row in table.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) < 3: 
                        continue
                    
                    row_text = "".join([c.text.strip() for c in cols]).replace(" ", "").replace("　", "")
                    
                    for team in target_teams:
                        is_match = False
                        if team in row_text:
                            is_match = True
                        elif team == "G大阪" and "ガンバ" in row_text:
                            is_match = True
                        elif team == "C大阪" and "セレッソ" in row_text:
                            is_match = True
                        elif team == "東京V" and "ヴェルディ" in row_text:
                            is_match = True
                        elif team == "横浜FM" and "マリノス" in row_text:
                            is_match = True
                        elif team == "マンC" and "マンチェスター・ｃ" in row_text.lower():
                            is_match = True
                        elif team == "マンU" and "マンチェスター・ｕ" in row_text.lower():
                            is_match = True

                        if is_match:
                            try:
                                # 1. 順位の確実な抽出（1列目から数字のみを抜く）
                                rank_text = cols[0].text.strip()
                                rank_match = re.search(r'\d+', rank_text)
                                rank = int(rank_match.group()) if rank_match else 99
                                
                                # 2. 得点数の確実な抽出
                                goals = 0
                                if goals_idx != -1 and goals_idx < len(cols):
                                    # ヘッダーから特定した列をピンポイントで取得
                                    g_txt = cols[goals_idx].text.strip()
                                    if g_txt.isdigit():
                                        goals = int(g_txt)
                                else:
                                    # ヘッダーがない場合のセーフティ：数字のみの列から末尾に近い適切な位置を探索
                                    num_cols = [int(c.text.strip()) for c in cols if c.text.strip().isdigit()]
                                    if len(num_cols) >= 5:
                                        goals = num_cols[-2] # 標準的な総得点の位置
                                    elif len(num_cols) >= 2:
                                        goals = num_cols[-1]
                                
                                # データを保存（すでに格納されていても、より新しいグループテーブルのデータ等で正しく上書き、あるいは保持）
                                raw_data[team] = {"rank": rank, "goals": goals}
                            except Exception:
                                continue
                            break
                            
        except Exception as e:
            print(f"    [WARN] {category} の順位表パース中に問題が発生しました: {e}")
            
    print(f"--- [INFO] Yahoo!スポーツから計 {len(raw_data)} チームの順位情報をキャッシュしました ---")
    return raw_data

def find_stats(toto_name, raw_data):
    clean_toto_name = toto_name.replace(" ", "").replace("　", "")
    
    if clean_toto_name in raw_data:
        return raw_data[clean_toto_name]["rank"], raw_data[clean_toto_name]["goals"]
        
    for official_name, stats in raw_data.items():
        if clean_toto_name in official_name or official_name in clean_toto_name:
            return stats["rank"], stats["goals"]
            
    import random
    return random.randint(6, 12), random.randint(14, 25)

def main():
    print("1. 今週のtoto対象対戦カードおよび各種基本データを取得中...")
    teams, match_date, hold_id = get_current_toto_teams()
    
    if len(teams) < 13:
        print(f"\n【警告】13試合分のデータを正常に抽出できませんでした。")
        sys.exit(0)
        
    print("\n2. 各リーグの最新順位データをYahoo!スポーツから収集中...")
    raw_data = get_official_standings()
    
    api_key = os.environ.get("RAPIDAPI_KEY", None)
    if api_key:
        print("\n3. GitHub SecretsからAPIキーを検出しました。本番通信を行います。")
    else:
        print("\n3. APIキーが未設定のため、シミュレーション（モック）モードで処理します。")
        
    match_list = []
    for i, (home, away) in enumerate(teams, 1):
        display_home = match_date if home == match_date or ("/" in home) else home
        
        home_rank, home_goals = find_stats(display_home, raw_data)
        away_rank, away_goals = find_stats(away, raw_data)
        
        print(f"  [試合No.{i:02d}] 順位・欠場者マッピング確認:")
        print(f"    -> ホーム: {display_home} ({home_rank}位 / 得点:{home_goals})")
        print(f"    -> アウェイ: {away} ({away_rank}位 / 得点:{away_goals})")
        
        home_injuries = fetch_missing_players_count(display_home, api_key=api_key)
        away_injuries = fetch_missing_players_count(away, api_key=api_key)
        
        match_list.append({
            "holdId": hold_id, 
            "matchNo": i, 
            "homeTeam": display_home, 
            "awayTeam": away,
            "homeRank": home_rank, 
            "awayRank": away_rank,      
            "homeGoalsFor": home_goals, 
            "awayGoalsFor": away_goals,  
            "homeInjuries": home_injuries,  
            "awayInjuries": away_injuries,  
            "weather": "晴",
            "homeCompatibility": "拮抗", 
            "homeTactics": "カウンター", 
            "awayTactics": "ポゼッション",
            "homeRecent": "普通", 
            "awayRecent": "好調", 
            "homeInterval": "中6日", 
            "awayInterval": "中3日",
            "homeRainWinRate": "45%", 
            "awayRainWinRate": "55%"
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)
    print("\n--- data.json の保存が完了しました ---")

if __name__ == "__main__":
    main()
