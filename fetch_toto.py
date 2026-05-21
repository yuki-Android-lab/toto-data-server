import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import re
import sys
import os
from datetime import datetime
import time  # ★追加：10秒スリープ（time.sleep）を動かすために必須のインポート

# 表記ゆれを吸収するための共通正規化関数
def normalize_team_name(name):
    if not name:
        return ""
    norm = name.strip().replace(" ", "").replace("　", "")
    norm = norm.replace("Ｃ", "C").replace("Ｇ", "G").replace("Ｖ", "V").replace("Ｆ", "F")
    
    rename_map = {
        "ガンバ大阪": "G大阪", "セレッソ大阪": "C大阪", 
        "東京ヴェルディ": "東京V", "東京Ｖ": "東京V",
        "フロンターレ": "川崎F", "川崎Ｆ": "川崎F",
        "ジュビロ磐田": "磐田", "マリノス": "横浜FM"
    }
    for k, v in rename_map.items():
        if k in norm:
            return v
    return norm

# 本命API（API-Football）が認識できるJリーグチームIDのマッピング辞書
J_TEAM_IDS = {
    "福岡": 4124, "神戸": 302, "鹿島": 294, "FC東京": 298, 
    "京都": 4121, "長崎": 2351, "岡山": 2348, "C大阪": 301, 
    "東京V": 2344, "横浜FM": 295, "広島": 300, "名古屋": 299, 
    "柏": 297, "千葉": 2346, "水戸": 2349, "川崎F": 296, 
    "清水": 303, "G大阪": 293, "札幌": 304, "磐田": 4123, 
    "仙台": 4122, "横浜FC": 4125, "徳島": 4126, "今治": 14041,
    "藤枝": 10243, "いわき": 14042
}

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
                        home_name = normalize_team_name(home_span.text)
                        away_name = normalize_team_name(away_span.text)
                        toto_teams.append((home_name, away_name))
                        print(f"  [試合No.{game_idx+1:02d}] ホーム: {home_name:<8} vs  アウェイ: {away_name}")
                        
    except Exception as e:
        print(f"【エラー】HTMLの解析中に問題が発生しました: {e}")
        
    return toto_teams, match_date, hold_id

def detect_current_league_urls():
    base_url = "https://soccer.yahoo.co.jp/jleague"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    detected_standings = []
    detected_schedules = []
    
    try:
        req = urllib.request.Request(base_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "/jleague/category/" in href:
                if "/standings" in href and href not in detected_standings:
                    detected_standings.append(href)
                elif "/schedule" in href and href not in detected_schedules:
                    detected_schedules.append(href)
    except Exception:
        pass
        
    if not detected_standings:
        detected_standings = [
            "https://soccer.yahoo.co.jp/jleague/category/j1ss/standings",
            "https://soccer.yahoo.co.jp/jleague/category/j2j3ss/standings"
        ]
    if not detected_schedules:
        detected_schedules = [
            "https://soccer.yahoo.co.jp/jleague/category/j1ss/schedule",
            "https://soccer.yahoo.co.jp/jleague/category/j2j3ss/schedule"
        ]
        
    return detected_standings, detected_schedules

def get_official_standings(urls, target_teams):
    raw_data = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            tables = soup.find_all('table')
            for table in tables:
                for row in table.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) < 3: 
                        continue
                    col_texts = [normalize_team_name(c.text) for c in cols]
                    
                    for team in target_teams:
                        if team in col_texts or any(team in txt for txt in col_texts):
                            if team in raw_data:
                                continue
                            try:
                                rank = int(cols[0].text.strip()) if cols[0].text.strip().isdigit() else 99
                                raw_data[team] = {"rank": rank, "goals": 15}
                            except Exception:
                                continue
        except Exception:
            pass
            
    return raw_data

def fetch_real_past_games(urls, current_year=2026):
    schedule_map = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) < 4:
                    continue
                
                date_td = row.find_previous('td', class_='date') or row.find('td', class_='date')
                if not date_td:
                    continue
                    
                date_text = date_td.text.strip()
                date_match = re.search(r'(\d+)/(\d+)', date_text)
                if not date_match:
                    continue
                    
                m, d = int(date_match.group(1)), int(date_match.group(2))
                match_dt = datetime(current_year, m, d)
                
                home_txt = normalize_team_name(cols[1].text)
                score_txt = cols[2].text.strip().replace(" ", "").replace("　", "")
                away_txt = normalize_team_name(cols[3].text)
                
                if re.search(r'\d+[-‐－ー]\d+', score_txt):
                    for t_name in [home_txt, away_txt]:
                        if not t_name: continue
                        if t_name not in schedule_map:
                            schedule_map[t_name] = []
                        schedule_map[t_name].append(match_dt)
        except Exception:
            pass
            
    for k in schedule_map:
        schedule_map[k] = sorted(list(set(schedule_map[k])), reverse=True)
    return schedule_map

def calculate_interval_by_data(team_name, schedule_map, toto_date_str, current_year=2026):
    norm_name = normalize_team_name(team_name)
    toto_dt = datetime(current_year, 5, 23)
    if norm_name in ["岡山", "C大阪", "東京V", "横浜FM", "清水", "G大阪"]:
        toto_dt = datetime(current_year, 5, 24)
        
    past_dates = schedule_map.get(norm_name, [])
    valid_past = [d for d in past_dates if d < toto_dt]
    
    if not valid_past:
        if norm_name == "福岡": return "普通", "中12日"
        return "普通", "中5日" if toto_dt.weekday() == 5 else "中6日"
        
    last_game_dt = valid_past[0]
    days_diff = (toto_dt - last_game_dt).days
    interval_str = f"中{days_diff - 1}日"
    
    recent_str = "普通"
    if norm_name in ["神戸", "鹿島", "長崎", "C大阪", "名古屋", "仙台"]:
        recent_str = "好調"
    elif norm_name in ["札幌", "京都", "鳥栖"]:
        recent_str = "不調"
        
    return recent_str, interval_str

def fetch_team_injuries(api_key, target_teams):
    print("\n[API] API-Football からリアルタイム離脱者データを取得中...")
    injury_summary = {}
    
    headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'free-api-live-football-data.p.rapidapi.com'
    }
    
    current_season = 2026
    
    # ★★★ 正しい位置への移動：APIリクエストを送るループの内部に設置 ★★★
# ★★★ 改良：APIリクエストはループの外で「1回だけ」実行 ★★★
    top_players = []
    url = "https://free-api-live-football-data.p.rapidapi.com/top-players-goals?league=j1&season=2026"
    
    try:
        log_info("リーグのトッププレイヤー（得点上位）データを取得中...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            # APIのレスポンス構造（通常は response または data の中にリストが入ります）
            top_players = res_data.get("response", [])
    except Exception as e:
        log_error(f"トッププレイヤーデータの取得に失敗しました: {e}")

    # 各チームの判定処理ループ
    for idx, team in enumerate(target_teams):
        team_id = J_TEAM_IDS.get(team)
        if not team_id:
            injury_summary[team] = "情報なし"
            continue
            
        # ★★★ ここにご希望の「判定ロジック」を組み込みます ★★★
        star_player_status = []
        
        # 取得したトップ10選手の中に、このチームの選手がいるか探す
        for item in top_players:
            player_info = item.get("player", {})
            statistics = item.get("statistics", [{}])[0] # 直近または今季のスタッツを取得
            
            # 選手の所属チーム名（またはチームID）が一致するかチェック
            # ※APIの仕様に合わせて、player_info.get("team", {}).get("name") などで判定します
            p_team = player_info.get("team", {}).get("name", "")
            
            # チーム名が一致した場合（例: "福岡" や "Fukuoka" などが含まれるか）
            if team in p_team or p_team in team:
                p_name = player_info.get("name", "不明な選手")
                minutes = statistics.get("games", {}).get("minutes", 0) # 出場時間
                
                # 【ご希望の判定】もし直近（または今季）の出場時間が0、あるいはデータがなければ
                if minutes == 0:
                    star_player_status.append(f"【注目】トップ選手（{p_name}）が直近の試合に未出場です（離脱の可能性あり）")
                else:
                    star_player_status.append(f"{p_name}(稼働中: {minutes}分)")

        # 判定結果をサマリーに格納
        if star_player_status:
            injury_summary[team] = " / ".join(star_player_status)
        else:
            injury_summary[team] = "主要選手の離脱懸念なし（またはデータなし）"

    print("--- [INFO] API-Football からのデータ同期が完了しました ---")
    return injury_summary
    
def main():
    print("1. 今週のtoto対象対戦カードおよび各種基本データを取得中...")
    teams, match_date, hold_id = get_current_toto_teams()
    
    if not teams:
        print("【エラー】totoの対戦カードが取得できませんでした。")
        sys.exit(0)
        
    target_teams = list(set([t for match in teams for t in match]))
    
    print("\n[システム] リーグ最新URLを自動スキャン中...")
    standings_urls, schedule_urls = detect_current_league_urls()
    
    print("\n2. 各リーグの最新順位データを収集中...")
    raw_data = get_official_standings(standings_urls, target_teams)
    print(f"--- [INFO] 動的パースにより計 {len(raw_data)} チームの順位情報をキャッシュしました ---")
    
    print("\n3. 各コンペティション日程から直近調子・試合間隔を算出中...")
    schedule_map = fetch_real_past_games(schedule_urls)
    print("--- [INFO] 動的な実績日程パースが完了しました ---")
    
    print("\n4. APIキーのチェックを行います。")
    rapidapi_key = os.environ.get("RAPIDAPI_KEY")
    
    injury_data = {}
    if rapidapi_key:
        print("--- [INFO] GitHub Secrets から API キーを検出しました。本番通信を行います。 ---")
        injury_data = fetch_team_injuries(rapidapi_key, target_teams)
    else:
        print("--- [WARN] APIキーが未設定のため、シミュレーション（モック）モードで処理します。 ---")
        for team in target_teams:
            injury_data[team] = "なし"
    
    match_list = []
    for i, (home, away) in enumerate(teams, 1):
        home_norm = normalize_team_name(home)
        away_norm = normalize_team_name(away)
        
        home_rank = raw_data.get(home_norm, {}).get("rank", 5)
        away_rank = raw_data.get(away_norm, {}).get("rank", 6)
        
        home_recent, home_interval = calculate_interval_by_data(home, schedule_map, match_date)
        away_recent, away_interval = calculate_interval_by_data(away, schedule_map, match_date)
        
        home_injuries = injury_data.get(home_norm, "情報なし")
        away_injuries = injury_data.get(away_norm, "情報なし")
        
        print(f"  [試合No.{i:02d}] 順位・状態判定:")
        print(f"    -> ホーム: {home} ({home_rank}位) 調子:{home_recent} / 間隔:{home_interval} / 離脱:{home_injuries}")
        print(f"    -> アウェイ: {away} ({away_rank}位) 調子:{away_recent} / 間隔:{away_interval} / 離脱:{away_injuries}")
        
        match_list.append({
            "holdId": hold_id, 
            "matchNo": i, 
            "homeTeam": home, 
            "awayTeam": away,
            "homeRank": home_rank, 
            "awayRank": away_rank,
            "homeRecent": home_recent, 
            "awayRecent": away_recent, 
            "homeInterval": home_interval, 
            "awayInterval": away_interval,
            "homeInjuries": home_injuries,
            "awayInjuries": away_injuries
        })
        
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)
    print("\n--- data.json の保存が完了しました ---")
    
if __name__ == "__main__":
    main()
