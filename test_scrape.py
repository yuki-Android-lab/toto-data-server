import requests
from bs4 import BeautifulSoup

# 第1361回 第1試合（福岡vs神戸）のURL
url = "https://www.totoone.jp/match/27736"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"🔄 {url} からデバッグ用HTMLを抽出します...")

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("\n=============================================")
        print("🔍 【デバッグ1】ページ全体のタイトル（<title>タグ）")
        print("=============================================")
        print(soup.find('title').get_text().strip() if soup.find('title') else "タイトルなし")
        
        print("\n=============================================")
        print("🔍 【デバッグ2】「選手情報（怪我人）」前後のHTML構造")
        print("=============================================")
        # サイト内のテーブル（tr, td）の構造を分かりやすく20行分ほど抽出
        rows = soup.find_all('tr')
        print(f"探知された総テーブル行数: {len(rows)}")
        
        count = 0
        for row in rows:
            # 💡 完全に中身をそのまま出すとグチャグチャになるため、
            # 各セルのテキストと、その tr が持っているHTML文字を一部露出させます
            cells = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
            if cells:
                print(f"\n[行番号 {count}] セル配列: {cells}")
                # 該当行の生のHTMLを少しだけ見せる
                raw_row = str(row)[:200]
                print(f"  └ 生HTML(冒頭): {raw_row} ...")
                count += 1
                if count >= 30: # ログが埋まりすぎないよう30行でストップ
                    print("\n...（以降の行は省略）...")
                    break
                    
        print("\n=============================================")
        print("🔍 【デバッグ3】主要なDIVタグのクラス名一覧")
        print("=============================================")
        # チーム名や順位が隠れていそうな怪しい親要素のクラス名をあぶり出します
        divs = soup.find_all('div', class_=True)
        class_names = set([col for div in divs for col in div['class']])
        print("ページ内で使われている主なクラス名:")
        print(list(class_names)[:20]) # 代表して20個表示
        
    else:
        print(f"🔴 通信失敗：ステータスコード {response.status_code}")
except Exception as e:
    print(f"❌ エラー発生: {e}")
