# 订阅链接文件路径
SOURCE_FILE = "/app/links.txt"

# 远程订阅链接网址
REMOTE_SOURCE_URL = ""

# 订阅转换服务基础地址
BASE_URL = "https://sub.dsdog.tk/sub"

# GitHub Gist配置
GIST_ID = "YOUR_GIST_ID"           # GitHub Gist ID
GIST_TOKEN = "YOUR_GITHUB_TOKEN"   # GitHub个人访问令牌(需gist权限)
GIST_FILENAME = "merged_sub.txt"   # Gist中保存的文件名

# 自定义转换参数
PARAMS = {
    "target": "clash",             # 输出格式(clash/surge等)
    "exclude": "剩余|订阅|好友|线路|套餐|官网|机场|过期|去除|地址|群|通知|限制",      # 排除包含指定字符串的节点
    "emoji": "true",               # 启用节点国旗
    "udp": "true",                 # 启用UDP
    "sort": "false",               # 禁用排序
    "scv": "false",                # 禁用证书验证
    "list": "true"                 # 显示节点列表
}