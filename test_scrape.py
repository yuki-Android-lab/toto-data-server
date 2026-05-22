import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://www.totoone.jp/match/27736"

print(f"🔄 {url} から選手情報のHTML配置を特定します...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")
    
    # 完全に描画されるまで少し長めに待機
    time.sleep(3.0)
    html_content = page.content()
    browser.close()

soup = BeautifulSoup(html_content, 'html.parser')

print("\n=============================================")
print("🎯 【特定ログ】『選手情報』周辺のHTMLテキスト抽出")
print("=============================================")

# 💡 キーワード「欠場濃厚」または「出場停止」が含まれる要素の親をたどる
keywords = ["欠場濃厚", "出場停止", "出場微妙", "橋本悠", "扇原貴宏"]
found = False

for kw in keywords:
    elements = soup.find_all(text=lambda text: text and kw in text)
    if elements:
        print(f"\n🔑 キーワード 【{kw}】 が見つかりました！(検知数: {len(elements)})")
        found = True
        for idx, elem in enumerate(elements):
            # その文字を囲んでいる親タグ（divやspanなど）の構造を3階層上まで出力
            parent = elem.parent
            print(f"  [{idx}] 文字列: '{elem.strip()}'")
            print(f"      └ 親タグ: <{parent.name}> クラス名: {parent.get('class')}")
            if parent.parent:
                print(f"      └ 祖父タグ: <{parent.parent.name}> クラス名: {parent.parent.get('class')}")
            if parent.parent and parent.parent.parent:
                print(f"      └ 曽祖父タグ: <{parent.parent.parent.name}> クラス名: {parent.parent.parent.get('class')}")

if not found:
    print("⚠️ 指定したキーワードがHTML内に見つかりませんでした。")
    print("念のため、ページ全体の文字情報を最初の2000文字だけ出力します：")
    print(soup.get_text()[:2000])
