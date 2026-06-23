import json
import os
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox

DIARY_FILE = "diary_data.json"
REMIND_FILE = "remind_list.json"

# ---------------------- 日记相关函数 ----------------------
# 加载全部日记
def load_diary():
    try:
        if not os.path.exists(DIARY_FILE):
            return []
        with open(DIARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # JSON损坏自动备份，防止数据丢失
        bak_name = DIARY_FILE + ".bak"
        os.rename(DIARY_FILE, bak_name)
        QMessageBox.warning(None, "数据损坏", f"日记文件损坏，已备份为{bak_name}，已创建空白日记库")
        return []
    except PermissionError:
        QMessageBox.critical(None, "权限错误", "无文件读取权限，请更换程序存放文件夹")
        return []
    except Exception as e:
        QMessageBox.critical(None, "读取失败", f"日记读取异常：{str(e)}")
        return []

# 保存日记
def save_diary(diary_list):
    try:
        with open(DIARY_FILE, "w", encoding="utf-8") as f:
            json.dump(diary_list, f, ensure_ascii=False, indent=2)
        return True
    except PermissionError:
        QMessageBox.critical(None, "权限错误", "无写入权限，保存日记失败")
        return False
    except Exception as e:
        QMessageBox.critical(None, "保存失败", f"日记保存异常：{str(e)}")
        return False

# 新建日记，img_html参数专门存储图文手账图片富文本
def add_diary(title, content, img_html="", is_secret=False, pwd_content=""):
    if not title.strip() or not content.strip():
        raise ValueError("标题和内容不能为空")
    diary_list = load_diary()
    new_item = {
        "id": len(diary_list) + 1,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "title": title,
        "content": content,
        "img_html": img_html,
        "secret": is_secret,
        "secret_text": pwd_content
    }
    diary_list.append(new_item)
    ok = save_diary(diary_list)
    if ok:
        return "日记保存完成"
    else:
        raise Exception("文件写入失败，日记未保存")

# 根据id删除单条日记
def del_diary(diary_id):
    diary_list = load_diary()
    new_list = [item for item in diary_list if item["id"] != diary_id]
    save_diary(new_list)

# 修改指定id日记内容
def edit_diary(diary_id, new_title, new_content):
    diary_list = load_diary()
    for item in diary_list:
        if item["id"] == diary_id:
            item["title"] = new_title
            item["content"] = new_content
            break
    save_diary(diary_list)

# ---------------------- 定时提醒相关函数 ----------------------
# 加载所有提醒
def load_remind():
    try:
        if not os.path.exists(REMIND_FILE):
            return []
        with open(REMIND_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

# 统一写入提醒文件，封装异常
def save_remind(remind_list):
    try:
        with open(REMIND_FILE, "w", encoding="utf-8") as f:
            json.dump(remind_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        QMessageBox.critical(None, "提醒保存失败", str(e))

# 创建提醒，校验时间不能是过去时间
def add_remind(title, target_time):
    try:
        target_dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M")
        now = datetime.now()
        if target_dt <= now:
            raise ValueError("提醒时间不能早于当前时间")
        remind_list = load_remind()
        remind_list.append({
            "title": title,
            "time": target_time
        })
        save_remind(remind_list)
        return "提醒创建成功"
    except ValueError as e:
        raise e
    except Exception as e:
        raise Exception(f"提醒创建失败：{str(e)}")

# 根据标题删除单条提醒
def del_remind_by_title(title):
    lst = load_remind()
    new_lst = [x for x in lst if x["title"] != title]
    save_remind(new_lst)

# 清空全部提醒
def clear_all_remind():
    save_remind([])
    return True