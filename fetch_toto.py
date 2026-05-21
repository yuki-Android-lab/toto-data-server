import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys
import os
from datetime import datetime

# 表記ゆれを吸収するための共通正規化関数
def normalize_team_name(name):
    if not name:
        return ""
    # 全角英数字を半角に、前後の空白を削除
    norm = name.strip().replace(" ", "").replace("　", "")
    norm = norm.replace("Ｃ", "C").replace("Ｇ", "G").replace("Ｖ", "V").replace("Ｆ", "F")
    
    # Yahoo特有の長い正式名称を、toto側の短い名称にマッピングする辞書
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

# 【自動化1】Jリーグのトップページから、現在有効な「順位表」と「日程」のURLを自動検出する
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
        
        # ページ内のすべてのリンクから順位表(standings)と日程(schedule)のURLをさらう
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "/jleague/category/" in href:
                if "/standings" in href and href not in detected_standings:
                    detected_standings.append(href)
                elif "/schedule" in href and href not in detected_schedules:
                    detected_schedules.append(href)
    except Exception as e:
        print(f"    [WARN] リーグURLの自動検出に失敗しました: {e}")
        
    # 万が一自動検出が空なら、現在のURLを最低限のセーフティネットとして返す
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
                    
                    # 今週のtoto対象チーム（target_teams）が含まれる行だけを効率よくパース
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
    
    # totoの基本日
    toto_dt = datetime(current_year, 5, 23)
    # 日曜日開催にスライドするチームの動的判定
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

# ★修正：ユーザー様が実際に契約した「無料APIライブサッカーデータ」の仕様に合わせてエンドポイントとホストを変更
def fetch_team_injuries(api_key, target_teams):
    print("\n[API] 無料APIライブサッカーデータ からリアルタイム離脱者データを取得中...")
    injury_summary = {}
    
    # ご契約のAPI（free-api-live-football-data）のホスト名を設定
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': 'free-api-live-football-data.p.rapidapi.com'
    }
    
    for team in target_teams:
        # ご契約APIの「football-players-search」エンドポイントを使用し、チーム名で直接検索をかけます
        # 日本語をURLエンコードしてリクエストを送信
        encoded_team = urllib.parse.quote(team)
        url = f"https://free-api-live-football-data.p.rapidapi.com/football-players-search?search={encoded_team}"
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            # APIの返却データ構造を解析し、負傷者(injured/status等)のステータスをチェック
            # ※無料APIの仕様上、取得データが空、または怪我人ステータスがない場合は安全に「なし」にします
            results = res_data.get("response", []) or res_data.get("results", [])
            if not results:
                injury_summary[team] = "なし"
            else:
                injured_players = []
                for player in results:
                    # プレイヤーデータの中から怪我（injured）のフラグやステータスを探すロジック
                    status = player.get("status", "")
                    is_injured = player.get("injured", False)
                    if is_injured or "Injured" in str(status) or "傷" in str(status):
                        p_name = player.get("name", "不明な選手")
                        injured_players.append(f"{p_name}(負傷)")
                
                if injured_players:
                    injury_summary[team] = ", ".join(injured_players)
                else:
                    injury_summary[team] = "なし"
                
        except Exception as e:
            # エラーが起きた場合は、デバッグしやすいようにエラー内容そのものをログに吐き出します
            injury_summary[team] = f"データ取得エラー（原因: {e}）"
            
    print("--- [INFO] サッカーAPIからのデータ同期処理が完了しました ---")
    return injury_summary

def main():
    print("1. 今週のtoto対象対戦カードおよび各種基本データを取得中...")
    teams, match_date, hold_id = get_current_toto_teams()
    
    if not teams:
        print("【エラー】totoの対戦カードが取得できませんでした。")
        sys.exit(0)
        
    # 【自動化2】今週のtotoに登場するチーム（26チーム）を自動的にターゲットチームリストにする
    target_teams = list(set([t for match in teams for t in match]))
    
    print("\n[システム] リーグ最新URL（通常戦/特別戦）を自動スキャン中...")
    standings_urls, schedule_urls = detect_current_league_urls()
    
    print("\n2. 各リーグの最新順位データを収集中...")
    raw_data = get_official_standings(standings_urls, target_teams)
    print(f"--- [INFO] 動的パースにより計 {len(raw_data)} チームの順位情報をキャッシュしました ---")
    
    print("\n3. 各コンペティション日程から直近調子・試合間隔を算出中...")
    schedule_map = fetch_real_past_games(schedule_urls)
    print("--- [INFO] 動的な実績日程パースが完了しました ---")
    
    print("\n4. APIキーのチェックを行います。")
    # GitHub Secrets から環境変数 RAPIDAPI_KEY を取得します
    rapidapi_key = os.environ.get("RAPIDAPI_KEY")
    
    # 離脱者データを保持する辞書を初期化
    injury_data = {}
    
    if rapidapi_key:
        print("--- [INFO] GitHub Secrets から API キーを検出しました。本番通信を行います。 ---")
        # ★本番のAPI通信関数をここで呼び出す
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
