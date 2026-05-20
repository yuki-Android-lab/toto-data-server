import urllib.request

def test_scraping():
    urls = {
        "J1": "https://www.jleague.jp/standings/j1/",
        "プレミア": "https://soccer.yahoo.co.jp/ws/category/eng/standings"
    }
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for category, url in urls.items():
        print(f"\n==================== {category} の検証開始 ====================")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                info = response.info()
                charset = info.get_content_charset() or 'utf-8'
                html = response.read().decode(charset, errors='ignore')
            
            print(f"【ステータス】: 接続成功（取得した文字数: {len(html)}文字）")
            
            # 特徴的な文字列が含まれているかチェック
            print("【中身の検証】:")
            if "table" in html:
                print("  -> HTML内に <table> タグ自体は存在します。")
            else:
                print("  -> 警告: <table> タグが見当たりません。")
                
            if "table-standings" in html or "sn-table" in html:
                print("  -> 狙っている順位表のクラス名（table-standings または sn-table）がHTML内に存在します。")
            else:
                print("  -> 警告: 狙っている順位表のクラス名がHTML内に見つかりません。")

            # 冒頭500文字をサンプル出力して、ブロック画面になっていないか確認
            print("\n【取得HTMLの冒頭サンプル（最初の500文字）】")
            print(html[:500])
            
        except Exception as e:
            print(f"【エラー発生】: {e}")
        print(f"==================== {category} の検証終了 ====================\n")

if __name__ == "__main__":
    test_scraping()
