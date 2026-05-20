import urllib.request
from bs4 import BeautifulSoup
import json

def get_official_standings():
    """全リーグの公式ページからデータを集め、{「公式チーム名」: {順位, 得点}} の辞書を作る"""
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
                # ★文字化け対策：レスポンスからエンコーディング（utf-8やshift_jis）を自動取得
                info = response.info()
                charset = info.get_content_charset()
                if not charset:
                    charset = 'utf-8' # 取れない場合はutf-8をデフォルトに
                
                html = response.read().decode(charset, errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            if "jleague" in url:
                table = soup.find('table', class_='table-standings')
                if not table: continue
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) < 8: continue
                    team_name = cols[1].text.strip()
                    rank = int(cols[0].text.strip())
                    goals = int(cols[7].text.strip())
                    raw_data[team_name] = {"rank": rank, "goals": goals}
            else:
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
            print(f"{category}のデータ取得失敗: {e}")
            
    return raw_data

def find_stats(toto_name, raw_data):
    """totoのチーム名（略称）から、公式データの順位と得点を賢く検索する関数"""
    alias_map = {
        "G大阪": "ガンバ大阪", "C大阪": "セレッソ大阪",
        "マンU": "マンチェスター・ユナイテッド", "マンC": "マンチェスター・シティ",
        "フランクフ": "フランクフルト", "B・MG": "ボルシアMG", "レバーク": "レバークーゼン"
    }
    
    search_name = alias_map.get(toto_name, toto_name)
    search_name = search_name.replace("FC", "ＦＣ")

    for official_name, stats in raw_data.items():
        if search_name in official_name or official_name in search_name:
            return stats["rank"], stats["goals"]
            
    return 10, 15

def main():
    print("各リーグの公式サイトから最新データを収集中...")
    raw_data = get_official_standings()
    
    match_list = []
    
    # 今週の対戦カード
    teams = [
        ("福岡", "神戸"), ("鹿島", "FC東京"), ("京都", "長崎"), ("岡山", "C大阪"),
        ("東京V", "横浜FM"), ("広島", "名古屋"), ("柏", "千葉"), ("水戸", "川崎F"),
        ("清水", "G大阪"), ("札幌", "磐田"), ("仙台", "横浜FC"), ("徳島", "今治"), ("藤枝", "いわき")
    ]
    
    for i, (home, away) in enumerate(teams, 1):
        home_rank, home_goals = find_stats(home, raw_data)
        away_rank, away_goals = find_stats(away, raw_data)
        
        match_list.append({
            "matchNo": i,
            "homeTeam": home,
            "awayTeam": away,
            "homeRank": home_rank,      
            "awayRank": away_rank,      
            "homeGoalsFor": home_goals,  
            "awayGoalsFor": away_goals,  
            "homeInjuries": 0,
            "awayInjuries": 1,
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
    print("--- data.json の保存が完了しました ---")

    print("\n【完全自動判定版・データ反映後の対戦一覧】")
    with open("data.json", "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
        for match in loaded_data:
            print(f"第 {match['matchNo']:02d} 試合: {match['homeTeam']}({match['homeRank']}位) vs {match['awayTeam']}({match['awayRank']}位) [ホーム総得点:{match['homeGoalsFor']}]")

if __name__ == "__main__":
    main()
