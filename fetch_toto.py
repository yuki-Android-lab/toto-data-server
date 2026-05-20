import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys

def get_current_toto_teams():
    """Yahoo! totoのページのみから今週の13試合を抽出。
    メンテナンス中などで取得できない場合は空リストを返す。"""
    toto_teams = []
    url = "https://toto.yahoo.co.jp/toto/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # メンテナンス画面であれば即座に処理を諦めて空で返す
        if "システムメンテナンス" in html or "一時停止" in html:
            print("【状態】Yahoo! totoがシステムメンテナンス中のため、対戦カードを読み込めません。")
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr', class_=re.compile(r'match|card|row'))
        for row in rows:
            cells = [td.text.strip() for td in row.find_all('td') if td.text.strip()]
            if len(cells) >= 3:
                # 投票率などのノイズを徹底排除
                clean_cells = [c for c in cells if "投票" not in c and "引き分け" not in c and "vs" not in c and "%" not in c]
                if len(clean_cells) >= 2:
                    home = re.sub(r'\s+', '', clean_cells[0])
                    away = re.sub(r'\s+', '', clean_cells[1])
                    if home and away and len(toto_teams) < 13:
                        toto_teams.append((home, away))
    except Exception as e:
        print(f"【通信エラー】Yahoo! totoへのアクセスに失敗: {e}")
        
    return toto_teams

def get_official_standings():
    """最新の順位表データを固定URLから取得"""
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
                        team_name = cols[1].text.strip()
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
                    team_name = cols[1].text.strip()
                    raw_data[team_name] = {"rank": int(cols[0].text.strip()), "goals": int(cols[6].text.strip())}
        except Exception:
            pass
    return raw_data

def find_stats(toto_name, raw_data):
    """チーム名のマッピング"""
    alias_map = {
        "札幌": "コンサドーレ札幌", "仙台": "ベガルタ仙台", "いわき": "いわきＦＣ", 
        "水戸": "水戸ホーリーホック", "栃木": "栃木ＳＣ", "群馬": "ザスパ群馬", 
        "千葉": "ジェフユナイテッド千葉", "柏": "柏レイソル", "FC東京": "ＦＣ東京",
        "東京V": "東京ヴェルディ", "町田": "ＦＣ町田ゼルビア", "川崎F": "川崎フロンターレ",
        "横浜FM": "横浜Ｆ・マリノス", "横浜FC": "横浜ＦＣ", "湘南": "湘南ベルマーレ",
        "甲府": "ヴァンフォーレ甲府", "新潟": "アルビレックス新潟", "清水": "清水エスパルス",
        "磐田": "ジュビロ磐田", "藤枝": "藤枝ＭＹＦＣ", "名古屋": "名古屋グランパス", 
        "京都": "京都サンガF.C.", "G大阪": "ガンバ大阪", "C大阪": "セレッソ大阪", 
        "神戸": "ヴィッセル神戸", "岡山": "ファジアーノ岡山", "広島": "サンフレッチェ広島", 
        "徳島": "徳島ヴォルティス", "愛媛": "愛媛ＦＣ", "今治": "ＦＣ今治", "福岡": "アビスパ福岡",
        "北九州": "ギラヴァンツ北九州", "鳥栖": "サガン鳥栖", "長崎": "V・ファーレン長崎",
        "熊本": "ロアッソ熊本", "大分": "大分トリニータ", "鹿児島": "鹿児島ユナイテッドＦＣ",
        "マンU": "マンチェスター・ユナイテッド", "マンC": "マンチェスター・シティ", "フランクフ": "フランクフルト"
    }
    search_name = alias_map.get(toto_name, toto_name)
    for official_name, stats in raw_data.items():
        if (search_name in official_name) or (official_name in search_name):
            return stats["rank"], stats["goals"]
    return 10, 15

def main():
    print("1. 今週のtoto対象対戦カードを自動取得中...")
    teams = get_current_toto_teams()
    
    # Yahooから13試合取れなければ、中途半端なデータを残さず安全に処理を終了（スキップ）する
    if len(teams) < 13:
        print("\n==================================================")
        print("【案内】今週の対戦カードを正しく取得できませんでした。")
        print("データの一貫性を守るため、今回の処理をスキップして終了します。")
        print("==================================================")
        sys.exit(0) # エラーを出さずに静かに終了
    
    print(f"  -> 成功：今週の {len(teams)} 試合を正常に特定しました。")
    print("\n2. 各リーグの公式サイトから最新順位データを収集中...")
    raw_data = get_official_standings()
    
    match_list = []
    for i, (home, away) in enumerate(teams, 1):
        home_rank, home_goals = find_stats(home, raw_data)
        away_rank, away_goals = find_stats(away, raw_data)
        
        match_list.append({
            "matchNo": i, "homeTeam": home, "awayTeam": away,
            "homeRank": home_rank, "awayRank": away_rank,      
            "homeGoalsFor": home_goals, "awayGoalsFor": away_goals,  
            "homeInjuries": 0, "awayInjuries": 1, "weather": "晴",
            "homeCompatibility": "拮抗", "homeTactics": "カウンター", "awayTactics": "ポゼッション",
            "homeRecent": "普通", "awayRecent": "好調", "homeInterval": "中6日", "awayInterval": "中3日",
            "homeRainWinRate": "45%", "awayRainWinRate": "55%"
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)
    print("\n--- data.json の保存が完了しました ---")

if __name__ == "__main__":
    main()
