import json
import os
from cryptography.fernet import Fernet

KEY_FILE = "secret.key"
PWD_FILE = "password.enc"

# 生成加密密钥
def create_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)

# 获取加密器
def get_cipher():
    create_key()
    with open(KEY_FILE, "rb") as f:
        key = f.read()
    return Fernet(key)

# 设置登录密码
def set_login_pwd(raw_pwd):
    try:
        cipher = get_cipher()
        enc_pwd = cipher.encrypt(raw_pwd.encode("utf-8"))
        with open(PWD_FILE, "wb") as f:
            f.write(enc_pwd)
        return True, "密码设置成功"
    except Exception as e:
        return False, f"密码保存失败：{str(e)}"

# 验证登录密码
def check_login_pwd(input_pwd):
    try:
        if not os.path.exists(PWD_FILE):
            return True, "首次使用，请设置登录密码"
        cipher = get_cipher()
        with open(PWD_FILE, "rb") as f:
            enc_data = f.read()
        real_pwd = cipher.decrypt(enc_data).decode("utf-8")
        if input_pwd == real_pwd:
            return True, "验证通过"
        else:
            return False, "密码错误，请重新输入"
    except Exception as e:
        return False, f"验证异常：{str(e)}"

# 加密单条私密笔记
def encrypt_note(content):
    cipher = get_cipher()
    return cipher.encrypt(content.encode("utf-8")).decode()

# 解密私密笔记
def decrypt_note(enc_content):
    try:
        cipher = get_cipher()
        raw = cipher.decrypt(enc_content.encode("utf-8")).decode()
        return True, raw
    except:
        return False, "笔记密码错误，无法解密"
# 重置登录密码
def reset_login_pwd(new_pwd):
    try:
        cipher = get_cipher()
        enc_pwd = cipher.encrypt(new_pwd.encode("utf-8"))
        with open(PWD_FILE, "wb") as f:
            f.write(enc_pwd)
        return True, "密码重置成功"
    except Exception as e:
        return False, f"重置失败：{str(e)}"