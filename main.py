import urllib.parse
import requests
import datetime
import os
import time # 虽然不再用于定时等待，但其他地方可能用到
from flask import Flask, Response
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import sys # 用于捕获标准输出和标准错误

# 创建 Flask 应用实例
app = Flask(__name__)

# 创建后台调度器实例
scheduler = BackgroundScheduler()

# --- 核心逻辑函数 ---
# 将原 main 函数的核心逻辑封装到此函数中，并使其返回执行状态和消息
def main_logic():
    """
    Contains the core logic to fetch, process, and upload the subscription links.
    Returns a tuple: (status, message)
    status: True for success, False for failure
    message: A string describing the result or error
    """
    print("程序开始运行:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 从环境变量读取配置参数，并设置默认值
    SOURCE_FILE = os.environ.get("SOURCE_FILE", "/app/links.txt")
    REMOTE_SOURCE_URL = os.environ.get("REMOTE_SOURCE_URL", "")
    BASE_URL = os.environ.get("BASE_URL", "https://sub.dsdog.tk/sub")
    GIST_ID = os.environ.get("GIST_ID", "YOUR_GIST_ID")
    GIST_TOKEN = os.environ.get("GIST_TOKEN", "YOUR_GITHUB_TOKEN")
    GIST_FILENAME = os.environ.get("GIST_FILENAME", "merged_sub.txt")

    # 从环境变量读取 PARAMS 字典的各个参数，并设置默认值
    PARAMS = {
        "target": os.environ.get("PARAMS_TARGET", "clash"),
        "exclude": os.environ.get("PARAMS_EXCLUDE", "剩余|订阅|好友|线路|套餐|官网|机场|过期|去除|地址|群|通知|限制"),
        "emoji": os.environ.get("PARAMS_EMOJI", "true"),
        "udp": os.environ.get("PARAMS_UDP", "true"),
        "sort": os.environ.get("PARAMS_SORT", "false"),
        "scv": os.environ.get("PARAMS_SCV", "false"),
        "list": os.environ.get("PARAMS_LIST", "true")
    }

    links = []
    source_type = "file" # 默认从文件读取
    status = True
    message = "程序运行成功"

    # 1. 尝试从远程链接读取订阅
    if REMOTE_SOURCE_URL:
        source_type = "remote"
        print(f"尝试从远程链接读取订阅: {REMOTE_SOURCE_URL}")
        try:
            resp = requests.get(REMOTE_SOURCE_URL, timeout=(3, 30))
            resp.raise_for_status()
            links = [line.strip() for line in resp.text.splitlines() if line.strip() and not line.startswith('#')]
            if not links:
                message = "警告：远程订阅链接内容为空，尝试从本地文件读取"
                print(message)
                # status = False # Keep status as True for now, might succeed with file
                source_type = "file" # 远程链接为空，回退到本地文件
        except requests.exceptions.RequestException as e:
            message = f"错误：读取远程订阅链接失败: {str(e)}，尝试从本地文件读取"
            print(message)
            # status = False # Keep status as True for now, might succeed with file
            source_type = "file" # 读取远程链接失败，回退到本地文件

    # 2. 从本地文件读取订阅 (当远程读取失败或未配置远程链接时)
    if source_type == "file":
        print(f"尝试从本地文件读取订阅: {SOURCE_FILE}")
        try:
            with open(SOURCE_FILE, "r") as f:
                links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if not links:
                    message = "警告：源文件为空"
                    print(message)
                    status = False # Both sources failed/empty
        except FileNotFoundError:
            message = f"错误：找不到源文件 {SOURCE_FILE}"
            print(message)
            status = False
        except IOError as e:
            message = f"错误：读取源文件时出错：{str(e)}"
            print(message)
            status = False

    if not links: # 再次检查 links 是否为空，防止远程和本地都为空的情况
        if status: # If status is still True, means remote failed but message was just warning
             message = "错误：未能获取任何订阅链接，跳过后续步骤"
             status = False
        print(message)
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return status, message # 未获取到链接，本次运行结束并返回状态

    # 3. 处理URL参数编码 (后续步骤与原代码相同)
    try:
        encoded_links = [
            urllib.parse.quote(link, safe="")
            for link in links
        ]
        url_param = "|".join(encoded_links)
    except Exception as e:
        message = f"URL编码失败: {str(e)}"
        print(message)
        status = False
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return status, message

    # 4. 构建最终请求URL
    try:
        final_params = {**PARAMS, "url": url_param}
        query = urllib.parse.urlencode(
            final_params,
            safe="%",
            quote_via=urllib.parse.quote
        )
        final_url = f"{BASE_URL}?{query}"
    except Exception as e:
        message = f"构建请求URL失败: {str(e)}"
        print(message)
        status = False
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return status, message

    # 5. 获取合并后的订阅内容
    try:
        resp = requests.get(final_url, timeout=(3, 30))
        resp.raise_for_status()
    except requests.exceptions.Timeout as e:
        message = f"错误：请求超时：{str(e)}"
        print(message)
        status = False
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return status, message
    except requests.exceptions.RequestException as e:
        message = f"获取订阅失败: {str(e)}"
        print(message)
        status = False
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return status, message

    # 6. 上传到GitHub Gist
    if GIST_ID != "YOUR_GIST_ID" and GIST_TOKEN != "YOUR_GITHUB_TOKEN":
        try:
            headers = {
                "Authorization": f"token {GIST_TOKEN}",
                "Accept": "application/vnd.github.com+json"
            }
            payload = {
                "files": {
                    GIST_FILENAME: {"content": resp.text}
                }
            }

            # Use the official GitHub API URL for patching a Gist
            gist_url = f"https://api.github.com/gists/{GIST_ID}"
            method = requests.patch

            gist_resp = requests.request(method.__name__, gist_url, headers=headers, json=payload, timeout=10)
            gist_resp.raise_for_status()
            message = f"成功更新Gist：{gist_resp.json().get('html_url', 'URL Not Available')}" # Use .get for safety
            print(message)
        except requests.exceptions.Timeout as e:
            message = f"错误：Gist上传超时：{str(e)}"
            print(message)
            status = False
        except requests.exceptions.RequestException as e:
            message = f"Gist更新失败: {str(e)}"
            print(message)
            status = False
        except Exception as e:
            message = f"意外错误：{str(e)}"
            print(message)
            status = False
    else:
        message = "未配置 Gist ID 或 Token，跳过上传 Gist 步骤。"
        print(message)
        # status remains True if previous steps were successful

    print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return status, message

# --- Web API 路由 ---
@app.route("/")
def index():
    """Simple index page."""
    return """
    <h1>订阅转换及 Gist 更新工具</h1>
    <p>访问 <code>/run</code> 触发手动运行。</p>
    """

@app.route("/run")
def trigger_run():
    """
    Web endpoint to manually trigger the main logic.
    Runs the logic and returns the result as an HTML page.
    """
    # Redirect stdout and stderr to capture output
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = sys.stdout = sys.stderr = sys.StringIO()

    try:
        # Trigger the main_logic and get the result
        success, msg = main_logic()

        # Get captured output
        console_output = redirected_output.getvalue()

        # Prepare HTML response
        if success:
            response_html = f"""
            <h1>程序运行成功</h1>
            <p>{msg}</p>
            <h2>控制台输出:</h2>
            <pre>{console_output}</pre>
            """
            status_code = 200
        else:
            response_html = f"""
            <h1>程序运行失败</h1>
            <p>错误信息: {msg}</p>
            <h2>控制台输出:</h2>
            <pre>{console_output}</pre>
            """
            status_code = 500

    except Exception as e:
        # Catch any unexpected errors during execution
        console_output = redirected_output.getvalue()
        response_html = f"""
        <h1>程序运行发生异常</h1>
        <p>异常信息: {str(e)}</p>
        <h2>控制台输出:</h2>
        <pre>{console_output}</pre>
        """
        status_code = 500
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return Response(response_html, status=status_code, mimetype='text/html')


# --- 主执行块 ---
if __name__ == "__main__":
    # 启动时立即执行一次
    print("程序启动，执行首次运行...")
    startup_success, startup_message = main_logic()
    print(f"首次运行结果: {'成功' if startup_success else '失败'} - {startup_message}")


    # 从环境变量读取 Cron 表达式
    cron_schedule = os.environ.get("CRON_SCHEDULE")

    if cron_schedule:
        print(f"将使用 Cron 表达式 '{cron_schedule}' 进行定时运行。")
        try:
            # 添加 cron 作业到调度器
            scheduler.add_job(
                func=main_logic,
                trigger=CronTrigger.from_crontab(cron_schedule),
                id='cron_job'
            )
            scheduler.start()
            print("Cron 调度器已启动。")
            # 确保程序退出时调度器能正常关闭
            atexit.register(lambda: scheduler.shutdown())
        except Exception as e:
            print(f"启动 Cron 调度器失败: {str(e)}")
            print("请检查 CRON_SCHEDULE 环境变量格式是否正确。")
            print("程序将只通过 Web API 触发运行。")
    else:
        print("未设置 CRON_SCHEDULE 环境变量，不启用定时任务。")

    # 运行 Flask Web 服务器
    # 监听所有网络接口 (0.0.0.0)，端口默认为 8080
    # 您可以通过设置 FLASK_RUN_PORT 环境变量来指定端口 (Flask 2.2+)
    # 或者直接在这里修改 app.run 的 port 参数
    web_port = int(os.environ.get("WEB_PORT", 8080))
    print(f"启动 Web API 服务，监听端口 {web_port}。访问 /run 触发手动运行。")
    # Flask 默认只监听 127.0.0.1，在 Docker 中需要监听 0.0.0.0
    app.run(host='0.0.0.0', port=web_port)