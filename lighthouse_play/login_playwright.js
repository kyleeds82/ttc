const { chromium } = require('playwright');  // Playwright 모듈 가져오기
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

(async () => {
  // URL 리스트 파일 경로 설정 (현재 경로 기준)
  const urlFilePath = path.join(__dirname, 'url_lists.txt');

  // URL 리스트 파일 읽기
  if (!fs.existsSync(urlFilePath)) {
    console.error('url_lists.txt 파일을 찾을 수 없습니다.');
    process.exit(1);
  }
  const urlList = fs.readFileSync(urlFilePath, 'utf-8')
    .split('\n') // 줄바꿈으로 분리
    .map(line => line.trim()) // 공백 제거
    .filter(line => line.length > 0); // 빈 줄 제거

  console.log('URL 리스트:', urlList);

  // Playwright 브라우저 인스턴스 생성
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/chromium'
    //executablePath: 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'  // Windows Chrome 설치 경로
  });

  // 새로운 페이지 열기
  const page = await browser.newPage();
  await page.goto('https://github.com/login');
  await page.fill('#login_field', '');
  await page.fill('#password', '');
  await page.click('[name="commit"]');
  await page.waitForNavigation();

  // 로그인 후 대기 (3초)
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'id_pw.png', fullPage: true });

  // Email 인증 페이지 확인
  try {
    // 로그인 성공 여부 확인 (ID/PW 성공)
    const topRepoExists = await page.locator('div.hide-sm.hide-md.mb-1.d-flex.flex-justify-between.flex-items-center h2:text("Top repositories")').count();
    if (topRepoExists > 0) {
      console.log('Login successful! Redirected to dashboard.');
    } else {
        const deviceVerificationExists = await page.locator('div.auth-form-header.p-0 > h1:text("Device verification")').count();
        if (deviceVerificationExists > 0) {
            console.log('Device verification required. Handling OTP...');   
    
            // github_email_verify.js 실행 및 인증 코드 가져오기
            const githubVerifyCode = await new Promise((resolve, reject) => {
              exec('node github_email_verify.js', (error, stdout, stderr) => {
                if (error) {
                  console.error(`Error executing github_email_verify.js: ${error.message}`);
                  return reject(error);
                }
                if (stderr) {
                  console.error(`Error output from github_email_verify.js: ${stderr}`);
                  return reject(new Error(stderr));
                }
                // stdout에서 인증 코드 추출
                const code = stdout.trim();
                console.log(`Received OTP: ${code}`);
                resolve(code);
              });
            });

            // OTP 입력
            await page.screenshot({ path: 'previous_code.png', fullPage: true });
            await page.fill('#otp', githubVerifyCode);
            await page.screenshot({ path: 'enter_code.png', fullPage: true });
            await page.waitForTimeout(5000);
        }
    }
  } catch (error) {
    console.error('An error occurred during the login process:', error.message);
    process.exit(1);
  }

  // 쿠키 저장
  const cookies = await page.context().cookies();
  fs.writeFileSync('./cookies.json', JSON.stringify(cookies, null, 2));

  //const cookiesFilePath = path.join(__dirname, 'cookies.json');
  //const cookiesContent = fs.readFileSync(cookiesFilePath, 'utf-8');
  //const cookies = JSON.parse(cookiesContent);

  // Lighthouse CI용 lighthouserc.json 생성
  const cookieHeader = cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ');
  const lhciConfig = {
    ci: {
      collect: {
        url: urlList, // 파일에서 읽은 URL 리스트 사용
        numberOfRuns: 1,
        settings: {
          output: ['html', 'json'],
          chromeFlags: '--no-sandbox --headless --disable-gpu --disable-dev-shm-usage',
          extraHeaders: {
            Cookie: cookieHeader
          }
        }
      },
      "upload": {
        target: 'filesystem',
        outputDir: './lighthouse-results',
      }
    }
  };

  // JSON 파일로 저장
  fs.writeFileSync('./lighthouserc.json', JSON.stringify(lhciConfig, null, 2));
  console.log('lighthouserc.json 생성 완료');

  // 스크린샷 저장
  await page.screenshot({ path: 'last_check.png', fullPage: true });
  await browser.close();
})();
