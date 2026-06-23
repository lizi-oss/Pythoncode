import webbrowser
import requests

# 打开外部超链接
def open_url(url):
    try:
        webbrowser.open(url)
        return True, "链接已跳转"
    except Exception as e:
        return False, f"链接打开失败：{str(e)}"

# 下载网络课本文件
def download_book(url, save_path):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(res.content)
        return True, "课本下载完成"
    except requests.exceptions.Timeout:
        return False, "下载超时，请检查网络"
    except Exception as e:
        return False, f"下载失败：{str(e)}"