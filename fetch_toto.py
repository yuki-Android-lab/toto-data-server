import urllib.request
from bs4 import BeautifulSoup
import json
import re
import sys

def get_current_toto_teams():
    """デバッグ機能を大幅に強化した対戦カード取得関数。
    取得した生のHTMLの一部(IN)と、抽出を試みた結果(OUT)をログに強制出力します。"""
    toto_teams = []
    url = "https://toto.yahoo.co.jp/toto/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    print("\n--- 【DEBUG: IN】Yahoo! totoへのアクセスを開始します ---")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        print(f"  -> 通信成功。取得したHTMLの総文字数: {len(html)} 文字")
        
        # 【INの検証】HTMLの先頭500文字と、怪しい箇所を部分出力
        print("\n=== [DEBUG] 取得したHTMLの冒頭部分 ===")
        print(html[:500])
        print("=======================================")
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # クラス名による部分的な検証
        home_elements = soup.find_all(class_=re.compile(r'homeTeam'))
        away_elements = soup.find_all(class_=re.compile(r'awayTeam'))
        
        print(f"\n=== [DEBUG: OUT] 抽出中間ステータス ===")
        print(f"  ・検出された 'homeTeam' を含む要素数: {len(home_elements)} 個")
        print(f"  ・検出された 'awayTeam' を含む要素数: {len(away_elements)} 個")
        
        # 実際に検出されたテキストの中身を、定石通りログに出力
        if home_elements:
            print("  ・最初に見つかったhomeTeam要素の生テキスト:", [el.text.strip() for el in home_elements[:3]])
        if away_elements:
            print("  ・最初に見つかったawayTeam要素の生テキスト:", [el.text.strip() for el in away_elements[:3]])
        print("=======================================")

        # ペアを組む処理
        for i, (home_el, away_el) in enumerate(zip(home_elements, away_elements), 1):
            home_name = home_el.text.strip()
            away_name = away_el.text.strip()
            
            if home_name and away_name and "チーム" not in home_name and "投票" not in home_name:
                home = re.sub(r'\s+', '', home_name)
                away = re.sub(r'\s+', '', away_name)
                if home and away and len(toto_teams) < 13:
                    toto_teams.append((home, away))

        print(f"\n  -> クラス名判定による最終取得ペア数: {len(toto_teams)} 組")
        
        # 【全滅時のバックアップ追跡ログ】もし0件だった場合、ページ内にどんなテキストがあるかヒントを出力
        if len(toto_teams) == 0:
            print("\n=== [DEBUG: 追跡] クラス名で取得できなかったため、ページ内のテキスト行を走査します ===")
            all_text = soup.get_text()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            print(f"  ・ページ内の全テキスト行数: {len(lines)} 行")
            print("  ・冒頭の30行をダンプします:")
            for idx, line in enumerate(lines[:30]):
                print(f"    [{idx+1}] {line}")
            print("=======================================================================")

    except Exception as e:
        print(f"【DEBUG: エラー検出】通信または解析中に例外が発生しました: {e}")
        import traceback
        traceback.print_exc()
        
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
        print(f"【判定】対象の13試合を確定できませんでした（現在取得数: {len(teams)}組）。")
        print("詳細な原因は上記の【DEBUG】ログにすべて出力されています。処理を終了します。")
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
            "homeCompatibility": "拮開", "homeTactics": "カウンター", "awayTactics": "ポゼッション",
            "homeRecent": "普通", "awayRecent": "好調", "homeInterval": "中6日", "awayInterval": "中3日",
            "homeRainWinRate": "45%", "awayRainWinRate": "55%"
        })

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)
    print("\n--- data.json の保存が完了しました ---")

if __name__ == "__main__":
    main()
