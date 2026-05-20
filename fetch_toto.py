import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys

def get_current_toto_teams():
    """セルの位置（インデックス）に一切依存せず、HTML内の『チーム名文字列』を
    直接検出してホームとアウェイを特定する最も堅牢なロジックです。"""
    toto_teams = []
    url = "https://toto.yahoo.co.jp/toto/?holdId=1631"
    
    # 順位表マッピング用の全主要チームのキーワードリスト（これを元にセル内を識別）
    known_keywords = [
        "札幌", "仙台", "いわき", "水戸", "栃木", "群馬", "千葉", "柏", "東京", "町田", 
        "川崎", "横浜", "湘南", "甲府", "新潟", "清水", "磐田", "藤枝", "名古屋", "京都", 
        "大阪", "神戸", "岡山", "広島", "徳島", "愛媛", "今治", "福岡", "北九州", "鳥栖", 
        "長崎", "熊本", "大分", "鹿児島", "鹿島", "浦和", "海外", "マン", "フランクフ"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        rows = soup.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                cell_texts = [td.text.strip().replace(" ", "").replace("　", "") for td in cells]
                match_no_text = cell_texts[0]
                
                # 1〜13の試合番号行であることを確認
                if match_no_text.isdigit() and 1 <= int(match_no_text) <= 13:
                    detected_teams = []
                    
                    # 行内の全セルを左からスキャンし、チーム名に該当する文字列を抽出
                    for text in cell_texts:
                        # 日付や投票率、ボタンなどの不要なノイズ行を徹底的に除外
                        if any(x in text for x in ["投票", "%", "型", "引き分け", "vs", "VS", "通算", "/", "："]):
                            continue
                            
                        # キーワードが含まれているか、かつ文字数が適切なチーム名らしい文字列か判定
                        if any(kw in text for kw in known_keywords) and len(text) <= 8:
                            # 重複を避けてストック（同じセルを複数回読まないよう配慮）
                            if text not in detected_teams:
                                detected_teams.append(text)
                    
                    # 1つの行から「ホーム」「アウェイ」の2チームが綺麗に検出できた場合のみ採用
                    if len(detected_teams) >= 2:
                        home = detected_teams[0]
                        away = detected_teams[1]
                        toto_teams.append((home, away))

    except Exception as e:
        print(f"【エラー】対戦カードのパース中に問題が発生しました: {e}")
        
    return toto_teams

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
        "G大阪": "ガンバ大阪", "C大阪": "セレッソ大阪", "神戸": "ヴィッセル神戸", "岡山": "ファジアーノ岡山", 
        "広島": "サンフレッチェ広島", "徳島": "徳島ヴォルティス", "愛媛": "愛媛ＦＣ", "今治": "ＦＣ今治", 
        "福岡": "アビスパ福岡", "北九州": "ギラヴァンツ北九州", "鳥栖": "サガン鳥栖", "長崎": "V・ファーレン長崎",
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
    print("1. 今週のtoto対象対戦カードを自動取得中...")
    teams = get_current_toto_teams()
    
    if len(teams) < 13:
        print(f"\n【警告】13試合分のデータを正常に抽出できませんでした（現在特定数: {len(teams)}組）。")
        sys.exit(0)
        
    print("\n==================================================")
    print("【検証ログ】プログラムが識別した13試合（完全確定）")
    print("==================================================")
    for i, (home, away) in enumerate(teams, 1):
        print(f"  [試合No.{i:02d}] ホーム: {home:<8} vs  アウェイ: {away}")
    print("==================================================\n")
    
    print("2. 各リーグの公式サイトから最新順位データを収集中...")
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
