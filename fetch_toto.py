import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys
import os

def get_current_toto_teams():
    """Yahoo! totoのHTMLからtoto回数、開催日、13試合の対戦カードを
    固有属性（my-game, poll_v）からピンポイントで抽出します。"""
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
        
        # toto回数の動的パース
        tab_txt_tag = soup.find("span", class_="toto_tab_txtArea")
        if tab_txt_tag:
            tab_text = tab_txt_tag.text.strip()
            num_match = re.search(r'\d+', tab_text)
            if num_match:
                hold_id = int(num_match.group())
                print(f"--- [INFO] HTMLから取得したtoto回数: 第{hold_id}回 ---")
        
        # 開催日の動的パース
        sub_date_tag = soup.find("span", class_="sub_date")
        if sub_date_tag:
            date_text = sub_date_tag.text.strip()
            if "〜" in date_text:
                after_wave = date_text.split("〜")[1].strip()
                match_date = after_wave.split(" ")[0].strip()
                print(f"--- [INFO] HTMLから取得した開催日: {match_date} ---")

        # 13試合のペアを抽出
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
    """【Flashscore用API】チーム名から海外API（API-FOOTBALL）経由で
    欠場者・出場停止選手数を取得します。"""
    
    # toto表記のチーム名から、APIで使われる正確な英語名への対応辞書
    api_team_map = {
        # J1
        "福岡": "Avispa Fukuoka", "神戸": "Vissel Kobe", "鹿島": "Kashima Antlers", 
        "FC東京": "FC Tokyo", "名古屋": "Nagoya Grampus", "広島": "Sanfrecce Hiroshima",
        "札幌": "Consadole Sapporo", "柏": "Kashiwa Reysol", "浦和": "Urawa Red Diamonds",
        "東京V": "Tokyo Verdy", "町田": "FC Machida Zelvia", "川崎F": "Kawasaki Frontale",
        "横浜FM": "Yokohama F. Marinos", "湘南": "Shonan Bellmare", "新潟": "Albirex Niigata",
        "磐田": "Jubilo Iwata", "G大阪": "Gamba Osaka", "C大阪": "Cerezo Osaka",
        "鳥栖": "Sagan Tosu", "京都": "Kyoto Sanga",
        # J2・海外主要
        "清水": "Shimizu S-Pulse", "横浜FC": "Yokohama FC", "長崎": "V-Varen Nagasaki",
        "仙台": "Vegalta Sendai", "山形": "Montedio Yamagata", "千葉": "JEF United Chiba",
        "マンC": "Manchester City", "マンU": "Manchester United", "アーセナル": "Arsenal",
        "リバプール": "Liverpool", "チェルシー": "Chelsea", "トッテナム": "Tottenham Hotspur",
        "フランクフ": "Eintracht Frankfurt", "バイエルン": "Bayern Munich", "ドルトムント": "Borussia Dortmund"
    }
    
    english_name = api_team_map.get(team_name, None)
    if not english_name:
        return 0
        
    if not api_key:
        # APIキーがない間は、安全にテスト用のランダム数値を返す（モックモード）
        import random
        mock_count = random.randint(0, 2)
        print(f"    [API_MOCK] {team_name} -> {english_name} のマッピング成功 (テスト出力: {mock_count}人)")
        return mock_count

    try:
        # RapidAPIのエンドポイントを叩く
        url = f"https://api-football-v1.p.rapidapi.com/v3/injuries?team={english_name}"
        req = urllib.request.Request(url)
        req.add_header("X-RapidAPI-Key", api_key)
        req.add_header("X-RapidAPI-Host", "api-football-v1.p.rapidapi.com")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8', errors='ignore')
            data = json.loads(res_body)
            injuries_list = data.get("response", [])
            count = len(injuries_list)
            print(f"    [API_REAL] {team_name} ({english_name}) のリアル欠場データを取得 -> {count}名")
            return count
    except Exception as e:
        print(f"    [API_ERROR] APIとの通信中にエラーが発生しました(0名として処理): {e}")
        return 0

def get_official_standings():
    """【Yahoo!スポーツ一本化】
    ボットブロックの甘いYahoo!スポーツから全リーグの順位・得点数を安全にスクレイピングします。"""
    raw_data = {}
    urls = {
        "J1": "https://soccer.yahoo.co.jp/jleague/category/j1/standings",
        "J2": "https://soccer.yahoo.co.jp/jleague/category/j2/standings",
        "J3": "https://soccer.yahoo.co.jp/jleague/category/j3/standings",
        "プレミア": "https://soccer.yahoo.co.jp/ws/category/eng/standings",
        "ブンデス": "https://soccer.yahoo.co.jp/ws/category/ger/standings"
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for category, url in urls.items():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', class_='sn-table')
            if not table: 
                continue
                
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) < 7: 
                    continue
                
                try:
                    rank = int(cols[0].text.strip())
                    team_name = cols[1].text.strip().replace(" ", "").replace("　", "")
                    goals = int(cols[6].text.strip()) if len(cols) > 6 else 0
                    
                    raw_data[team_name] = {"rank": rank, "goals": goals}
                except ValueError:
                    continue
        except Exception as e:
            print(f"    [WARN] {category} の順位表パース中にスキップが発生しました: {e}")
            pass
            
    print(f"--- [INFO] Yahoo!スポーツから計 {len(raw_data)} チームの順位情報をキャッシュしました ---")
    return raw_data

def find_stats(toto_name, raw_data):
    """Yahoo!スポーツのチーム名表記とtotoのチーム名表記をマッチングさせます。"""
    alias_map = {
        "札幌": "コンサドーレ札幌", "仙台": "ベガルタ仙台", "いわき": "いわきFC", 
        "水戸": "水戸ホーリーホック", "栃木": "栃木SC", "群馬": "ザスパ群馬", 
        "千葉": "ジェフユナイテッド千葉", "柏": "柏レイソル", "FC東京": "FC東京", "東京V": "東京ヴェルディ",
        "町田": "FC町田ゼルビア", "川崎F": "川崎フロンターレ", "横浜FM": "横浜F・マリノス", "横浜FC": "横浜FC", 
        "湘南": "湘南ベルマーレ", "甲府": "ヴァンフォーレ甲府", "新潟": "アルビレックス新潟", "清水": "清水エスパルス",
        "磐田": "ジュビロ磐田", "藤枝": "藤枝MYFC", "名古屋": "名古屋グランパス", "京都": "京都サンガF.C.", 
        "G大阪": "ガンバ大阪", "C大阪": "セレッソ大阪", "神戸": "ヴィッセル神戸", "岡山": "ファジアーノ岡山", 
        "広島": "サンフレッチェ広島", "徳島": "徳島ヴォルティス", "愛媛": "愛媛FC", "今治": "FC今治", 
        "福岡": "アビスパ福岡", "北九州": "ギラヴァンツ北九州", "鳥栖": "サガン鳥栖", "長崎": "V・ファーレン長崎",
        "熊本": "ロアッソ熊本", "大分": "大分トリニータ", "鹿児島": "鹿児島ユナイテッドFC",
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
        
    print("\n2. 各リーグの最新順位データをYahoo!スポーツから収集中...")
    raw_data = get_official_standings()
    
    # GitHubの保管庫（Secrets）からAPIキーを自動検出
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
        
        print(f"  [試合No.{i:02d}] 欠場者データ検索:")
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
