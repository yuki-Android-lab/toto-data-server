import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys

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
    """【新規追加】アプローチA: APIを叩いて対象チームの欠場者数を取得する関数
    ※APIキーが未設定（None）の場合は、解析用のログを出して仮の数値を返します。"""
    
    # toto表記のチーム名から、海外API（API-FOOTBALL等）で使われる英語名へのマッピングマスタ
    # ここに13試合に登場するチームの対訳を定義していきます
    api_team_map = {
        "福岡": "Avispa Fukuoka",
        "神戸": "Vissel Kobe",
        "鹿島": "Kashima Antlers",
        "FC東京": "FC Tokyo",
        "名古屋": "Nagoya Grampus",
        "広島": "Sanfrecce Hiroshima",
        # 必要に応じて他のチームもここに追加
    }
    
    english_name = api_team_map.get(team_name, None)
    
    if not english_name:
        # マスタに未登録のチーム名の場合はログを出す
        print(f"    [API_MAP_INFO] '{team_name}' の英語マッピング名が未定義です。")
        return 0
        
    if api_key is None:
        # 【テスト用モック処理】まだAPI接続キーがない状態でのシミュレーション
        # 実際にはここに、urllibを使ったAPIへのリクエスト処理が入ります
        import random
        mock_count = random.randint(0, 3) # テスト用に0〜3人をランダム生成
        print(f"    [API_MOCK] {team_name} ({english_name}) の欠場データを問い合わせました -> 検出: {mock_count}名")
        return mock_count

    # TODO: RapidAPI / API-FOOTBALL への実際のリクエスト送信処理（キー設定後に有効化）
    return 0

def get_official_standings():
    raw_data = {}
    urls = {
        "J1": "https://www.jleague.jp/standings/j1/",
        "J2": "https://www.jleague.jp/standings/j2/",
        "J3": "https://www.jleague.jp/standings/j3/",
        "プレミア": "https://soccer.yahoo.co.jp/ws/category/eng/standings",
        "ブンデス": "https://soccer.yahoo.co.jp/ws/category/ger/standings"
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for category, url in urls.items():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            if "jleague" in url:
                table = soup.find('table', class_='table-standings') or soup.find('table')
                if not table: continue
                for row in table.find_all('tr'):
                    if row.find('th'): continue
                    cols = row.find_all('td')
                    if len(cols) < 3: continue
                    try:
                        rank = int(cols[0].text.strip())
                        team_name = cols[1].text.strip().replace(" ", "").replace("　", "")
                        goals = int(cols[6].text.strip()) if len(cols) > 6 else 0
                        raw_data[team_name] = {"rank": rank, "goals": goals}
                    except ValueError:
                        continue
            else:
                table = soup.find('table', class_='sn-table')
                if not table: continue
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) < 7: continue
                    team_name = cols[1].text.strip().replace(" ", "").replace("　", "")
                    raw_data[team_name] = {"rank": int(cols[0].text.strip()), "goals": int(cols[6].text.strip())}
        except Exception:
            pass
    return raw_data

def find_stats(toto_name, raw_data):
    alias_map = {
        "札幌": "コンサドーレ札幌", "仙台": "ベガルタ仙台", "いわき": "いわきＦＣ", 
        "水戸": "水戸ホーリーホック", "栃木": "栃木ＳＣ", "群馬": "ザスパ群馬", 
        "千葉": "ジェフユナイテッド千葉", "柏": "柏レイソル", "FC東京": "ＦＣ東京", "東京V": "東京ヴェルディ",
        "町田": "ＦＣ町田ゼルビア", "川崎F": "川崎フロンターレ", "横浜FM": "横浜Ｆ・マリノス", "横浜FC": "横浜ＦＣ", 
        "湘南": "湘南ベルマーレ", "甲府": "ヴァンフォーレ甲府", "新潟": "アルビレックス新潟", "清水": "清水エスパルス",
        "磐田": "ジュビロ磐田", "藤枝": "藤枝ＭＹＦＣ", "名古屋": "名古屋グランパス", "京都": "京都サンガF.C.", 
        "G大阪": "ガンバ自動", "C大阪": "セレッソ大阪", "神戸": "ヴィッセル神戸", "岡山": "ファジアーノ岡山", 
        "広島": "サンフレッチェ広島", "徳島": "徳島ヴォルティス", "愛媛": "愛媛ＦＣ", "今治": "ＦＣ今治", 
        "福岡": "アビスパ福岡", "北九州": "ギラヴァンツ北九州", "鳥栖": "サガン鳥栖", "長崎": "V・バァーレン長崎",
        "熊本": "ロアッソ熊本", "大分": "大分トリニータ", "鹿児島": "鹿児島ユナイテッドＦＣ",
        "マンU": "マンチェスター・ユナイテッド", "マンC": "マンチェスター・シティ", "フランクフ": "フランクフルト"
    }
    
    search_name = alias_map.get(toto_name, toto_name).replace(" ", "").replace("　", "").lower()
    for official_name, stats in raw_data.items():
        off_name_clean = official_name.lower()
        if (search_name in off_name_clean) or (off_name_clean in search_name):
            return stats["rank"], stats["goals"]
            
    return 10, 15

def main():
    print("1. 今週のtoto対象対戦カードおよび各種基本データを取得中...")
    teams, match_date, hold_id = get_current_toto_teams()
    
    if len(teams) < 13:
        print(f"\n【警告】13試合分のデータを正常に抽出できませんでした。")
        sys.exit(0)
        
    print("\n2. 各リーグの公式サイトから最新順位データを収集中...")
    raw_data = get_official_standings()
    
    print("\n3. 【新規】各チームの欠場者・出場停止データをAPI連携（検証）中...")
    match_list = []
    for i, (home, away) in enumerate(teams, 1):
        display_home = match_date if home == match_date or ("/" in home) else home
        
        home_rank, home_goals = find_stats(display_home, raw_data)
        away_rank, away_goals = find_stats(away, raw_data)
        
        # 欠場者情報の関数を呼び出し
        print(f"  [試合No.{i:02d}] 欠場者データ検索:")
        home_injuries = fetch_missing_players_count(display_home, api_key=None)
        away_injuries = fetch_missing_players_count(away, api_key=None)
        
        match_list.append({
            "holdId": hold_id, 
            "matchNo": i, 
            "homeTeam": display_home, 
            "awayTeam": away,
            "homeRank": home_rank, 
            "awayRank": away_rank,      
            "homeGoalsFor": home_goals, 
            "awayGoalsFor": away_goals,  
            "homeInjuries": home_injuries,  # API（モック）から取得した数値に連動
            "awayInjuries": away_injuries,  # API（モック）から取得した数値に連動
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
