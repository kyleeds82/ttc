import asyncio
import json
import os
import requests
from pathlib import Path
from base64 import b64decode
from crawl4ai import AsyncWebCrawler, CacheMode
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


#SMS_CODE_PATH = "C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\sms_code.txt"
#USER_DATA_DIR = "C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\user-data"
#STORAGE_STATE_PATH_A = "C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\user-data\\storage_state_a.json"
#STORAGE_STATE_PATH_B = "C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\user-data\\storage_state_b.json"
#
#PLAYWRIGHT_CHROMIUM_PATH = "C:\\Users\\KTDS\\AppData\\Local\\ms-playwright\\chromium-1148\\chrome-win\\chrome.exe"

#SMS_CODE_PATH_A = "crawl4ai_url/sms_code_crawl4ai.txt"
#TWO_FA_CODE_A= "twoFA_code.txt"
#
USER_DATA_DIR = "crawl4ai_url/user-data"
STORAGE_STATE_PATH_A = "crawl4ai_url/user-data/storage_state_a.json"
STORAGE_STATE_PATH_B = "crawl4ai_url/user-data/storage_state_b.json"

#SAVE_DIR = "crawl4ai_url/save_resource"

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

def convert_https(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines() 
    change_lines=[line.replace("http://", "https://") for line in lines if "logout.do" not in line]
    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(change_lines)
    print("https 변경 후 저장")


async def save_login_state(url_a):   
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,  
            headless=True,
            ignore_https_errors=True
        ) 
        page = await browser.new_page()
        await asyncio.sleep(5)
        await page.screenshot(path="result_sshot/open_browser_a.png", full_page=False)
        await page.goto(url_a)
        await asyncio.sleep(10)
        await page.screenshot(path="result_sshot/move_url_a.png", full_page=False)
        print("로그인 완료")
        currentUrl_a = page.url
        getDomainName_a=get_domain_name(currentUrl_a)

        cookies_a = await browser.cookies()
        cookies_path_a = USER_DATA_DIR+f"/cookies_{getDomainName_a}.json"
        
        with open(cookies_path_a, "w", encoding="utf-8") as f:
            json.dump(cookies_a, f, indent=4)
        await browser.storage_state(path=STORAGE_STATE_PATH_A)

        print("1번째 도메인 로그인 처리 완료")
        await asyncio.sleep(2)
        await page.close()
        print("currentUrl_a : ", currentUrl_a)
        print("getDomainName_a :", getDomainName_a)
        return currentUrl_a, getDomainName_a
        #return currentUrl_a, getDomainName_a, currentUrl_b, getDomainName_b


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
    ) as crawler, async_playwright() as p:
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
        #with open(f"C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\original_page_{url_label}.html", "w", encoding="utf-8") as f:
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

        #all_urls_path = f"C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\all_urls_{url_label}.txt"
        all_urls_path = f"crawl4ai_url/all_urls_{url_label}.txt"
        with open(all_urls_path, "w", encoding="utf-8") as f:
            f.write("\n".join(url_lists))

        # 중복 저장 안함
        if not url_lists:
            url_lists.append(enter_crawl_url)


        filter_domain = get_domain_url(enter_crawl_url)
        filtered_urls = filter_urls(url_lists, filter_domain)

        #with open(f"C:\\Users\\KTDS\\Downloads\\js_save-master\\js_save\\crawl4ai_url\\filtered_urls_{url_label}.txt", "w", encoding="utf-8") as f:
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


def compare_urls(list_a, compare_num):
    COMPARE_FILE_PATH = "crawl4ai_url/compare_list.txt"
    compare_number = compare_num

    select_a = list_a[:compare_number] if list_a else []

    with open(COMPARE_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(select_a))
    print("비교 리스트 저장 성공")
    convert_https(COMPARE_FILE_PATH)

if __name__ == "__main__":
    #if len(sys.argv) < 2:
    #    print("play success crawl4aiGetUrl.py")
    #    sys.exit(1)
    #   
    #enter_url=sys.argv[1]
    #asyncio.run(crawl4aiGetUrl(enter_url))
    #시작


    #url_a, url_name_a, url_b, url_name_b = asyncio.run(save_login_state("https://auth.ncloud.com/login", "https://shop.kt.com/mobile/products.do?&=&category=mobile"))
    
    # 첫 번째 도메인
    url_a, url_name_a = asyncio.run(save_login_state("https://dev-security.ktds.co.kr/"))
    top_list_a = asyncio.run(crawl4aiGetUrl(url_a, STORAGE_STATE_PATH_A, url_name_a))
    compare_urls(top_list_a, 3)

    # 두 번째 도메인
    #url_b, url_name_b = asyncio.run(save_login_state("https://auth.ncloud.com/login"))
    #filtered_urls_b = asyncio.run(crawl4aiGetUrl(url_b, STORAGE_STATE_PATH_B, url_name_b))
    #all_filtered_urls.extend(filtered_urls_b)
