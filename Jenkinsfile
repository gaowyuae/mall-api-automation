pipeline {
    agent any

    parameters {
        choice(
            name: 'TEST_SCOPE',
            choices: ['smoke', 'all'],
            description: 'smoke=冒烟测试；all=全部测试'
        )
    }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    triggers {
        // 入门阶段用轮询最省事：Jenkins 大约每 5 分钟检查一次仓库更新。
        pollSCM('H/5 * * * *')
    }

    environment {
        PYTHON_EXE = 'F:/conda_mall_env/python.exe'
        PYTHONUTF8 = '1'
        PYTHONIOENCODING = 'utf-8'
        APP_ENV = 'jenkins'
        PORTAL_BASE_URL = 'http://127.0.0.1:8085/'
    }

    stages {
        stage('拉取代码') {
            steps {
                checkout scm
            }
        }

        stage('准备 Python 环境') {
            steps {
                bat '''
@echo off
"%PYTHON_EXE%" --version
"%PYTHON_EXE%" -m pip install --disable-pip-version-check -r requirements-dev.txt
'''
            }
        }

        stage('CI - 代码检查') {
            steps {
                bat '''
@echo off
"%PYTHON_EXE%" -m ruff check .
"%PYTHON_EXE%" -m pytest --collect-only -q
'''
            }
        }

        stage('CI - 执行测试') {
            steps {
                // 用例失败时标黄并继续，让下一阶段仍能发布失败报告。
                catchError(buildResult: 'UNSTABLE', stageResult: 'FAILURE') {
                    script {
                        def testArgs = params.TEST_SCOPE == 'all' ? '' : '-m smoke'

                        bat """
@echo off
"%PYTHON_EXE%" -m pytest ${testArgs} --junitxml=reports/junit.xml
"""
                    }
                }
            }
        }

        stage('CD - 交付测试报告') {
            steps {
                allure commandline: 'allure2',
                       includeProperties: false,
                       jdk: '',
                       results: [[path: 'reports/allure-results']]

                junit testResults: 'reports/junit.xml', allowEmptyResults: true

                archiveArtifacts(
                    artifacts: 'reports/**/*, logs/**/*',
                    allowEmptyArchive: true,
                    fingerprint: true
                )
            }
        }
    }

    post {
        success {
            echo '流水线成功：代码检查和冒烟测试均已通过。'
        }
        unstable {
            echo '流水线不稳定：测试有失败，请打开 Test Result 或归档报告查看。'
        }
        failure {
            echo '流水线失败：优先检查代码拉取、Python 路径和依赖安装日志。'
        }
    }
}
