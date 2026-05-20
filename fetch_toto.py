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
        mock_count = random.randint(0, 2)
        print(f"    [API_MOCK] {team_name} -> {english_name} のマッピング成功 (テスト出力: {mock_count}人)")
        return mock_count

    try:
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
    """【徹底デバッグ版】
    HTMLの中身を力技で画面に露出させ、原因を完全に突き止めます。"""
    raw_data = {}
    urls = {
        "J1": "https://soccer.yahoo.co.jp/jleague/category/j1/standings",
        "プレミア": "https://soccer.yahoo.co.jp/ws/category/eng/standings",
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for category, url in urls.items():
        print(f"\n==== [DEBUG START] {category} ページの解析テスト ====")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # 証拠出し①: そもそもテーブルタグがページ内に何個あるか出す
            all_tables = soup.find_all('table')
            print(f"  [DEBUG ①] ページ内に存在する <table> タグの総数: {len(all_tables)}個")
            
            # 証拠出し②: ページ内にあるテーブルのクラス名を全部リストアップする
            for idx, t in enumerate(all_tables, 1):
                print(f"    テーブルNo.{idx} のクラス名: {t.get('class')}")
                
            # 証拠出し③: 最初のテーブルの、最初の2行分だけテキストを無理やり出してみる
            if all_tables:
                print(f"  [DEBUG ③] テーブルNo.1 の中身（先頭の一部）:")
                rows = all_tables[0].find_all('tr')
                for r_idx, r in enumerate(rows[:3]):
                    print(f"    行.{r_idx} の生テキスト: {r.text.strip().replace(chr(10), ' | ')}")
                    
            # 従来のパース処理（どこで弾かれているか追跡）
            if "jleague" in url:
                table = soup.find('table', class_='yjStTable') or soup.find('table')
                if not table:
                    print("  [DEBUG ERROR] Jリーグ表テーブルの特定に失敗")
                    continue
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) < 3: continue
                    try:
                        rank_text = cols[0].text.strip()
                        team_name = cols[1].text.strip().replace(" ", "").replace("　", "")
                        team_name = re.sub(r'\d+位', '', team_name)
                        goals = int(cols[6].text.strip()) if len(cols) > 6 else 0
                        raw_data[team_name] = {"rank": 1, "goals": goals} # デバッグ用に仮
                    except Exception as ex:
                        print(f"    [DEBUG ROW ERROR] 行パース失敗: {ex}")
            else:
                table = soup.find('table', class_='sn-table')
                if not table:
                    print("  [DEBUG ERROR] 海外表テーブルの特定に失敗")
                    continue
                    
        except Exception as e:
            print(f"  [DEBUG FATAL ERROR] 通信または解析自体がクラッシュ: {e}")
            
    print(f"\n--- [DEBUG END] キャッシュできた総数: {len(raw_data)} チーム ---")
    return raw_data

def find_stats(toto_name, raw_data):
    return 5, 20 # デバッグ中は一旦固定値でスルーさせます

def main():
    print("1. 今週のtoto対象対戦カードデータを取得中...")
    teams, match_date, hold_id = get_current_toto_teams()
    
    print("\n2. デバッグ用・順位表データのスクレイピング検証...")
    raw_data = get_official_standings()
    
    match_list = []
    for i, (home, away) in enumerate(teams, 1):
        match_list.append({
            "holdId": hold_id, "matchNo": i, "homeTeam": home, "awayTeam": away,
            "homeRank": 5, "awayRank": 5, "homeGoalsFor": 20, "awayGoalsFor": 20,  
            "homeInjuries": 0, "awayInjuries": 0, "weather": "晴"
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
