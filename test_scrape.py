import json
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError

BASE_URL = "https://www.totoone.jp"

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def fetch_html(url: str) -> str:
    """現在の環境で確実にHTMLソースを返すための最小限の処理"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # ページ全体の通信が落ち着くまで少し待つ
            time.sleep(3)
            return page.content()
        except Exception as e:
            print(f"URLアクセスエラー: {e}")
            return ""
        finally:
            browser.close()

def extract_names_from_section(section) -> list:
    """昔の test_scrape.py が行っていた、li や div からのキーワード抽出ロジックの完全再現"""
    keywords = ["欠場", "欠場濃厚", "出場停止", "出場微妙"]
    result = []
    
    # 1. 昔のロジック通り、li要素を最優先で走査
    for li in section.find_all("li"):
        txt = normalize_text(li.get_text())
        if any(k in txt for k in keywords):
            result.append(txt)
            
    # 2. 昔のロジック通り、liで見つからなければdiv要素を走査（フォールバック）
    if not result:
        for div in section.find_all("div"):
            txt = normalize_text(div.get_text())
            if any(k in txt for k in keywords):
                result.append(txt)

    # 3. 抽出したテキストから「ポジションやステータス」を削り、純粋な選手名だけを抽出する
    cleaned_names = []
    for r in result:
        # 昔の置換・分割ロジックの再現
        name = re.split(r"欠場|出場停止|出場微妙|欠場濃厚", r)[0]
        # ポジション表記（GK/DF/MF/FW）が残っている場合は削る
        name = re.sub(r"^(GK|DF|MF|FW)\s*", "", name)
        name = normalize_text(name)
        if name and name != "なし" and name not in cleaned_names:
            cleaned_names.append(name)
            
    return cleaned_names

def parse_injuries_only(soup: BeautifulSoup, match_no: int) -> dict:
    """
    昔の test_scrape.py の核心部。
    チーム名や順位は一切無視し、section要素の1番目(ホーム)と2番目(アウェイ)から
    離脱者リストをぶっこ抜く。
    """
    sections = soup.find_all("section")
    
    # 昔の仕様：sectionが足りなければ離脱者なしとして安全にスルーする（絶対にエラーで落とさない）
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
    # 昔動いていた、安全が確認されている固定の試合IDリスト
    hold_id = 1512
    match_ids = [27736, 27737, 27738, 27739, 27740, 27741, 27742, 27743, 27744, 27745, 27746, 27747, 27748]
    results = []

    print(f"巻き戻し実行: 開催回 {hold_id} の『怪我人・出場停止データのみ』を昔のロジックで抽出します...")

    for idx, match_id in enumerate(match_ids, start=1):
        url = f"{BASE_URL}/match/{match_id}"
        print(f"▶️ [試合No.{idx}] 離脱者解析中...")

        html = fetch_html(url)
        if not html:
            print(f"  ⚠️ HTMLが空のため、No.{idx} はスキップします。")
            continue
            
        try:
            # 新環境の html.parser または lxml どちらでも動くように標準パーサーを指定
            soup = BeautifulSoup(html, "html.parser")
            
            # 離脱者データのみを昔のロジックで抽出
            injury_data = parse_injuries_only(soup, idx)
            
            # アプリ（Kotlin）側がクラッシュしないよう、今回の巻き戻しで取得しない項目は
            # エラーにならない安全な固定値（ダミー）を最低限セットして器を維持します
            full_data = {
                "holdId": hold_id,
                "matchNo": idx,
                "homeTeam": f"ホームチーム_{idx}", # 後で修復するための一時文字列
                "awayTeam": f"アウェイチーム_{idx}",
                "homeRank": 99,
                "awayRank": 99,
                **injury_data
            }
            results.append(full_data)
            print(f"  ✅ 成功: 離脱者 H {injury_data['homeInjuriesCount']}人 / A {injury_data['awayInjuriesCount']}人")
            
        except Exception as e:
            # 【絶対厳守】何があっても raise せず、ログを出して次の試合の処理を続け、ファイルを残す
            print(f"  ❌ No.{idx} (ID: {match_id}) の解析で予期せぬエラー: {e}")

    # 一部でも取得できたデータがあれば JSON を保存する
    if results:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✨ [復旧完了] 昔のロジックで data.json を生成しました。")
    else:
        print("\n❌ 1件もデータが取得できませんでした。")

if __name__ == "__main__":
    main()
