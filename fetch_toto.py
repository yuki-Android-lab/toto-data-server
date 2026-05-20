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
    
    # マッチング用のJリーグ全地名・チーム名キーワードのリスト
    known_keywords = [
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
            
            for row in soup.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) < 3: 
                    continue
                
                # 行全体のテキストを結合して、どのチームの行かを探す
                row_text = "".join([c.text.strip() for c in cols]).replace(" ", "").replace("　", "")
                
                # 1列目から確実に「順位の数字」を取り出す
                rank_match = re.search(r'\d+', cols[0].text.strip())
                if not rank_match:
                    continue
                rank = int(rank_match.group())
                
                # 既知のキーワードが含まれているかチェック
                detected_team = None
                for kw in known_keywords:
                    # 「ガンバ大阪」なら「G大阪」や「ガンバ」に引っかかるように前方・部分一致も考慮
                    if kw in row_text or (kw == "G大阪" and "ガンバ" in row_text) or (kw == "C大阪" and "セレッソ" in row_text) or (kw == "東京V" and "ヴェルディ" in row_text):
                        detected_team = kw
                        break
                
                if detected_team:
                    # 得点数の抽出：ヘッダー列に依存せず、後ろの方の列（通常は得失点関連）から数字を安全に探す
                    # Yahooの特殊仕様（列数が多くても通常右から5〜7番目付近が得点）
                    goals = 0
                    for col in reversed(cols):
                        val = col.text.strip()
                        if val.isdigit() and int(val) > 0 and int(val) < 150: # 現実的な得点数の範囲
                            goals = int(val)
                            # 得失点差（マイナスがあり得る）や勝点（得点より大きいことが多い）を避けるため、
                            # 最初に見つかった適切な数値を簡易的に採用、または固定位置から
                            break
                    
                    # 確実に得点列（通常インデックス6〜8付近、変則時は後ろから数えて調整）
                    # 今回の100年構想テーブルの構造上、数字が並ぶ中から「得点」に相当する列を抽出
                    try:
                        # 安全策として、数値が入っている列のうち、得点に該当するインデックスを補正
                        num_cols = [int(re.search(r'\d+', c.text).group()) for c in cols if re.search(r'^-?\d+$', c.text.strip())]
                        if len(num_cols) >= 4:
                            # 通常 [順位, 試合数, 勝点, 勝, 分, 敗, 得点, 失点] などの並び
                            # 得点は総得点なので、後ろから3番目か4番目に位置することが多い
                            goals = num_cols[-2] if len(num_cols) > 5 else num_cols[-1]
                    except Exception:
                        pass
                        
                    # キャッシュに保存（特殊大会のWest/Eastで重複しても上書き、または保持）
                    raw_data[detected_team] = {"rank": rank, "goals": goals}
                    
        except Exception as e:
            print(f"    [WARN] {category} の順位表パース中に問題が発生しました: {e}")
            
    print(f"--- [INFO] Yahoo!スポーツから計 {len(raw_data)} チームの順位情報をキャッシュしました ---")
    return raw_data

def find_stats(toto_name, raw_data):
    clean_toto_name = toto_name.replace(" ", "").replace("　", "")
    
    # 完全にキーワード一致で引けるように辞書を検索
    if clean_toto_name in raw_data:
        return raw_data[clean_toto_name]["rank"], raw_data[clean_toto_name]["goals"]
        
    # 部分一致のフォールバック
    for official_name, stats in raw_data.items():
        if clean_toto_name in official_name or official_name in clean_toto_name:
            return stats["rank"], stats["goals"]
            
    # 見つからない場合は中央値付近をセーフティとして返す
    return 5, 12

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
