import urllib.parse
import requests
import datetime
import os
import time  # 导入 time 模块

def main_logic():
    """
    This function contains the core logic of the original main function,
    separated to be called by the scheduling loop.
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

    # 1. 尝试从远程链接读取订阅
    if REMOTE_SOURCE_URL:
        source_type = "remote"
        print(f"尝试从远程链接读取订阅: {REMOTE_SOURCE_URL}")
        try:
            resp = requests.get(REMOTE_SOURCE_URL, timeout=(3, 30))
            resp.raise_for_status()
            links = [line.strip() for line in resp.text.splitlines() if line.strip() and not line.startswith('#')]
            if not links:
                print("警告：远程订阅链接内容为空，尝试从本地文件读取")
                source_type = "file" # 远程链接为空，回退到本地文件
        except requests.exceptions.RequestException as e:
            print(f"错误：读取远程订阅链接失败: {str(e)}，尝试从本地文件读取")
            source_type = "file" # 读取远程链接失败，回退到本地文件

    # 2. 从本地文件读取订阅 (当远程读取失败或未配置远程链接时)
    if source_type == "file":
        print(f"尝试从本地文件读取订阅: {SOURCE_FILE}")
        try:
            with open(SOURCE_FILE, "r") as f:
                links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if not links:
                    print("警告：源文件为空")
                    # return # 本地文件为空，不再终止程序，以便定时任务继续尝试
                    pass # 允许继续执行，但links为空，后续会处理
        except FileNotFoundError:
            print(f"错误：找不到源文件 {SOURCE_FILE}")
            # return # 本地文件未找到，不再终止程序，以便定时任务继续尝试
            pass # 允许继续执行，但links为空，后续会处理
        except IOError as e:
            print(f"错误：读取源文件时出错：{str(e)}")
            # return # 本地文件IO错误，不再终止程序，以便定时任务继续尝试
            pass # 允许继续执行，但links为空，后续会处理

    if not links: # 再次检查 links 是否为空，防止远程和本地都为空的情况
        print("错误：未能获取任何订阅链接，跳过后续步骤")
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return # 未获取到链接，本次运行结束

    # 3. 处理URL参数编码 (后续步骤与原代码相同)
    try:
        encoded_links = [
            urllib.parse.quote(link, safe="")
            for link in links
        ]
        url_param = "|".join(encoded_links)
    except Exception as e:
        print(f"URL编码失败: {str(e)}")
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return

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
        print(f"构建请求URL失败: {str(e)}")
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return

    # 5. 获取合并后的订阅内容
    try:
        resp = requests.get(final_url, timeout=(3, 30))
        resp.raise_for_status()
    except requests.exceptions.Timeout as e:
        print(f"错误：请求超时：{str(e)}")
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return
    except requests.exceptions.RequestException as e:
        print(f"获取订阅失败: {str(e)}")
        print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        return

    # 6. 上传到GitHub Gist
    # 仅在 GIST_ID 和 GIST_TOKEN 都已设置（非默认的 YOUR_GIST_ID 或 YOUR_GITHUB_TOKEN）时尝试上传
    if GIST_ID != "YOUR_GIST_ID" and GIST_TOKEN != "YOUR_GITHUB_TOKEN":
        try:
            headers = {
                "Authorization": f"token {GIST_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {
                "files": {
                    GIST_FILENAME: {"content": resp.text}
                }
            }

            gist_resp = requests.patch(
                f"https://ghapi.dsdog.tk/gists/{GIST_ID}",
                headers=headers,
                json=payload,
                timeout=3
            )
            gist_resp.raise_for_status()
            print(f"成功更新Gist：{gist_resp.json()['html_url']}")
        except requests.exceptions.Timeout as e:
            print(f"错误：Gist上传超时：{str(e)}")
        except requests.exceptions.RequestException as e:
            print(f"Gist更新失败: {str(e)}")
        except Exception as e:
            print(f"意外错误：{str(e)}")
    else:
        print("未配置 Gist ID 或 Token，跳过上传 Gist 步骤。")

    print("程序运行结束:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

def main():
    """
    Main function that handles scheduling based on environment variable.
    """
    # 从环境变量读取运行间隔
    run_interval_str = os.environ.get("RUN_INTERVAL_SECONDS", "0")
    try:
        run_interval = int(run_interval_str)
    except ValueError:
        print(f"警告: 无效的 RUN_INTERVAL_SECONDS 值 '{run_interval_str}', 将只运行一次。")
        run_interval = 0

    if run_interval > 0:
        print(f"程序将每隔 {run_interval} 秒运行一次。")
        while True:
            main_logic()
            print(f"等待 {run_interval} 秒进行下一次运行...")
            time.sleep(run_interval)
    else:
        print("RUN_INTERVAL_SECONDS 未设置或无效 (<= 0)，程序将运行一次后退出。")
        main_logic()

if __name__ == "__main__":
    main()