import os, re, sys, time, random
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# ====== 按实际页面修改这里 ======
REF_URL      = "https://vpn.qianlink.link/?ref=DJOM9MBWAV"
SEL_EMAIL    = 'input[type="email"], input[name="email"]'
SEL_PASSWORD = 'input[type="password"]'              # 若有“确认密码”框会一并填写
SEL_CODE     = 'input[name="email_code"], input[placeholder*="验证码"]'
SEL_SEND     = 'button:has-text("发送"), button:has-text("获取")'
SEL_SUBMIT   = 'button[type="submit"], button:has-text("注册")'
TXT_REGISTER = "注册"                                  # 首页进入注册页的按钮文字
TXT_LINE     = "默认线路"                              # 控制台里默认线路入口文字
TXT_QR       = "二维码"
SEL_QR_TEXT  = "textarea, .qr-content, [class*=copy]"  # 弹窗里装订阅内容的元素
PASSWORD     = os.environ.get("REG_PASSWORD", "ChangeMe_12345")
DELAY        = (20, 40)                                 # 每个账号之间随机等待秒数
# ================================

def load_mail(path="mail.txt"):
    """格式: 邮箱----密码----client_id----refresh_token----分组"""
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split("----")
        if len(p) < 4:
            print("skip bad line:", p[0]); continue
        yield p[0], {"client_id": p[2], "refresh_token": p[3]}

def get_access_token(acct):
    r = requests.post(
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        data={"client_id": acct["client_id"], "grant_type": "refresh_token",
              "refresh_token": acct["refresh_token"]}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]

def wait_code(email, acct, since, timeout=150):
    at = get_access_token(acct)
    end = time.time() + timeout
    while time.time() < end:
        try:
            r = requests.get(
                "https://graph.microsoft.com/v1.0/me/messages",
                params={"$top": 10, "$orderby": "receivedDateTime desc",
                        "$select": "subject,body,receivedDateTime"},
                headers={"Authorization": f"Bearer {at}"}, timeout=20)
            r.raise_for_status()
            for m in r.json().get("value", []):
                if m["receivedDateTime"] < since:
                    continue
                text = m["subject"] + " " + re.sub(r"<[^>]+>", " ", m["body"]["content"])
                c = re.search(r"(?<!\d)(\d{4,8})(?!\d)", text)
                if c:
                    return c.group(1)
        except Exception as e:
            print("mail err:", e)
        time.sleep(5)
    raise TimeoutError("no code")

def run_one(pw, email, token):
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()
    try:
        page.goto(REF_URL, wait_until="networkidle")
        if page.locator(f'text="{TXT_REGISTER}"').count():
            page.locator(f'text="{TXT_REGISTER}"').first.click()
        page.fill(SEL_EMAIL, email)
        for p in page.locator(SEL_PASSWORD).all():
            p.fill(PASSWORD)
        if page.locator(SEL_SEND).count():
            since = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            page.locator(SEL_SEND).first.click()
            page.fill(SEL_CODE, wait_code(email, token, since))
        page.locator(SEL_SUBMIT).first.click()
        page.wait_for_url(re.compile(r"(dashboard|console|user)"), timeout=30000)
        page.get_by_text(TXT_LINE).first.click()
        page.get_by_text(TXT_QR).first.click()
        page.wait_for_selector(SEL_QR_TEXT, timeout=10000)
        el = page.locator(SEL_QR_TEXT).first
        content = (el.input_value() if el.evaluate("e=>e.tagName") == "TEXTAREA" else el.inner_text()).strip()
        return content
    finally:
        browser.close()

def main():
    with sync_playwright() as pw, open("data.txt", "a", encoding="utf-8") as out:
        for email, token in load_mail():
            try:
                c = run_one(pw, email, token)
                out.write(c + "\n"); out.flush()
                print("OK", email)
            except Exception as e:
                print("FAIL", email, e)
            time.sleep(random.uniform(*DELAY))

if __name__ == "__main__":
    main()
