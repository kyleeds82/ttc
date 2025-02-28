const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');
const { URL } = require("url");

function getDomainName(url) {
  const hostname = new URL(url).hostname;
  const parts = hostname.split('.');

  // www로 시작하는 경우 제거
  if (parts[0] === "www") {
    return parts.slice(1).join('_');
  }
  
  return hostname.replace(/\./g, '_'); // .을 _로 변경
}

(async () => {
    const urlFilePath = path.join(__dirname, 'crawl4ai_url/compare_list.txt');

    if (!fs.existsSync(urlFilePath)) {
        console.error('compare_list.txt 파일을 찾을 수 없습니다.');
        process.exit(1);
    }
  
    const urlList = fs.readFileSync(urlFilePath, 'utf-8')
        .split('\n') // 줄바꿈으로 분리
        .map(line => line.trim()) // 공백 제거
        .filter(line => line.length > 0); // 빈 줄 제거

    await new Promise(resolve => setTimeout(resolve, 2000));


    const MAX_RUNS = 10;
    const limitedUrls = urlList.slice(0, MAX_RUNS);

    const lhciConfig = {
      ci: {
        collect: {
          puppeteerScript : './reload_chrome.js',
          url: limitedUrls,
          numberOfRuns: 1,
          puppeteerLaunchOptions: {
            executablePath: '/usr/bin/chromium',
            headless: true,
            userDataDir: './crawl4ai_url/user-data',
            ignoreHTTPSErrors: true,
            args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
          },
          settings: {
            preset: 'desktop',
            output: ['html', 'json'],
            chromeFlags: "--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new"

            }
          },
        "upload": {
          target: 'filesystem',
          outputDir: './lighthouse-results',
        }
      }
    }

    // JSON 파일로 저장
    fs.writeFileSync('./lighthouserc.json', JSON.stringify(lhciConfig, null, 2));
    console.log('lighthouserc.json 생성 완료');
})();
