import urllib.request
from bs4 import BeautifulSoup
import json
from datetime import datetime

def get_current_toto_teams():
    """Yahoo! totoの最新開催ページから、今週の対象13試合のチーム名を自動取得する"""
    toto_teams = []
    url = "https://toto.yahoo.co.jp/toto/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # テーブル行の抽出
        rows = soup.find_all('tr', class_=re.compile(r'match|card|row'))
        if not rows:
            table = soup.find('table', class_='toto-table') or soup.find('table')
            if table:
                rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                home = cells[1].text.strip().split('\n')[0].strip()
                away = cells[2].text.strip().split('\n')[0].strip()
                
                if home and away and len(toto_teams) < 13:
                    toto_teams.append((home, away))
                    
    except Exception as e:
        print(f"【システムエラー】通信または解析に失敗しました: {e}")
        
    return toto_teams

def get_official_standings():
    """全リーグの公式ページからデータを集め、{「公式チーム名」: {順位, 得点}} の辞書を作る"""
    raw_data = {}
    current_year = datetime.now().year
    
    urls = {
        "J1": f"https://www.jleague.jp/standings/{current_year}/j1/",
        "J2": f"https://www.jleague.jp/standings/{current_year}/j2/",
        "J3": f"https://www.jleague.jp/standings/{current_year}/j3/",
        "プレミア": "https://soccer.yahoo.co.jp/ws/category/eng/standings",
        "ブンデス": "https://soccer.yahoo.co.jp/ws/category/ger/standings"
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for category, url in urls.items():
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                info = response.info()
                charset = info.get_content_charset() or 'utf-8'
                html = response.read().decode(charset, errors='ignore')
            
            soup = BeautifulSoup(html, 'html.parser')
            
            if "jleague" in url:
                table = soup.find('table', class_='table-standings')
                if not table: continue
                for row in table.find_all('tr'):
                    if row.find('th'): continue
                    cols = row.find_all('td')
                    if len(cols) < 5: continue
                    
                    rank_text = cols[0].text.strip()
                    team_name = cols[1].text.strip()
                    
                    try:
                        rank = int(rank_text)
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
                    rank = int(cols[0].text.strip())
                    goals = int(cols[6].text.strip())
                    raw_data[team_name] = {"rank": rank, "goals": goals}
        except Exception as e:
            print(f"{category}のデータ取得中にエラー: {e}")
            
    return raw_data

def find_stats(toto_name, raw_data):
    """totoのチーム名から公式データを検索"""
    alias_map = {
        "G大阪": "ガンバ大阪", "C大阪": "セレッソ大阪",
        "マンU": "マンチェスター・ユナイテッド", "マンC": "マンチェスター・シティ",
        "フランクフ": "フランクフルト", "B・MG": "ボルシアMG", "レバーク": "レバークーゼン",
        "川崎F": "川崎フロンターレ", "東京V": "東京ヴェルディ", "横浜FM": "横浜Ｆ・マリノス"
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
    import re
    print("1. 今週のtoto対象対戦カードを自動取得中...")
    teams = get_current_toto_teams()
    
    # ★ご指摘通りのチェックロジック。取得数が13試合に満たない場合は即座に中断
    if len(teams) < 13:
        print("\n==================================================")
        print("【警告】対戦カードが自動取得できないため予測が出来ません。")
        print("==================================================")
        return
    
    print("2. 各リーグの公式サイトから最新順位データを収集中...")
    raw_data = get_official_standings()
    
    match_list = []
    
    try:
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
    except Exception as e:
        print(f"マッチング処理中に予期せぬエラー: {e}")
        return

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(match_list, f, ensure_ascii=False, indent=4)
    print("--- data.json の保存が完了しました ---")

    print("\n【自動取得・データ反映後の対戦一覧】")
    for match in match_list:
        print(f"第 {match['matchNo']:02d} 試合: {match['homeTeam']}({match['homeRank']}位) vs {match['awayTeam']}({match['awayRank']}位) [ホーム総得点:{match['homeGoalsFor']}]")

if __name__ == "__main__":
    main()
