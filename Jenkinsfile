pipeline {
    agent any

    environment {
         // true: Puppeteer 실행, false: Puppeteer 실행하지 않음
        NEED_PUPPETEER = "false"
        
        redmineApiKey = credentials('redmine_api_key') // Jenkins credential store에서 Redmine API 키를 가져옵니다.
        PATH = "/usr/local/bin:$PATH"
        NODE_PATH = "/usr/local/lib/node_modules"
    }

    stages {
        stage('Clone Repository') {
            steps {
                script {
                    env.repoName = env.WORKSPACE.tokenize('/').last()
                        .replaceAll('.git$', '')
                    echo "Repository Name: ${env.repoName}"
                    
                    sh 'rm -rf ./* ./.??*' // 모든 파일과 숨겨진 파일/폴더 삭제
                    sh "git clone http://eae1154ad0b52159e17616b675e9b31accecb7ab@gitea:3000/gitea/${repoName}.git ."
                    sh "git config --global user.name 'ttc'"
                    sh "git config --global user.email 'ttc@kt.com'"
                    sh 'git config --global --add safe.directory ${WORKSPACE}'
                    sh "git checkout master"

                    def currentTime = new Date().format("MM.dd HH:mm")
                    def logEntry = "Time: ${currentTime}\n"

                    sh "echo '${logEntry}' >> log.txt"
                    sh 'git add log.txt'
                    sh "git commit -m '${currentTime}'"
                    sh 'git push http://eae1154ad0b52159e17616b675e9b31accecb7ab@gitea:3000/gitea/${repoName}.git'
                    
                    // url_lists.txt에서 URL 읽기
                    //def urlFilePath = "${WORKSPACE}/url_lists.txt"
                    //if (!fileExists(urlFilePath)) {
                    //    echo "url_lists.txt 파일이 존재하지 않습니다: ${urlFilePath}"
                    //}
                    // 파일에서 URL 목록 읽기 및 환경 변수 설정
                    //def urlsContent = readFile(urlFilePath).trim()
                    //env.urls = urlsContent.replaceAll("[\\r\\n]+", ",")
                    //echo "Loaded URLs: ${env.urls}"
                }
            }
        }
        
        stage('Crawl4ai Before SMS code') {
            steps {
                script {
                    env.LHCI_BUILD_CONTEXT__CURRENT_HASH = sh(returnStdout: true, script: "git rev-parse HEAD").trim()
                    sh 'python3 crawl4ai_url/crawl4aiGetUrl.py &'
                }
            }
        }
        
        stage('Crawl4ai User Input SMS code') {
            steps {
                script {
                    timeout(time: 500, unit: 'SECONDS') {
                        sleep(120)
                        waitUntil {
                            def inputSMScode_crawl4ai = input(
                                message: 'Private Url 크롤링에 필요한 SMS 인증번호 입력하세요',
                                parameters: [string(name: 'SMS_CODE_crawl4ai', defaultValue: '', description: '')]
                            )
                            if (!inputSMScode_crawl4ai.isNumber() || inputSMScode_crawl4ai.length() != 6) {
                                error "다시 입력하세요"
                            }
                            writeFile(file: 'crawl4ai_url/sms_code_crawl4ai_b.txt', text: inputSMScode_crawl4ai)
                            echo "코드 저장: ${inputSMScode_crawl4ai}"
                        }
                    }
                }
            }
        }
        
        stage('Crawl4ai 종료 대기') {
            steps {
                script {
                    sh 'while pgrep -f "python3 crawl4ai_url/crawl4aiGetUrl.py"; do sleep 20; done'
                }
            }
        }
        
        stage('Puppeteer Before SMS code') {
            steps {
                script {
                    env.LHCI_BUILD_CONTEXT__CURRENT_HASH = sh(returnStdout: true, script: "git rev-parse HEAD").trim()
                    sh 'node autoLogin.js'
                }
            }
        }

        stage('Play LHCI') {
            steps {
                script {
                    sh 'lhci autorun'
                    sh 'lhci upload --target=lhci --serverBaseUrl="http://lhci:9003/" --token="5de52879-a73e-47a5-8943-6eb5494c79b0"'
                    sh 'node sep_score.js'
                }
            }
        }
    }
}
