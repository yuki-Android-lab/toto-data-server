import requests
from bs4 import BeautifulSoup

# テスト対象：第1361回（2026/05/23）第1試合（福岡vs神戸）のページ
url = "https://www.totoone.jp/match/27736"

# プログラムからの自動アクセスと判定されて弾かれないよう、ブラウザのフリをする設定
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    print(f"🔄 {url} にアクセスを試みています...")
    response = requests.get(url, headers=headers, timeout=10)
    
    # ステータスコードが200（成功）か確認
    if response.status_code == 200:
        print("🟢 通信成功！Webサイトの読み込みに成功しました。")
        
        # HTMLを解析
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 実験として、ページ内の「タイトル（試合名）」が正しく抜けるかテスト
        title_tag = soup.find('title')
        if title_tag:
            print(f"📦 取得したページタイトル: {title_tag.get_text().strip()}")
        
        # 画面にHTMLの最初の500文字だけお試し表示してみる
        print("\n--- HTML冒頭の500文字 ---")
        print(response.text[:500])
        print("--------------------------")
        
    else:
        print(f"🔴 通信失敗：ステータスコード {response.status_code}")
        print("サイト側のセキュリティブロック（403等）、またはURLが存在しない可能性があります。")

except Exception as e:
    print(f"❌ エラーが発生しました: {e}")
