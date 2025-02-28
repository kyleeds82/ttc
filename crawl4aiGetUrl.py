import asyncio
import json
import os
from pathlib import Path
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

#SMS_CODE_PATH = "C:\\Users\\KTDS\\Downloads\\urlcompare\\crawl4ai_url\\sms_code.txt"
#USER_DATA_DIR = "C:\\Users\\KTDS\\Downloads\\urlcompare\\crawl4ai_url\\user-data"
#STORAGE_STATE_PATH_A = "C:\\Users\\KTDS\\Downloads\\urlcompare\\crawl4ai_url\\user-data\\storage_state_a.json"
#STORAGE_STATE_PATH_B = "C:\\Users\\KTDS\\Downloads\\urlcompare\\crawl4ai_url\\user-data\\storage_state_b.json"
#PLAYWRIGHT_CHROMIUM_PATH = "C:\\Users\\KTDS\\AppData\\Local\\ms-playwright\\chromium-1148\\chrome-win\\chrome.exe"

SMS_CODE_PATH = "crawl4ai_url/sms_code_crawl4ai.txt"
TWO_FA_CODE_A= "twoFA_code.txt"
SMS_CODE_PATH_B = "crawl4ai_url/sms_code_crawl4ai_b.txt"

USER_DATA_DIR = "crawl4ai_url/user-data"
STORAGE_STATE_PATH_A = "crawl4ai_url/user-data/storage_state_a.json"
STORAGE_STATE_PATH_B = "crawl4ai_url/user-data/storage_state_b.json"

async def close_dialog(dialog):
            print(f"팝업 메시지: {dialog.message}")
            await dialog.accept()
            print("팝업 닫힘")

async def check_sms_code(txt_path, interval=5):
    while not Path(txt_path).exists():
        print("SMS 코드 파일 없음")
        await asyncio.sleep(interval)
    print("SMS 코드 파일 확인")

def get_domain_name(url):
    parseUrl = urlparse(url)
    hostname = parseUrl.hostname
    return hostname.replace(".", "_")

def get_domain_url(enter_url):
    parsed_url = urlparse(enter_url)
    return parsed_url.netloc

def filter_urls(enter_urls, filter_domain):
    filtered = []
    for enter_url in enter_urls:
        parsed_url = urlparse(enter_url)

        # url이 domain과 불일치 제거
        if filter_domain not in parsed_url.netloc:
            continue

        # http, https가 아니거나 javascript링크가 포함되면 제거
        if parsed_url.scheme not in ["http", "https"] or "javascript" in enter_url:
            continue

        # #문자가 있으면 뒷 부분 버리고 앞 부분 도메인:포트만 저장
        clean_url = enter_url.split("#")[0]

        # 중복되면 저장하지 않음
        if clean_url not in filtered:
            filtered.append(clean_url)
    return filtered

# 에러 로그 기록 함수
def log_error(step, exception):
    error_message = f"{step} - 오류 발생: {str(exception)}\n"
    error_message += traceback.format_exc() + "\n"
    
    # 로그를 파일에 기록
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(error_message)
    
    print(error_message)


#async def save_login_state(url_a):
async def save_login_state(url_a, url_b):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,  
                headless=True,
                ignore_https_errors=True,
                locale="ko-KR"
            )

            page = await browser.new_page()
            await asyncio.sleep(5)

            await page.goto(url_a)
            await asyncio.sleep(5)
            await page.screenshot(path="result_sshot/move_to_url_a.png", full_page=False)

            await asyncio.sleep(5)

            iframe = page.frame_locator("#wrap > iframe")
            await iframe.locator('input[placeholder="사원번호 입력"]').fill('82107083')
            await iframe.locator('input[placeholder="사원번호 입력"]').press("Tab")
            await asyncio.sleep(1)
            await iframe.locator('input[placeholder="비밀번호 입력"]').fill('csr06806!!')
            await asyncio.sleep(1)
            await page.screenshot(path="result_sshot/enter_idpw_a.png", full_page=False)
            await iframe.locator('input[placeholder="비밀번호 입력"]').press("Enter")
            await asyncio.sleep(5)

            otp_element = iframe.locator("h3:has-text('OTP 인증 안내')")
            if await otp_element.is_visible():
                await check_sms_code(SMS_CODE_PATH)
                sms_code_a = Path(SMS_CODE_PATH).read_text(encoding="utf-8").strip()
                print(f"인증번호: {sms_code_a}")
                await iframe.locator('input[placeholder="인증번호 입력"]', sms_code_a)
                await asyncio.sleep(1)
                await iframe.locator('input[placeholder="인증번호 입력"]').press("Enter")
                await asyncio.sleep(1)
            else:
                print("Don't need OTP")

            await asyncio.sleep(5)
            await page.screenshot(path="result_sshot/after_login_a.png", full_page=False)
            await asyncio.sleep(1)
            await page.goto("https://security.kt.co.kr")
            print("security 도메인 이동 성공")
            await asyncio.sleep(10)
            await page.screenshot(path="result_sshot/security_url_a.png", full_page=False)

            currentUrl_a = page.url
            getDomainName_a=get_domain_name(currentUrl_a)

            cookies_a = await browser.cookies()
            cookie_path_a = USER_DATA_DIR+f"/cookies_{getDomainName_a}.json"
            with open(cookie_path_a, "w", encoding="utf-8") as f:
                json.dump(cookies_a, f, indent=4)
            await browser.storage_state(path=STORAGE_STATE_PATH_A)

            print("1번째 도메인 로그인 처리 완료")

            await asyncio.sleep(5)
            await page.goto(url_b)
            await asyncio.sleep(5)
            await page.goto(url_b)
            print("move to success URL_B")
            await asyncio.sleep(20)
            await page.screenshot(path="result_sshot/move_to_url_b.png", full_page=False)
            page.on("dialog", close_dialog)
            await asyncio.sleep(5)
            await page.screenshot(path="result_sshot/close_dialog_b.png", full_page=False)

            await page.fill('input[name="loginfmt"]', 'soorin.choi@kt.com')
            await asyncio.sleep(1)
            await page.screenshot(path="result_sshot/enter_id_b.png", full_page=False)
            await page.click("#idSIButton9"); 
            await asyncio.sleep(10)
 
            await page.fill('input[type="password"]', 'csr06806!!')
            await asyncio.sleep(1)
            await page.screenshot(path="result_sshot/enter_pw_b.png", full_page=False)
            await page.click("#idSIButton9"); 
            await asyncio.sleep(10)
            await page.screenshot(path="result_sshot/after_pw_b.png", full_page=False)

            if await page.locator('#idSIButton9').is_visible():
                await page.click('#idSIButton9')
                await asyncio.sleep(3)
            elif await page.locator('#tileList > div:nth-child(2) > div > button').is_visible():
                await page.click('#tileList > div:nth-child(2) > div > button')
                await asyncio.sleep(3)
            elif await page.locator('button[type="submit"]').is_visible():
                await page.click('button[type="submit"]')
                await asyncio.sleep(3)
            else:
                await page.keyboard.press("Enter")
                print("Enter Press")

            await asyncio.sleep(10)
            html_content_1b = await page.content()
            with open("after_pw_b.html", "w", encoding="utf-8") as f:
                f.write(html_content_1b)
            print("HTML 저장 완료")
            await asyncio.sleep(1)

            if await page.locator('#idSIButton9').is_visible():
                await page.click('#idSIButton9')
                await asyncio.sleep(3)
            elif await page.locator('#tileList > div:nth-child(2) > div > button').is_visible():
                await page.click('#tileList > div:nth-child(2) > div > button')
                await asyncio.sleep(3)
            elif await page.locator('button[type="submit"]').is_visible():
                await page.click('button[type="submit"]')
                await asyncio.sleep(3)
            else:
                await page.keyboard.press("Enter")
                print("Enter Press")
            await asyncio.sleep(5)
            await page.screenshot(path="result_sshot/otp_url_b.png", full_page=False)
            await asyncio.sleep(10)
            html_content_2b = await page.content()
            with open("otp_url_b.html", "w", encoding="utf-8") as f:
                f.write(html_content_2b)
            print("HTML 저장 완료")

            otp_element_b = page.locator("#idTxtBx_SAOTCC_OTC")
            if await otp_element_b.is_visible():
                await check_sms_code(SMS_CODE_PATH_B)
                sms_code_b = Path(SMS_CODE_PATH_B).read_text(encoding="utf-8").strip()
                print(f"인증번호: {sms_code_b}")
                await otp_element_b.fill(sms_code_b)
                await page.screenshot(path="result_sshot/input_otp_b.png", full_page=False)
                await asyncio.sleep(1)

                check_box_b = page.locator("#idChkBx_SAOTCC_TD")
                if await check_box_b.is_visible():
                    await check_box_b.click()
                    await asyncio.sleep(1)
                else:
                    print("No check box")
                    await asyncio.sleep(1)

                if await page.locator('#idSIButton9').is_visible():
                    await page.click('#idSIButton9')
                    await asyncio.sleep(3)
                elif await page.locator('#tileList > div:nth-child(2) > div > button').is_visible():
                    await page.click('#tileList > div:nth-child(2) > div > button')
                    await asyncio.sleep(3)
                elif await page.locator('button[type="submit"]').is_visible():
                    await page.click('button[type="submit"]')
                    await asyncio.sleep(3)
                else:
                    await page.keyboard.press("Enter")
                    print("Enter Press")

                await asyncio.sleep(10)
                await page.screenshot(path="result_sshot/step_1b.png", full_page=False)

            else:
                print("Don't need SMS code")
            await asyncio.sleep(10)

            if await page.locator('#idSIButton9').is_visible():
                await page.click('#idSIButton9')
                await asyncio.sleep(3)
            elif await page.locator('#tileList > div:nth-child(2) > div > button').is_visible():
                await page.click('#tileList > div:nth-child(2) > div > button')
                await asyncio.sleep(3)    
            else:
                print("Don't need button click")

            await asyncio.sleep(10)
            after_login_b = await page.content()
            with open("after_login_b.html", "w", encoding="utf-8") as f:
                f.write(after_login_b)
            print("HTML 저장 완료")

            await page.screenshot(path="result_sshot/after_login_b.png", full_page=False)
            await asyncio.sleep(2)

            currentUrl_b = page.url
            getDomainName_b=get_domain_name(currentUrl_b)

            cookies_b = await browser.cookies()
            cookie_path_b = USER_DATA_DIR+f"/cookies_{getDomainName_b}.json"
            with open(cookie_path_b, "w", encoding="utf-8") as f:
                json.dump(cookies_b, f, indent=4)
            await browser.storage_state(path=STORAGE_STATE_PATH_B)

            print("2번째 도메인 로그인 처리 완료")
            await asyncio.sleep(3)
            await page.close()
        
            return currentUrl_a, getDomainName_a, currentUrl_b, getDomainName_b
            #return currentUrl_a, getDomainName_a
    except Exception as e:
        log_error("로그인 프로세스 실패", e)

async def crawl4aiGetUrl(enter_crawl_url, storage_state_path, url_label):
    async with AsyncWebCrawler(
        headless=True,
        verbose=False,
        enable_click=True,
        max_depth=2,
        max_pages=100,
        delay=2,
        viewport_width=1280,
        viewport_height=720,
        storage_state=storage_state_path,
        user_data_dir=USER_DATA_DIR,
        #executable_path=PLAYWRIGHT_CHROMIUM_PATH,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    ) as crawler:
        try:
            result = await crawler.arun(
                url=enter_crawl_url,
                screenshot=False,
                wait_for="document.readyState === 'complete'",
                cache_mode=CacheMode.BYPASS,
            )
            print(f"{url_label} Crawl Success")
        except Exception as e:
            print(f"{url_label} Crawl Failed: {e}")
            return

        # 스크린샷 결과 저장
        #with open(f"C:\\Users\\KTDS\\Downloads\\urlcompare\\crawl4ai_url\\login_result_{url_label}.png", "wb") as f:
        #    f.write(b64decode(result.screenshot))

        # 원본 HTML 저장
        with open(f"crawl4ai_url/original_page_{url_label}.html", "w", encoding="utf-8") as f:
            f.write(result.html)
        print("Crawling result save as .html FILE")

        # HTML 내용 확인
        soup = BeautifulSoup(result.html, "html.parser")
        url_lists = []

        print(f"크롤링 시작 URL: {enter_crawl_url}")
        # 모든 <a> 태그의 href 추출
        for a_tag in soup.find_all("a", href=True):
            url = urljoin(result.url, a_tag["href"])
            url_lists.append(url)

        all_urls_path = f"crawl4ai_url/all_urls_{url_label}.txt"
        with open(all_urls_path, "w", encoding="utf-8") as f:
            f.write("\n".join(url_lists))

        # 중복 저장 안함
        if not url_lists:
            url_lists.append(enter_crawl_url)


        filter_domain = get_domain_url(enter_crawl_url)
        filtered_urls = filter_urls(url_lists, filter_domain)

        with open(f"crawl4ai_url/filtered_urls_{url_label}.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(filtered_urls))
        print("Filtering result save as .txt FILE")
        return filtered_urls

def convert_https(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines() 
    change_lines=[line.replace("http://", "https://") for line in lines if "logout.do" not in line]
    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(change_lines)
    print("https 변경 후 저장")

def compare_urls(list_a, list_b, compare_num):
    COMPARE_FILE_PATH = "crawl4ai_url/compare_list.txt"
    compare_number = compare_num

    select_a = list_a[:compare_number] if list_a else []
    select_b = list_b[:compare_number] if list_b else []

    with open(COMPARE_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(select_a + select_b))
    print("비교 리스트 저장 성공")
    convert_https(COMPARE_FILE_PATH)


#def compare_urls(list_a, compare_num):
#    COMPARE_FILE_PATH = "crawl4ai_url/compare_list.txt"
#    compare_number = compare_num
#
#    select_a = list_a[:compare_number] if list_a else []
#
#    with open(COMPARE_FILE_PATH, "w", encoding="utf-8") as f:
#        f.write("\n".join(select_a))
#    print("비교 리스트 저장 성공")
#    convert_https(COMPARE_FILE_PATH)


if __name__ == "__main__":
    #if len(sys.argv) < 2:
    #    print("play success crawl4aiGetUrl.py")
    #    sys.exit(1)
    #   
    #enter_url=sys.argv[1]
    #asyncio.run(crawl4aiGetUrl(enter_url))
    url_a, url_name_a, url_b, url_name_b = asyncio.run(save_login_state("http://kate.kt.com/", "https://dev-security.ktds.co.kr/"))
    #url_a, url_name_a = asyncio.run(save_login_state("https://onm-adplatform.kt.com/index.do"))
    top_list_a = asyncio.run(crawl4aiGetUrl(url_a, STORAGE_STATE_PATH_A, url_name_a))
    top_list_b = asyncio.run(crawl4aiGetUrl(url_b, STORAGE_STATE_PATH_B, url_name_b))
    compare_urls(top_list_a, top_list_b, 3)
