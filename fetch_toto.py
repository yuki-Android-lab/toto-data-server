import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys

def get_current_toto_teams():
    """スマホ版への強制転送を回避するため、holdId付きのPC版URLをダイレクトに指定。
    確実に13試合のテキストが含まれるHTMLをロードします。"""
    toto_teams = []
    
    # ログから判明した最新の開催回(1631)を含むPC版の直接URL
    url = "https://toto.yahoo.co.jp/toto/?holdId=1631"
    
    # 完全にPC(Windows / Chrome)からのアクセスに見せかけるための厳密なヘッダー
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # PC版の13試合テーブルに存在する matchNo を目印に全ての行を取得
        rows = soup.find_all('tr')
        
        temp_teams = []
        for row in rows:
            cells = [td.text.strip() for td in row.find_all('td')]
            # PC版の対戦表は通常、1つの行に「試合番号」「ホームチーム」「アウェイチーム」等のデータが入る
            if len(cells) >= 3:
                # チーム名に余計な記号や％、投票などの文字が混ざっていないか、純粋な文字列を精査
                clean_cells = [c for c in cells if c and not any(x in c for x in ["投票", "%", "引き分け", "vs", "VS", "通算"])]
                if len(clean_cells) >= 2:
                    # 最初の2つの有効な文字列をホーム、アウェイと仮定
                    home = re.sub(r'\s+', '', clean_cells[0])
                    away = re.sub(r'\s+', '', clean_cells[1])
                    
                    # チーム名として明らかに不自然な文字（数字のみ等）を除外
                    if home and away and not home.isdigit() and not away.isdigit():
                        if len(home) <= 8 and len(away) <= 8:  # チーム名は通常短い
                            temp_teams.append((home, away))

        # 重複を排除しつつ、綺麗に13試合分を取り出す
        seen = set()
        for home, away in temp_teams:
            pair = (home, away)
            if pair not in seen and len(toto_teams) < 13:
                seen.add(pair)
                toto_teams.append(pair)

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
    
    if len(teams) < 13:
        print("\n==================================================")
        print(f"【案内】対象の13試合を確定できませんでした（現在取得数: {len(teams)}組）。")
        print("URLを再調整するか、今節のカードが公開されているかご確認ください。")
        print("==================================================")
        sys.exit(0)
    
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
