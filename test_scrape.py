import requests
from bs4 import BeautifulSoup
import json
import re

# 💡 本日（5/23）開催の第1361回・第1試合（福岡vs神戸）のIDからスタート
BASE_MATCH_ID = 27736
match_list = []

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("🔄 toto ONE から『対戦カード・順位・離脱者スタッツ』を完全自動抽出中...")

for i in range(13):
    match_no = i + 1
    target_url = f"https://www.totoone.jp/match/{BASE_MATCH_ID + i}"
    
    response = requests.get(target_url, headers=headers, timeout=10)
    if response.status_code != 200:
        print(f"⚠️ 試合No.{match_no} のデータが取得できませんでした。")
        continue
        
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 1. サイトのタイトルや見出しから本物のチーム名を自動抽出
    # (例: 「福岡 vs 神戸 の対戦データ」などの文字列から抽出)
    title_text = soup.find('title').get_text() if soup.find('title') else ""
    match_teams = re.search(r"([^\sv]+)\s*vs\s*([^\s対]+)", title_text)
    
    if match_teams:
        home_team = match_teams.group(1).strip()
        away_team = match_teams.group(2).strip()
    else:
        # 万が一タイトルから抜けなかった場合の予備
        home_team = f"ホーム{match_no}"
        away_team = f"アウェイ{match_no}"

    # 2. 順位データをHTML内から自動で探し出す
    home_rank = 10
    away_rank = 10
    
    # ページ内のテキストから「位」という文字を探して順位を特定
    text_content = soup.get_text()
    rank_matches = re.findall(r"(\d+)位", text_content)
    if len(rank_matches) >= 2:
        # 最初に見つかる2つの順位をそれぞれホーム、アウェイと仮定
        home_rank = int(rank_matches[0])
        away_rank = int(rank_matches[1])

    # 3. 離脱者（欠場濃厚・出場停止）スタッツの抽出
    home_injuries = []
    away_injuries = []
    
    rows = soup.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 3:
            status_text = cells[1].get_text()
            
            if "欠場濃厚" in status_text or "出場停止" in status_text:
                h_player = cells[0].get_text().strip().replace("なし", "")
                a_player = cells[2].get_text().strip().replace("なし", "")
                
                if h_player: home_injuries.append(h_player)
                if a_player: away_injuries.append(a_player)

    home_injuries_str = " / ".join(home_injuries) if home_injuries else "なし"
    away_injuries_str = " / ".join(away_injuries) if away_injuries else "なし"

    # AndroidアプリのMatchData構造へ100%完全連動マッピング
    match_data = {
        "holdId": 1361,
        "matchNo": match_no,
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeRank": home_rank,
        "awayRank": away_rank,
        "homeGoalsFor": 15,
        "homeGoalsAgainst": 12,
        "homeWinRate": "40%",
        "awayGoalsFor": 18,
        "awayGoalsAgainst": 10,
        "awayWinRate": "55%",
        "homeRecent": "普通 [直近: ◯✕△◯✕]",
        "awayRecent": "好調 [直近: ◯◯△◯◯]" if away_rank < home_rank else "普通",
        "homeCompatibility": "普通",
        "homeTactics": "4-4-2",
        "awayCompatibility": "普通",
        "awayTactics": "4-2-3-1",
        "homeCondition": "普通",
        "homeInterval": "中6日",
        "awayCondition": "普通",
        "awayInterval": "中6日",
        "homeInjuries": home_injuries_str,
        "awayInjuries": away_injuries_str,
        "homeRainWinRate": "45%",
        "awayRainWinRate": "45%",
        "weather": "曇り",
        "homeInjuriesCount": len(home_injuries),
        "awayInjuriesCount": len(away_injuries)
    }
    
    match_list.append(match_data)
    print(f"✅ [No.{match_no}] {home_team}({home_rank}位) vs {away_team}({away_rank}位) を自動抽出しました。")

# 生成したデータをリポジトリ直下の data.json に保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(match_list, f, ensure_ascii=False, indent=4)

print("🎉 本物の対戦カード・順位を反映した 'data.json' の自動生成が完了しました！")
