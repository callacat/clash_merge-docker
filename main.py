import urllib.parse
import requests
import datetime
import os

def main():
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
    # 使用读取到的 REMOTE_SOURCE_URL 变量
    if REMOTE_SOURCE_URL:
        source_type = "remote"
        print(f"尝试从远程链接读取订阅: {REMOTE_SOURCE_URL}")
        try:
            # 使用读取到的 REMOTE_SOURCE_URL 变量
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
        # 使用读取到的 SOURCE_FILE 变量
        print(f"尝试从本地文件读取订阅: {SOURCE_FILE}")
        try:
            # 使用读取到的 SOURCE_FILE 变量
            with open(SOURCE_FILE, "r") as f:
                links = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                if not links:
                    print("警告：源文件为空")
                    return # 本地文件为空，程序终止
        except FileNotFoundError:
            # 使用读取到的 SOURCE_FILE 变量
            print(f"错误：找不到源文件 {SOURCE_FILE}")
            return # 本地文件未找到，程序终止
        except IOError as e:
            print(f"错误：读取源文件时出错：{str(e)}")
            return # 本地文件IO错误，程序终止

    if not links: # 再次检查 links 是否为空，防止远程和本地都为空的情况
        print("错误：未能获取任何订阅链接，程序终止")
        return

    # 3. 处理URL参数编码 (后续步骤与原代码相同)
    try:
        encoded_links = [
            urllib.parse.quote(link, safe="")
            for link in links
        ]
        url_param = "|".join(encoded_links)
    except Exception as e:
        print(f"URL编码失败: {str(e)}")
        return

    # 4. 构建最终请求URL
    try:
        # 使用读取到的 PARAMS 字典
        final_params = {**PARAMS, "url": url_param}
        query = urllib.parse.urlencode(
            final_params,
            safe="%",
            quote_via=urllib.parse.quote
        )
        # 使用读取到的 BASE_URL 变量
        final_url = f"{BASE_URL}?{query}"
    except Exception as e:
        print(f"构建请求URL失败: {str(e)}")
        return

    # 5. 获取合并后的订阅内容
    try:
        resp = requests.get(final_url, timeout=(3, 30))
        resp.raise_for_status()
    except requests.exceptions.Timeout as e:
        print(f"错误：请求超时：{str(e)}")
        return
    except requests.exceptions.RequestException as e:
        print(f"获取订阅失败: {str(e)}")
        return

    # 6. 上传到GitHub Gist
    # 仅在 GIST_ID 和 GIST_TOKEN 都已设置（非默认的 YOUR_GIST_ID 或 YOUR_GITHUB_TOKEN）时尝试上传
    if GIST_ID != "YOUR_GIST_ID" and GIST_TOKEN != "YOUR_GITHUB_TOKEN":
        try:
            headers = {
                # 使用读取到的 GIST_TOKEN 变量
                "Authorization": f"token {GIST_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {
                "files": {
                    # 使用读取到的 GIST_FILENAME 变量
                    GIST_FILENAME: {"content": resp.text}
                }
            }

            # 使用读取到的 GIST_ID 变量
            gist_resp = requests.patch(
                f"https://api.github.com/gists/{GIST_ID}",
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

if __name__ == "__main__":
    main()