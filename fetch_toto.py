import urllib.request
from bs4 import BeautifulSoup
import json

def main():
    url = "https://www.sport-kuji.sportstoto.co.jp/toto/index.html"
    match_list = []
    
    # 今週（5月23日締め切り分）の正しい対戦カード
    teams = [
        ("福岡", "神戸"), ("鹿島", "FC東京"), ("京都", "長崎"), ("岡山", "C大阪"),
        ("東京V", "横浜FM"), ("広島", "名古屋"), ("柏", "千葉"), ("水戸", "川崎F"),
        ("清水", "G大阪"), ("札幌", "磐田"), ("仙台", "横浜FC"), ("徳島", "今治"), ("藤枝", "いわき")
    ]
    
    for i, (home, away) in enumerate(teams, 1):
        match_list.append({
            "matchNo": i,
            "homeTeam": home,
            "awayTeam": away,
            "homeRank": 10,
            "awayRank": 5,
            "homeGoalsFor": 15,
            "awayGoalsFor": 20,
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

if __name__ == "__main__":
    main()
