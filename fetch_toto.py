import urllib.request
from bs4 import BeautifulSoup
import json
import re

def get_current_toto_teams():
    """【検証1の対策】投票率テーブルを完全にスルーし、専用クラスから13試合のチーム名を確実に取得"""
    toto_teams = []
    url = "https://toto.yahoo.co.jp/toto/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Yahoo! totoの仕様である「左右のチーム名」を保持する要素を直接狙い撃ち
        home_elements = soup.find_all(class_='left-team')
        away_elements = soup.find_all(class_='right-team')
        
        for home_el, away_el in zip(home_elements, away_elements):
            home = home_el.text.strip()
            away = away_el.text.strip()
            
            # 余計な改行や空白、システム文言を除去
            home = re.sub(r'\s+', '', home)
            away = re.sub(r'\s+', '', away)
            
            if home and away and "投票" not in home and "引き分け" not in home:
                if (home, away) not in toto_teams and len(toto_teams) < 13:
                    toto_teams.append((home, away))
                    
    except Exception as e:
        print(f"【エラー】toto対戦カードの解析に失敗: {e}")
        
    return toto_teams

def get_official_standings():
    """【検証2の対策】実績の確認された「西暦なし」の固定URLから正確に順位表を取得"""
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
                # Jリーグ公式の順位表構造をパース
                table = soup.find('table', class_='table-standings') or soup.find('table')
                if not table: continue
                
                for row in table.find_all('tr'):
                    if row.find('th'): continue
                    cols = row.find_all('td')
                    if len(cols) < 5: continue
                    
                    rank_text = cols[0].text.strip()
                    team_name = cols[1].text.strip()
                    
                    try:
                        rank = int(rank_text)
                        # 得点（通常7列目）を安全に取得
                        goals = int(cols[6].text.strip()) if len(cols) > 6 else 0
                        raw_data[team_name] = {"rank": rank, "goals": goals}
                    except ValueError:
                        continue
            else:
                # スポーツナビの順位表構造をパース
                table = soup.find('table', class_='sn-table')
                if not table: continue
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) < 7: continue
                    team_name = cols[1].text.strip()
                    rank = int(cols[0].text.strip())
                    goals = int(cols[6].text.strip())
                    raw_data[team_name] = {"rank": rank, "goals": goals}
        except Exception as e:
            print(f"【警告】{category}のデータ取得スキップ: {e}")
            
    return raw_data

def find_stats(toto_name, raw_data):
    """toto表記のチーム名と公式サイトの正式名称を紐づけるマッピング関数"""
    alias_map = {
        # Jリーグ（表記ブレを補正）
        "札幌": "コンサドーレ札幌", "仙台": "ベガルタ仙台", "秋田": "ブラウブリッツ秋田",
        "山形": "モンテディオ山形", "いわき": "いわきＦＣ", "水戸": "水戸ホーリーホック",
        "栃木": "栃木ＳＣ", "群馬": "ザスパ群馬", "大宮": "大宮アルディージャ",
        "千葉": "ジェフユナイテッド千葉", "柏": "柏レイソル", "FC東京": "ＦＣ東京",
        "東京V": "東京ヴェルディ", "町田": "ＦＣ町田ゼルビア", "川崎F": "川崎フロンターレ",
        "横浜FM": "横浜Ｆ・マリノス", "横浜FC": "横浜ＦＣ", "湘南": "湘南ベルマーレ",
        "甲府": "ヴァンフォーレ甲府", "松本": "松本山雅ＦＣ", "新潟": "アルビレックス新潟",
        "富山": "カターレ富山", "金沢": "ツエーゲン金沢", "清水": "清水エスパルス",
        "磐田": "ジュビロ磐田", "藤枝": "藤枝ＭＹＦＣ", "沼津": "アスルクラロ沼津",
        "名古屋": "名古屋グランパス", "岐阜": "ＦＣ岐阜", "京都": "京都サンガF.C.",
        "G大阪": "ガンバ大阪", "C大阪": "セレッソ大阪", "神戸": "ヴィッセル神戸",
        "奈良": "奈良クラブ", "鳥取": "ガイナーレ鳥取", "岡山": "ファジアーノ岡山",
        "広島": "サンフレッチェ広島", "レノファ山口": "レノファ山口ＦＣ", "徳島": "徳島ヴォルティス",
        "愛媛": "愛媛ＦＣ", "今治": "ＦＣ今治", "福岡": "アビスパ福岡",
        "北九州": "ギラヴァンツ北九州", "鳥栖": "サガン鳥栖", "長崎": "V・ファーレン長崎",
        "熊本": "ロアッソ熊本", "大分": "大分トリニータ", "宮崎": "テゲバジャーロ宮崎",
        "鹿児島": "鹿児島ユナイテッドＦＣ", "琉球": "ＦＣ琉球",
        # 欧州主要クラブ
        "マンU": "マンチェスター・ユナイテッド", "マンC": "マンチェスター・シティ",
        "フランクフ": "フランクフルト", "B・MG": "ボルシアMG", "レバーク": "レバークーゼン"
    }
    
    search_name = alias_map.get(toto_name, toto_name)
    search_name_zen = search_name.replace("FC", "ＦＣ")
    search_name_han = search_name.replace("ＦＣ", "FC")

    for official_name, stats in raw_data.items():
        if (search_name in official_name) or (search_name_zen in official_name) or (search_name_han in official_name) or (official_name in search_name):
            return stats["rank"], stats["goals"]
            
    print(f"【マッピング未登録】チーム名【{toto_name}】が公式順位表で見つからなかったため初期値を適用します。")
    return 10, 15

def main():
    print("1. 今週のtoto対象対戦カードを自動取得中...")
    teams = get_current_toto_teams()
    
    if len(teams) < 13:
        print("\n==================================================")
        print("【警告】対戦カードが自動取得できないため予測が出来ません。")
        print(f"（現在取得できたペア数: {len(teams)}組）")
        print("==================================================")
        return
    
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

    print("\n【自動取得・データ反映後の対戦一覧】")
    for match in match_list:
        print(f"第 {match['matchNo']:02d} 試合: {match['homeTeam']}({match['homeRank']}位) vs {match['awayTeam']}({match['awayRank']}位) [ホーム総得点:{match['homeGoalsFor']}]")

if __name__ == "__main__":
    main()
