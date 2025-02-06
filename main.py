import urllib.parse
import requests
import config

def main():
    # 1. 读取订阅链接文件
    try:
        with open(config.SOURCE_FILE, "r") as f:
            links = [line.strip() for line in f if line.strip()]
            if not links:
                print("警告：源文件为空")
                return
    except FileNotFoundError:
        print(f"错误：找不到源文件 {config.SOURCE_FILE}")
        return
    except IOError as e:
        print(f"错误：读取源文件时出错：{str(e)}")
        return

    # 2. 处理URL参数编码
    try:
        encoded_links = [
            urllib.parse.quote(link, safe="")  # 编码单个链接
            for link in links
        ]
        url_param = "|".join(encoded_links)    # 用|连接编码后的链接
    except Exception as e:
        print(f"URL编码失败: {str(e)}")
        return

    # 3. 构建最终请求URL
    try:
        final_params = {**config.PARAMS, "url": url_param}  # 合并参数
        query = urllib.parse.urlencode(
            final_params,
            safe="%",                      # 保留已编码的%
            quote_via=urllib.parse.quote   # 使用标准编码方式
        )
        final_url = f"{config.BASE_URL}?{query}"
    except Exception as e:
        print(f"构建请求URL失败: {str(e)}")
        return

    # 4. 获取合并后的订阅内容
    try:
        resp = requests.get(final_url, timeout=(3, 30))  # 连接超时3秒，读取超时30秒
        resp.raise_for_status()
    except requests.exceptions.Timeout as e:
        print(f"错误：请求超时：{str(e)}")
        return
    except requests.exceptions.RequestException as e:
        print(f"获取订阅失败: {str(e)}")
        return

    # 5. 上传到GitHub Gist
    try:
        headers = {
            "Authorization": f"token {config.GIST_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        payload = {
            "files": {
                config.GIST_FILENAME: {"content": resp.text}
            }
        }
        
        # 设置超时时间为3秒
        gist_resp = requests.patch(
            f"https://api.github.com/gists/{config.GIST_ID}",
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

if __name__ == "__main__":
    main()