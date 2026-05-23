import json
import re
from bs4 import BeautifulSoup
import requests

BASE_URL = "https://www.totoone.jp"

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def fetch_html_old_school(url: str) -> str:
    """
    Playwrightを完全排除。
    昔の環境通り、requestsを使ってサーバーから生のHTMLをそのまま1発で落とす。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
        else:
            print(f"  ⚠️ アクセス失敗 (Status Code: {response.status_code})")
            return ""
    except Exception as e:
        print(f"  ⚠️ 通信エラー: {e}")
        return ""

def extract_names_from_section(section) -> list:
    """昔の走査ロジックを完全再現"""
    keywords = ["欠場", "欠場濃厚", "出場停止", "出場微妙"]
    result = []
    
    # 生HTMLにある li と div を全捜索
    for li in section.find_all("li"):
        txt = normalize_text(li.get_text())
        if any(k in txt for k in keywords):
            result.append(txt)
            
    if not result:
        for div in section.find_all("div"):
            txt = normalize_text(div.get_text())
            if any(k in txt for k in keywords):
                result.append(txt)

    cleaned_names = []
    for r in result:
        name = re.split(r"欠場|出場停止|出場微妙|欠場濃厚", r)[0]
        name = re.sub(r"^(GK|DF|MF|FW)\s*", "", name)
        name = normalize_text(name)
        if name and name != "なし" and name not in cleaned_names:
            cleaned_names.append(name)
            
    return cleaned_names

def parse_injuries_old_school(soup: BeautifulSoup, match_no: int) -> dict:
    """
    生のHTMLデータに対して section を走査する。
    Playwrightに荒らされていない状態のDOMなので、昔の並び順がそのまま活きます。
    """
    sections = soup.find_all("section")
    
    if len(sections) < 2:
        return {
            "matchNo": match_no,
            "homeInjuries": "なし",
            "awayInjuries": "なし",
            "homeInjuriesCount": 0,
            "awayInjuriesCount": 0
        }
        
    home_list = extract_names_from_section(sections[0])
    away_list = extract_names_from_section(sections[1])
    
    return {
        "matchNo": match_no,
        "homeInjuries": " / ".join(home_list) if home_list else "なし",
        "awayInjuries": " / ".join(away_list) if away_list else "なし",
        "homeInjuriesCount": len(home_list),
        "awayInjuriesCount": len(away_list)
    }

def main():
    hold_id = 1512
    match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]
    results = []

    print(f"🚀 【完全環境巻き戻し】Playwrightを廃止し、昔のrequests環境で離脱者抽出をやり直します...")

    for idx, match_id in enumerate(match_ids, start=1):
        url = f"{BASE_URL}/match/{match_id}"
        print(f"▶️ [試合No.{idx}] 生HTML解析中...")

        html = fetch_html_old_school(url)
        if not html:
            continue
            
        try:
            # html.parser でシンプルに解析（lxmlすら不要）
            soup = BeautifulSoup(html, "html.parser")
            injury_data = parse_injuries_old_school(soup, idx)
            
            full_data = {
                "holdId": hold_id,
                "matchNo": idx,
                "homeTeam": f"ホームチーム_{idx}",
                "awayTeam": f"アウェイチーム_{idx}",
                "homeRank": 99,
                "awayRank": 99,
                **injury_data
            }
            results.append(full_data)
            print(f"  ✅ 抽出結果: H {injury_data['homeInjuriesCount']}人 / A {injury_data['awayInjuriesCount']}人")
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")

    if results:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✨ [完全復舊] 昔のrequests環境ロジックで data.json を再生成しました。")

if __name__ == "__main__":
    main()
