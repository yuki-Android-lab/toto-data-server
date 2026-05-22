import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

url = "https://www.totoone.jp/match/27736"

print(f"🔄 {url} へ本物ブラウザ（headless Chrome）で隠密アクセスを開始します...")

with sync_playwright() as p:
    # ブラウザを起動（ユーザーエージェントを偽装して人間っぽく振る舞う）
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    
    # ページを開く
    page.goto(url, wait_until="domcontentloaded")
    
    print("⏳ データの読み込み（ローディング表示の終了）を少し待ちます...")
    # 1秒間、画面がレンダリングされるのを物理的に待つ
    time.sleep(2.0)
    
    # 展開された後の本物のHTMLソースを取得
    html_content = page.content()
    browser.close()

# 展開後のHTMLを解析
soup = BeautifulSoup(html_content, 'html.parser')

print("\n=============================================")
print("🔍 【ブラウザ展開後デバッグ1】ページタイトル")
print("=============================================")
print(soup.find('title').get_text().strip() if soup.find('title') else "タイトルなし")

print("\n=============================================")
print("🔍 【ブラウザ展開後デバッグ2】探知されたテーブル行（tr）")
print("=============================================")
rows = soup.find_all('tr')
print(f"ブラウザ起動によって探知された総テーブル行数: {len(rows)}")

count = 0
for row in rows:
    cells = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
    if cells:
        print(f"\n[行番号 {count}] セル内容: {cells}")
        count += 1
        if count >= 20:
            print("\n...（20行以降は省略）...")
            break

if len(rows) == 0:
    print("\n⚠️ まだテーブルが0件です。文字データとしてページ内に残っているか確認します:")
    text_snippet = soup.get_text()
    if "欠場" in text_snippet or "出場停止" in text_snippet:
        print("💡 テーブル形式ではないですが、ページ内に『欠場』や『出場停止』の文字自体は存在しています！")
    else:
        print("❌ ページ内に怪我人に関するキーワードが見当たりません。")
