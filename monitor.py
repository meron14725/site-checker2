#!/usr/bin/env python3
"""
Webサイト監視＆LINE通知プログラム（同期版・シンプル）
特定の要素が出現したらスクリーンショットを撮影してLINEに通知
"""

from datetime import datetime
import json
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import tempfile
from dotenv import load_dotenv
from pathlib import Path
import random


# 環境変数の読み込み
load_dotenv()

# ========== 設定 ==========
LINE_NOTIFY_TOKEN = os.getenv('LINE_NOTIFY_TOKEN')
LINE_NOTIFY_API = 'https://notify-api.line.me/api/notify'
TARGET_URL = os.getenv('TARGET_URL', 'https://example.com')

# スクリーンショット保存先
SCREENSHOT_DIR = Path('screenshots')
SCREENSHOT_DIR.mkdir(exist_ok=True)

# 監視設定
CHECK_INTERVAL = 30  # 秒単位で再チェック
MAX_RETRIES = 3      # 最大リトライ回数
TIMEOUT = 30000      # ミリ秒単位のタイムアウト

# ブラウザ設定
BROWSER_HEADLESS = True  # False にするとブラウザが表示される（デバッグ用）

LINE_CHANNEL_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
def send_stock_notification(message):
    """
    友だち登録者全員に在庫通知を送信
    """
    url = "https://api.line.me/v2/bot/message/broadcast"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_CHANNEL_TOKEN}'
    }
    
    data = {
        'messages': [
            {
                'type': 'text',
                'text': message
            }
        ]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        print("✅ LINE通知送信成功")
    else:
        print(f"❌ エラー: {response.text}")
    
    return response.status_code == 200


def send_line_notification(message, image_path=None):
    """
    LINE Notifyで通知を送信
    
    Args:
        message: 送信するメッセージ
        image_path: 添付する画像のパス（オプション）
    """
    if not LINE_NOTIFY_TOKEN:
        print("❌ LINE Notifyトークンが設定されていません")
        return False
    
    headers = {'Authorization': f'Bearer {LINE_NOTIFY_TOKEN}'}
    data = {'message': message}
    files = {}
    
    if image_path and os.path.exists(image_path):
        files = {'imageFile': open(image_path, 'rb')}
    
    try:
        print("📤 LINE通知を送信中...")
        response = requests.post(
            LINE_NOTIFY_API,
            headers=headers,
            data=data,
            files=files
        )
        
        if files:
            files['imageFile'].close()
        
        if response.status_code == 200:
            print("✅ LINE通知の送信完了")
            return True
        else:
            print(f"❌ LINE通知の送信失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ LINE通知エラー: {e}")
        return False


def monitor_website():
    print("🚀 Chrome起動中...")
    
    # 一時プロファイルを作成
    user_data_dir = tempfile.mkdtemp()
    
    options = uc.ChromeOptions()
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--headless')  # ヘッドレスは使わない

    time.sleep(2) 
    
    try:
        driver = uc.Chrome(
            options=options,
            version_main=139,
            use_subprocess=False  # Falseに変更
        )
        print("✅ ドライバー初期化成功")
        
        # ログインページへ
        driver.get('https://www.popmart.com/jp/user/login')
        time.sleep(5)
        
        # 地域選択（必要に応じて）
        try:
            ip_country = driver.find_element(By.XPATH, "//div[contains(@class, 'index_ipInConutry')]")
            ip_country.click()
            time.sleep(2)
        except:
            pass
        
        # ポリシー同意
        try:
            policy_btn = driver.find_element(By.XPATH, "//div[contains(@class, 'policy_acceptBtn')]")
            policy_btn.click()
            time.sleep(2)
        except:
            pass
        
        # チェックボックス
        checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox' and @class='ant-checkbox-input']")
        checkbox.click()
        time.sleep(1)
        
        # メールアドレス入力
        email_input = driver.find_element(By.ID, "email")
        email_input.send_keys(os.getenv('EMAIL_ADDRESS'))
        time.sleep(1)
        
        # 続行ボタン
        continue_btn = driver.find_element(By.XPATH, "//button[@type='button' and contains(text(), '続行')]")
        continue_btn.click()
        time.sleep(3)
        
        # パスワード入力
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_input.send_keys(os.getenv('PASSWORD'))
        time.sleep(1)
        
        # サインインボタン
        signin_btn = driver.find_element(By.XPATH, "//button[@type='submit' and contains(text(), 'サインイン')]")
        signin_btn.click()
        
        print("✅ ログイン試行完了")
        time.sleep(2)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class, 'index_cartItem')]"
            ))
        )

        cart_element = driver.find_element(By.XPATH, "//div[contains(@class, 'index_cartItem')]")
        
        # 成功確認
        if cart_element:
            print("✅ ログイン成功！")
        
        #あらかじめカートに入れられる場合
        cart_element.click()

        found_available = False

        while not found_available:
            print('ループ開始')

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[starts-with(@class, 'product_checkbox') and not(contains(@class, 'Disabled'))]"
                ))
            )

            checkboxes = driver.find_elements(
                By.XPATH,
                "//div[starts-with(@class, 'product_checkbox') and not(contains(@class, 'Disabled')) and not(contains(@class, 'Container')) and not(*)]"
            )

            if len(checkboxes) > 0:
                print(f"✅ {len(checkboxes)}個の有効なチェックボックスを発見！")
                found_available = True

                # 商品名を取得（有効な商品のみ）
                product_names = []
                try:
                    # すべての商品コンテナを取得
                    product_containers = driver.find_elements(
                        By.XPATH,
                        "//div[contains(@class, 'product_checkboxContainer')]"
                    )
                    
                    for container in product_containers:
                        # 有効なチェックボックスを持つコンテナのみ処理
                        checkbox = container.find_elements(
                            By.XPATH,
                            ".//div[starts-with(@class, 'product_checkbox__')]"
                        )
                        
                        if checkbox:  # 有効なチェックボックスがある場合
                            # 隣接する商品名を取得
                            try:
                                product_name = container.find_element(
                                    By.XPATH,
                                    "following-sibling::div//div[contains(@class, 'product_productName')]"
                                ).text
                                product_names.append(product_name)
                            except:
                                pass
                                
                except Exception as e:
                    print(f"商品名取得エラー: {e}")

                # # スクリーンショット
                # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # screenshot_path = f"screenshots/stock_found_{timestamp}.png"

                # LINE通知メッセージ作成
                message = f"""
                🎯 POP MART 在庫復活！
                
                ✅ 購入可能商品: {len(checkboxes)}個
                
                📦 商品リスト:
                {chr(10).join(['・' + name for name in product_names]) if product_names else '商品名取得失敗'}
                
                🕐 {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
                🛒 自動購入処理を開始...
                """
                
                # 通知送信
                send_stock_notification(message)
                
                # チェックボックスをクリック
                for checkbox in checkboxes:
                    try:
                        checkbox.click()
                        time.sleep(0.3)
                    except:
                        continue
                
                break
            
            if not found_available:
                time.sleep(random.uniform(0.4, 0.7))
                driver.refresh()
        
        checkout_button = driver.find_element(
            By.XPATH,
            "//button[contains(text(), '購入手続きへ')]"
        )
        checkout_button.click()

        # ページ遷移を待つ（重要）
        time.sleep(3)
        WebDriverWait(driver, 10).until(
            EC.url_contains("order-confirmation")  # URLが変わるまで待つ
        )

        # ローディング要素が消えるまで待つ（正確なクラス名）
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.XPATH, "//div[@class='index_loadingWrapFull__LhIPV']"))
            )
        except:
            pass

        # レジに進むボタンをJavaScriptで強制クリック
        try:
            processing_checkout_button = driver.find_element(
                By.XPATH, 
                "//button[@class='ant-btn ant-btn-primary ant-btn-dangerous index_placeOrderBtn__E2dbt']"
            )
            
            # JavaScriptで強制クリック（ローディングを無視）
            driver.execute_script("arguments[0].click();", processing_checkout_button)
            print("✅ レジに進むボタンをクリック（JavaScript）")
            
        except Exception as e:
            # それでもダメなら待ってから再試行
            time.sleep(5)
            processing_checkout_button = driver.find_element(
                By.XPATH,
                "//button[contains(text(), 'レジに進む')]"
            )
            driver.execute_script("arguments[0].click();", processing_checkout_button)


        print('a')

        # 検索しなければならない場合
        # Mollyテキストをクリック
        search_element = driver.find_element(By.XPATH, "//div[@class='header_hotText__xrk9k']")
        search_element.click()
        time.sleep(1)

        # 検索ボックスが表示されるまで待つ
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[contains(@class, 'search_searchInput')]"))
        )

        # テキストを入力
        search_box.clear()  # 既存のテキストをクリア
        search_box.send_keys("Lil Peach Riot Sleepover シリーズ")

        # Enterキーで検索実行（必要に応じて）
        time.sleep(1)
        search_icon = driver.find_element(By.XPATH, "//div[contains(@class, 'search_searchIconContainer')]")
        search_icon.click() 
        print('a')
        
    except Exception as e:
        print(f"エラー: {e}")
    
    finally:
        input("Enterキーを押すとブラウザを閉じます...")
        driver.quit()


# screenshot_page関数もasyncにする
async def screenshot_page(page):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"✅ スクリーンショット保存: {screenshot_path}")

async def handle_google_login(new_page):
    """Googleログインページでの操作"""
    
    # 新しいタブが完全に読み込まれるまで待つ
    await new_page.wait_for_load_state("domcontentloaded")
    
    # メールアドレス入力
    await new_page.fill('input#identifierId', os.getenv('GOOGLE_EMAIL'))
    await new_page.click('button:has-text("次へ")')
    
    await new_page.wait_for_timeout(2000)
    
    await screenshot_page(new_page)
    # パスワード入力
    await new_page.wait_for_selector('input[type="password"]', state="visible")
    await new_page.fill('input[type="password"]', os.getenv('GOOGLE_PASSWORD'))
    await new_page.click('button:has-text("次へ")')
    
    # 認証後、元のサイトにリダイレクトされるまで待つ
    await new_page.wait_for_url("**/popmart.com/**", timeout=30000)
    
    print(f"ログイン完了！現在のURL: {new_page.url}")
    return new_page

async def click_google_login_advanced(page):
    """改良版Googleログインクリック"""
    
    print("Googleログインを試行中...")
    
    # 現在のページ数を記録
    pages_before = len(page.context.pages)
    
    # 人間らしい動作でクリック
    await human_like_google_click(page)
    
    # 3秒待つ
    await page.wait_for_timeout(3000)
    
    # ページ数が増えたか確認（新しいタブ）
    pages_after = len(page.context.pages)
    
    if pages_after > pages_before:
        # 新しいタブが開いた
        new_page = page.context.pages[-1]
        print(f"新しいタブ検出: {new_page.url}")
        return new_page
    elif page.url != LOGIN_URL:
        # 同じタブで遷移した
        print(f"ページ遷移成功: {page.url}")
        return page
    else:
        print("クリックしたが遷移しませんでした")
        # デバッグ情報を出力
        console_logs = []
        page.on("console", lambda msg: console_logs.append(msg.text))
        await page.wait_for_timeout(1000)
        if console_logs:
            print(f"コンソールログ: {console_logs}")
        return None

async def human_like_google_click(page):
    """人間らしい動作でクリック"""
    
    # ランダムな位置にマウスを動かす
    await page.mouse.move(100, 100)
    await page.wait_for_timeout(random.randint(500, 1000))
    
    # Googleアイコンまでゆっくり移動
    google_element = page.locator('.index_loginIcon__KGxWn').nth(1)
    box = await google_element.bounding_box()
    
    if box:
        # 段階的にマウスを移動
        steps = 10
        start_x, start_y = 100, 100
        end_x = box['x'] + box['width'] / 2
        end_y = box['y'] + box['height'] / 2
        
        for i in range(steps):
            progress = (i + 1) / steps
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress
            await page.mouse.move(x, y)
            await page.wait_for_timeout(50)
        
        # クリック
        await page.mouse.down()
        await page.wait_for_timeout(random.randint(50, 150))
        await page.mouse.up()
        
        print(f"人間らしくクリック完了: ({end_x}, {end_y})")

async def monitor_network(page):
    """ネットワークリクエストを監視してOAuth URLを取得"""
    
    oauth_url = None
    
    def handle_request(request):
        nonlocal oauth_url
        if 'accounts.google.com' in request.url or 'oauth' in request.url:
            oauth_url = request.url
            print(f"OAuth URL検出: {oauth_url}")
    
    page.on("request", handle_request)
    
    # Googleアイコンをクリック
    await click_google_with_force(page)
    await page.wait_for_timeout(3000)
    
    if oauth_url:
        # 直接OAuth URLに遷移
        await page.goto(oauth_url)

async def click_google_login(page):
    """インデックス2の要素を確実にクリック"""
    
    # まず通常のPlaywrightクリックを試す
    try:
        google_element = page.locator('.index_loginIcon__KGxWn').nth(1)  # 0始まりなので1が2番目
        await google_element.click()
        print("Playwrightクリック実行")
    except:
        pass
    
    await page.wait_for_timeout(2000)
    
    # ページが遷移したか確認
    current_url = page.url
    print(f"現在のURL: {current_url}")
    
    # 遷移していない場合、Pointerイベントを試す
    if "login" in current_url:
        await click_google_with_mouse(page)

async def click_google_with_mouse(page):
    """マウス座標で直接クリック"""
    
    # 要素の座標を取得
    google_element = page.locator('.index_loginIcon__KGxWn').nth(1)
    box = await google_element.bounding_box()
    
    if box:
        # 中心座標を計算
        x = box['x'] + box['width'] / 2
        y = box['y'] + box['height'] / 2
        
        # マウスを移動してクリック
        await page.mouse.move(x, y)
        await page.wait_for_timeout(500)
        await page.mouse.click(x, y)
        print(f"座標 ({x}, {y}) をクリック")

async def click_google_with_force(page):
    """強制的にクリックイベントを発火"""

    print("🚀 強制的にクリックイベントを発火")
    
    # まず要素にフォーカス
    google_element = page.locator('.index_loginIcon__KGxWn').nth(1)
    await google_element.focus()
    await page.wait_for_timeout(100)
    
    # Enterキーを押す
    await page.keyboard.press('Enter')
    
    # それでもダメなら座標クリックを複数回
    box = await google_element.bounding_box()
    if box:
        x = box['x'] + box['width'] / 2
        y = box['y'] + box['height'] / 2
        
        # ダブルクリック
        await page.mouse.dblclick(x, y)

async def click_with_pointer_events(page):
    """PointerEventを使ってクリック"""
    
    result = await page.evaluate("""
        () => {
            const elements = document.querySelectorAll('.index_loginIcon__KGxWn');
            if (elements.length >= 2) {
                const googleIcon = elements[1];  // 2番目の要素（Googleアイコン）
                
                // 要素の位置を取得
                const rect = googleIcon.getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                
                // PointerEventを作成して発火
                const pointerdown = new PointerEvent('pointerdown', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                const pointerup = new PointerEvent('pointerup', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                const click = new PointerEvent('click', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                
                googleIcon.dispatchEvent(pointerdown);
                googleIcon.dispatchEvent(pointerup);
                googleIcon.dispatchEvent(click);
                
                return 'PointerEvent発火完了';
            }
            return '要素が見つかりません';
        }
    """)
    
    print(f"結果: {result}")

async def debug_find_google_icon(page):
    """ページ内の画像要素をデバッグ"""
    
    images_info = await page.evaluate("""
        () => {
            const images = document.querySelectorAll('img');
            const result = [];
            images.forEach((img, index) => {
                result.push({
                    index: index,
                    src: img.src,
                    alt: img.alt,
                    className: img.className,
                    parentClassName: img.parentElement?.className
                });
            });
            return result;
        }
    """)
    
    print("=== ページ内の画像一覧 ===")
    for img in images_info:
        if 'google' in img['src'].lower():
            print(f"🎯 Google画像発見: {img}")
    
    return images_info

async def find_clickable_elements(page):
    """クリック可能な要素を探す"""
    
    clickable = await page.evaluate("""
        () => {
            // ログインアイコンのクラスを持つ要素を探す
            const elements = document.querySelectorAll('[class*="loginIcon"], [class*="otherLogin"]');
            const result = [];
            
            elements.forEach((el, index) => {
                result.push({
                    index: index,
                    tagName: el.tagName,
                    className: el.className,
                    innerHTML: el.innerHTML.substring(0, 200),
                    hasGoogleText: el.innerHTML.includes('google')
                });
            });
            
            return result;
        }
    """)
    
    print("=== クリック可能な要素 ===")
    for el in clickable:
        print(f"要素 {el['index']}: {el['className']}")
        if el['hasGoogleText']:
            print(f"  → Googleテキストを含む！")
    
    return clickable


if __name__ == "__main__":
    monitor_website()