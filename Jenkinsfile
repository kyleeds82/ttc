def loadConfig() {
    def config = readYaml file: 'ttc_config'
    return config
}

def setupStages(config) {
    echo "Setting up configuration..."
    config.each { subProject ->
        echo "Folder: ${subProject.FOLDER ?: 'root'}"
        echo "Build Tool: ${subProject.BUILD_TOOL}"
        echo "Test Tool(s): ${subProject.TEST_TOOL}"
        echo "SonarQube Analysis: ${subProject.SONARQUBE_ANALYSIS}"
    }
}

def parallelBuildTestQualityGate(config) {
    def branches = [:]
    config.each { subProject ->
        def folder = subProject.FOLDER ?: '.'
        def repoName = folder.tokenize('/').last().replaceAll('.git$', '')
        if (folder == '.') {
            def gitUrl = sh(script: 'git remote get-url origin', returnStdout: true).trim()
            repoName = gitUrl.tokenize('/').last().replaceAll('.git$', '')
        } else {
            repoName = folder.tokenize('/').last().replaceAll('.git$', '')
        }

        def buildTool = subProject.BUILD_TOOL
        def testTools = subProject.TEST_TOOL
        branches["${repoName}"] = {                 
            stage("Build - ${repoName}") {
                echo "Building ${repoName} with ${buildTool}"
                script {
                    def startTime = System.currentTimeMillis()
                    def buildResult = 'SUCCESS'
                    try {
                        echo "Starting Build stage at: ${new Date(startTime)}"
                        if (buildTool == 'gradle') {
                            sh """
                                cd ${folder}
                                chmod +x ./gradlew
                                ./gradlew clean build -x test
                            """
                        } else if (buildTool == 'maven') {
                            sh "cd ${folder} && ${MVN_HOME}/bin/mvn clean install -Dmaven.test.skip=true -Drat.skip=true"
                        } else {
                            error "Unsupported build tool: ${buildTool}. Pipeline stopped."
                        }
                    } catch (Exception e) {
                        buildResult = 'FAILURE'
                        currentBuild.result = 'FAILURE'
                    } finally {
                        def endTime = System.currentTimeMillis()
                        def duration = (endTime - startTime) / 1000
                        def durationInt = duration.toInteger()

                        def hours = (durationInt / 3600).toInteger()
                        def minutes = ((durationInt % 3600) / 60).toInteger()
                        def seconds = (durationInt % 60).toInteger()

                        def formattedDuration = String.format("%02d:%02d:%02d", hours, minutes, seconds)

                        echo "Build stage completed at: ${new Date(endTime)}"
                        echo "Build stage took: ${formattedDuration}"

                        def redmineIssueTitle = "[${repoName}][Build][${currentBuild.number}]-[${buildResult}]"
                        def redmineIssueDescription = """
- Build Result: ${buildResult}
- Build Start Time: ${new Date(startTime).format('yyyy-MM-dd HH:mm:ss')}
- Build Duration: ${formattedDuration}
- Build Number: ${currentBuild.number}
"""

                        def redmineIssueData = [
                            issue: [
                                project_id: 1,
                                tracker_id: 1,
                                subject: redmineIssueTitle,
                                description: redmineIssueDescription
                            ]        
                        ]

                        httpRequest(
                            httpMode: 'POST',
                            url: 'http://redmine:3000/issues.json',
                            acceptType: 'APPLICATION_JSON',
                            contentType: 'APPLICATION_JSON',
                            customHeaders: [[name: 'X-Redmine-API-Key', value: redmineApiKey]],
                            requestBody: groovy.json.JsonOutput.toJson(redmineIssueData)
                        )
                    }
                }
            }

            stage("Test - ${repoName}") {
                echo "Testing ${repoName} with ${testTools}"
                script {
                    def xmlFiles

                    if (testTools.contains('junit')) {
                        try {
                            if (buildTool == 'gradle') {
                                sh "cd ${folder} && ./gradlew test"
                                sh "ls -R build/test-results/test"
                                junit "build/test-results/test/**/*.xml"
                                xmlFiles = findFiles(glob: "build/test-results/test/**/*.xml")
                            } else if (buildTool == 'maven') {
                                sh "cd ${folder} && ${MVN_HOME}/bin/mvn test -Drat.skip=true"
                                sh "ls -R target/surefire-reports"
                                junit "target/surefire-reports/*.xml"
                                xmlFiles = findFiles(glob: "target/surefire-reports/*.xml")
                            }
                        } catch (Exception e) {
                            currentBuild.result = 'FAILURE'
                        }
                    }

                    try {
                        def formattedJobPath = "job/${env.JOB_NAME.replace('/', '/job/')}"
                        echo "${formattedJobPath}"
                        def curlUrl = "jenkins:8080/${formattedJobPath}/${currentBuild.number}/testReport/api/json"

                        def junitReportJson = sh(
                            script: """ 
                                curl -u admin:${jenkinsApiKey} ${curlUrl}
                            """,
                            returnStdout: true
                        ).trim()

                        writeFile file: 'jenkins_junit.json', text: junitReportJson
                        def giteaUrl = "http://localhost:14000/gitea/${repoName}"
                        def summaryOutput = sh(
                            script: "sh ./junit_result.sh ${giteaUrl}",
                            returnStdout: true
                        ).trim()

                        def junitSummary = readFile('redmine_junit.txt').trim()
                        // JUnit Reports ZIP 생성
                        def junitReportPath = ""
                        def junitZipPath = ""
                        
                        if (buildTool == 'gradle') {
                            junitReportPath = "${folder}/build/test-results/test/"
                            junitZipPath = "${folder}/build/test-results/test/junit_results.zip"
                        } else if (buildTool == 'maven') {
                            junitReportPath = "${folder}/target/surefire-reports/"
                            junitZipPath = "${folder}/target/surefire-reports/junit_results.zip"
                        } else {
                            echo "Unsupported build tool: ${buildTool}"
                        }

                        sh """
                            cd ${junitReportPath}
                            zip -r junit_results *.xml
                        """

                        def uploadFileToRedmine = { filePath ->
                            try {
                                def uploadResponse = sh(
                                    script: """
                                    curl -X POST "http://redmine:3000/uploads.json" \
                                        -H "X-Redmine-API-Key: ${redmineApiKey}" \
                                        -H "Content-Type: application/octet-stream" \
                                        --data-binary @${filePath} \
                                        -s -o upload_response.json -w "%{http_code}"
                                    """,
                                    returnStdout: true
                                ).trim()

                                if (uploadResponse == "201") {
                                    def responseJson = readJSON file: 'upload_response.json'
                                    echo "Upload Token: ${responseJson.upload.token}"
                                    return responseJson.upload.token
                                } else {
                                    echo "Failed to upload file to Redmine. HTTP response: ${uploadResponse}"
                                }
                            } catch (Exception e) {
                                echo "Failed to upload file to Redmine: ${e.message}"
                            }
                        }
                        
                        // JUnit ZIP 파일 업로드 및 토큰 획득
                        //def junitToken = uploadFileToRedmine("${folder}/target/surefire-reports/junit_results.zip")
                        def junitToken = uploadFileToRedmine(junitZipPath)

                        // JUnit Redmine 이슈 생성
                        def createRedmineIssue = { title, description, uploadToken ->
                            try {
                                def issueData = [
                                    issue: [
                                        project_id: 1,
                                        tracker_id: 2, // Tracker ID (예: Bug, Feature 등)
                                        subject: title,
                                        description: description,
                                        uploads: [
                                            [token: uploadToken, filename: 'junit_results.zip', description: 'JUnit Test Reports']
                                        ]
                                    ]
                                ]

                                httpRequest(
                                    httpMode: 'POST',
                                    url: 'http://redmine:3000/issues.json',
                                    acceptType: 'APPLICATION_JSON',
                                    contentType: 'APPLICATION_JSON',
                                    customHeaders: [[name: 'X-Redmine-API-Key', value: redmineApiKey]],
                                    requestBody: groovy.json.JsonOutput.toJson(issueData)
                                )

                                echo "JUnit results uploaded to Redmine and issue created successfully."
                            } catch (Exception e) {
                                echo "Error while creating Redmine issue: ${e.message}"
                            }
                        }

                        // 이슈 제목 및 설명 정의
                        def junitIssueTitle = "[${repoName}][JUnit Results][Build #${currentBuild.number}]"
                        def junitIssueDescription = junitSummary

                        // Redmine 이슈 생성 호출
                        createRedmineIssue(junitIssueTitle, junitIssueDescription, junitToken)
                        echo "JUnit results uploaded to Redmine."
                    } catch (Exception e) {
                        echo "Error while uploading Junit results to Redmine: ${e.message}"
                    }
                
                    if (testTools.contains('jacoco') && testTools.contains('junit')) {
                        try {
                            def jacocoReportPath = ""
                            def jacocoHtmlPath = ""

                            if (buildTool == 'gradle') {
                                // Gradle Jacoco 보고서 생성
                                sh "cd ${folder} && ./gradlew jacocoTestReport"
                                jacocoReportPath = "${folder}/build/reports/jacoco/test/html"
                                jacocoHtmlPath = "${folder}/build/reports/jacoco/test/html/index.html"
                            } else if (buildTool == 'maven') {
                                // Maven Jacoco 보고서 생성
                                sh "cd ${folder} && ${MVN_HOME}/bin/mvn jacoco:report -Drat.skip=true"
                                jacocoReportPath = "${folder}/target/site/jacoco"
                                jacocoHtmlPath = "${folder}/target/site/jacoco/index.html"
                            } else {
                                echo "Unsupported build tool: ${buildTool} for Jacoco"
                            }

                            def reportPath = (buildTool == 'gradle') ? jacocoHtmlPath : jacocoHtmlPath
                            def jacocoSummaryOutput = sh(
                                script: "sh ./jacoco_result.sh ${reportPath}",
                                returnStdout: true
                            ).trim()

                            def jacocoSummary = readFile('redmine_jacoco.txt').trim()

                            // 파일을 Redmine에 업로드하는 함수
                            def uploadFileToRedmine = { filePath ->
                                try {
                                    def uploadResponse = sh(
                                        script: """
                                        curl -X POST "http://redmine:3000/uploads.json" \
                                            -H "X-Redmine-API-Key: ${redmineApiKey}" \
                                            -H "Content-Type: application/octet-stream" \
                                            --data-binary @${filePath} \
                                            -s -o upload_response.json -w "%{http_code}"
                                        """,
                                        returnStdout: true
                                    ).trim()
                            
                                    if (uploadResponse == "201") {
                                        def responseJson = readJSON file: 'upload_response.json'
                                        echo "Upload Token: ${responseJson.upload.token}"
                                        return responseJson.upload.token
                                    } else {
                                        echo "Failed to upload file to Redmine. HTTP response: ${uploadResponse}"
                                    }
                                } catch (Exception e) {
                                    echo "Failed to upload file to Redmine: ${e.message}"
                                }
                            }

                            // Jacoco ZIP 파일 업로드 및 토큰 획득
                            //def jacocoToken = uploadFileToRedmine("${folder}/target/site/jacoco/index.html")
                            def jacocoToken = uploadFileToRedmine(jacocoHtmlPath)

                            // Jacoco Redmine 이슈 생성
                            def createRedmineIssue = { title, description, uploadToken, filename ->
                                try {
                                    def issueData = [
                                        issue: [
                                            project_id: 1,
                                            tracker_id: 3,
                                            subject: title,
                                            description: description,
                                            uploads: [
                                                [token: uploadToken, filename: filename, description: 'Jacoco Code Coverage Report']
                                            ]
                                        ]
                                    ]

                                    httpRequest(
                                        httpMode: 'POST',
                                        url: 'http://redmine:3000/issues.json',
                                        acceptType: 'APPLICATION_JSON',
                                        contentType: 'APPLICATION_JSON',
                                        customHeaders: [[name: 'X-Redmine-API-Key', value: redmineApiKey]],
                                        requestBody: groovy.json.JsonOutput.toJson(issueData)
                                    )

                                    echo "Jacoco results uploaded to Redmine and issue created successfully."
                                } catch (Exception e) {
                                    echo "Error while creating Redmine issue: ${e.message}"
                                }
                            }
                            // 이슈 제목 및 설명 정의
                            def jacocoIssueTitle = "[${repoName}][Jacoco Coverage][Build #${currentBuild.number}]"
                            def jacocoIssueDescription = jacocoSummary

                            // Redmine 이슈 생성 호출
                            createRedmineIssue(jacocoIssueTitle, jacocoIssueDescription, jacocoToken, 'index.html')
                            echo "Jacoco results (index.html) uploaded to Redmine."
                        } catch (Exception e) {
                            echo "Error while processing Jacoco results for ${repoName}: ${e.message}"
                            currentBuild.result = 'FAILURE'
                        }
                    }
                }
                if (testTools.contains('openclover') && buildTool == 'maven') {
                    sh "cd ${folder} && ${MVN_HOME}/bin/mvn clover:setup test clover:aggregate clover:clover -Drat.skip=true"
                }
            }
        
            if (subProject.SONARQUBE_ANALYSIS == true) {
                stage("SonarQube - ${repoName}") {
                    echo "Running SonarQube analysis on ${repoName}"
                    script {
                        try {
                            def sonarEnv = (buildTool == 'gradle') ? 'sonarqube_gradle' : 'sonarqube'

                            withSonarQubeEnv("${sonarEnv}") {
                                if (buildTool == 'gradle') {
                                    sh """
                                        cd ${folder}
                                        ./gradlew --continue -Dsonar.host.url=http://sonarqube:9000 -Dsonar.login=${gradle_sonarApiToken} -Dsonar.projectKey=${repoName} -Dsonar.projectName="${repoName}" -Dsonar.plugins.downloadOnlyRequired=true -Dsonar.java.binaries=build sonar 
                                    """
                                } else if (buildTool == 'maven') {
                                    sh "cd ${folder} && ${MVN_HOME}/bin/mvn sonar:sonar -Dsonar.host.url=http://sonarqube:9000 -Dsonar.login=${maven_sonarApiToken} -Dsonar.projectKey=${repoName} -Dsonar.projectName=${repoName} -Dsonar.plugins.downloadOnlyRequired=true -Drat.skip=true -DtestFailureIgnore=true"
                                } else {
                                    echo "Unsupported build tool for SonarQube: ${buildTool}. Pipeline stopped."
                                }
                            }
                        } catch (Exception e) {
                            echo "SonarQube analysis failed: ${e.message}"
                        } finally {
                            timeout(time: 5, unit: 'MINUTES') {
                                def qg = waitForQualityGate()
                                echo "Quality Gate status: ${qg.status}"
                                if (qg.status != 'OK') {
                                    echo "Quality Gate failed: ${qg.status}"
                                    currentBuild.result = 'UNSTABLE'
                                }
                            }

                            def qualityGateResult
                            if (buildTool == 'gradle') {
                                qualityGateResult = httpRequest(
                                    httpMode: 'GET',
                                    url: "http://sonarqube:9000/api/qualitygates/project_status?projectKey=${repoName}",
                                    acceptType: 'APPLICATION_JSON',
                                    customHeaders: [[name: 'Authorization', value: "Bearer ${gradle_sonarApiToken}"]]
                                )
                            } else if (buildTool == 'maven') {
                                qualityGateResult = httpRequest(
                                    httpMode: 'GET',
                                    url: "http://sonarqube:9000/api/qualitygates/project_status?projectKey=${repoName}",
                                    acceptType: 'APPLICATION_JSON',
                                    customHeaders: [[name: 'Authorization', value: "Bearer ${maven_sonarApiToken}"]]
                                )
                            }

                            def json = readJSON text: qualityGateResult.content
                            def qualityGateStatus = json.projectStatus.status
                            def conditions = json.projectStatus.conditions

                            def overallConditions = conditions.findAll { !it.metricKey.contains("new") }
                            def newConditions = conditions.findAll { it.metricKey.contains("new") }

                            def formatCondition = { condition ->
                                def actualValue = condition.actualValue ?: 'N/A'
                                def errorThreshold = condition.errorThreshold ?: 'N/A'
                                def unit = condition.comparator == 'LT' ? '%' : ''
                                return "- Metric: ${condition.metricKey} | Status: ${condition.status} | Actual Value: ${actualValue}/${errorThreshold}${unit}"
                            }

                            def redmineIssueTitle = "[${repoName}][QualityGate][${currentBuild.number}]-[${qualityGateStatus}]"
                            def redmineIssueDescription = """
- QualityGate Result: ${qualityGateStatus}

[Overall]
${overallConditions.collect { formatCondition(it) }.join('\n ')}

---------------------------------

[New]
${newConditions.collect { formatCondition(it) }.join('\n ')}

---------------------------------

- Link: http://localhost:19000/dashboard?id=${repoName}
"""

                            def redmineIssueData = [
                                issue: [
                                    project_id: 1,
                                    tracker_id: 4,
                                    subject: redmineIssueTitle,
                                    description: redmineIssueDescription
                                ]
                            ]

                            httpRequest(
                                httpMode: 'POST',
                                url: 'http://redmine:3000/issues.json',
                                acceptType: 'APPLICATION_JSON',
                                contentType: 'APPLICATION_JSON',
                                customHeaders: [[name: 'X-Redmine-API-Key', value: redmineApiKey]],
                                requestBody: groovy.json.JsonOutput.toJson(redmineIssueData)
                            )
                        }
                    }
                }
            }
        }
    }
    parallel branches
}

pipeline {
    agent any

    environment {
        redmineApiKey = credentials('redmine_api_key')
        jenkinsApiKey = credentials('jenkins_api')
        
        PATH = "${GRADLE_HOME}/bin:$PATH:/var/jenkins_home/.local/bin"

        maven_sonarApiToken = credentials('sonar-github-maven')
        gradle_sonarApiToken = credentials('sonar-github-gradle')
        
        GRADLE_HOME = tool 'Jenkins_Gradle_8_11'
        MVN_HOME = tool 'jenkins_Maven_3_9_9'
    }

    stages {
        stage('Setup') {
            steps {
                script {
                    def config = loadConfig()
                    setupStages(config)
                }
            }
        }

        stage('TestToolChain') {
            steps {
                script {
                    def config = loadConfig()
                    parallelBuildTestQualityGate(config)
                }
            }
        }
    }
}
