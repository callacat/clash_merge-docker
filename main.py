import urllib.parse
import requests
import config  # 导入用户配置

def main():
    # 1. 读取订阅链接文件
    try:
        with open(config.SOURCE_FILE, "r") as f:
            links = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误：找不到源文件 {config.SOURCE_FILE}")
        return

    # 2. 处理URL参数编码
    encoded_links = [
        urllib.parse.quote(link, safe="")  # 编码单个链接
        for link in links
    ]
    url_param = "|".join(encoded_links)    # 用|连接编码后的链接
    
    # 3. 构建最终请求URL
    final_params = {**config.PARAMS, "url": url_param}  # 合并参数
    query = urllib.parse.urlencode(
        final_params,
        safe="%",                      # 保留已编码的%
        quote_via=urllib.parse.quote   # 使用标准编码方式
    )
    final_url = f"{config.BASE_URL}?{query}"

    # 4. 获取合并后的订阅内容
    try:
        resp = requests.get(final_url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"获取订阅失败: {str(e)}")
        return

    # 5. 上传到GitHub Gist
    headers = {
        "Authorization": f"token {config.GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "files": {
            config.GIST_FILENAME: {"content": resp.text}
        }
    }

    try:
        gist_resp = requests.patch(
            f"https://api.github.com/gists/{config.GIST_ID}",
            headers=headers,
            json=payload
        )
        gist_resp.raise_for_status()
        print(f"成功更新Gist：{gist_resp.json()['html_url']}")
    except Exception as e:
        print(f"Gist更新失败: {str(e)}")

if __name__ == "__main__":
    main()