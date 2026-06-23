import sys
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt
from handbook.ui.main_window import HandBookWindow
from handbook.security.password import check_login_pwd, set_login_pwd, reset_login_pwd

class PwdDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.resize(620, 400)
        # 无边框+透明圆角
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 粉色流沙样式
        self.setStyleSheet("""
        QDialog{background: transparent;}
        #main_panel{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #FFE6EF, stop:0.4 #FFD6E4, stop:0.8 #FFC8DD, stop:1 #F8D7E8);
            border-radius:18px;
        }
        #title_bar{background:rgba(255,180,200,150);border-top-left-radius:18px;border-top-right-radius:18px;}
        #close_btn{color:#662F44;background:rgba(255,255,255,80);border-radius:12px;}
        QLabel{font-size:13px;color:#66394F;}
        QLineEdit{background:rgba(255,255,255,200);border:1px solid #FFB8CC;border-radius:10px;padding:8px 12px;font-size:12px;}
        QPushButton#confirm_btn{background:rgba(255,220,232,200);border:1px solid #FFA8C0;border-radius:10px;padding:9px;font-size:12px;color:#582F40;box-shadow: 0 0 6px rgba(255,170,195,0.45);}
        QPushButton#confirm_btn:hover{background:rgba(255,200,218,230);box-shadow: 0 0 10px rgba(255,150,180,0.7);}
        """)
        # 主面板
        main_panel = QWidget()
        main_panel.setObjectName("main_panel")
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        # 自定义标题栏
        title_bar = QWidget()
        title_bar.setObjectName("title_bar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20,10,20,10)
        title_label = QLabel("🔒 粉色手账 · 登录验证")
        close_btn = QPushButton("×")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(24,24)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        main_layout.addWidget(title_bar)
        # 输入区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(70, 50, 70, 50)
        content_layout.setSpacing(30)
        tip_label = QLabel("请输入你的手账登录密码")
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setPlaceholderText("输入密码解锁全部笔记")
        btn_ok = QPushButton("确认解锁")
        btn_ok.setObjectName("confirm_btn")
        btn_ok.clicked.connect(self.verify)
        # 新增重置密码按钮
        btn_reset = QPushButton("忘记密码重置")
        btn_reset.clicked.connect(self.reset_pwd)
        content_layout.addWidget(tip_label)
        content_layout.addWidget(self.pwd_input)
        content_layout.addWidget(btn_ok)
        content_layout.addWidget(btn_reset)
        main_layout.addWidget(content_widget)
        # 外层布局
        root_layout = QVBoxLayout()
        root_layout.addWidget(main_panel)
        root_layout.setContentsMargins(12,12,12,12)
        self.setLayout(root_layout)
        self.result_flag = False

    def verify(self):
        pwd = self.pwd_input.text().strip()
        try:
            flag, msg = check_login_pwd(pwd)
            if "首次使用" in msg:
                set_login_pwd(pwd)
                QMessageBox.information(self, "初始化完成", "已设置当前密码为登录密码！")
                self.result_flag = True
                self.close()
            elif flag:
                QMessageBox.information(self, "验证通过", "欢迎回到粉色手账✨")
                self.result_flag = True
                self.close()
            else:
                QMessageBox.warning(self, "密码错误", msg)
        except Exception as e:
            QMessageBox.critical(self, "验证异常", str(e))

    def reset_pwd(self):
        new_pwd, ok = QInputDialog.getText(self, "重置密码", "输入新登录密码：", QLineEdit.Password)
        if ok and new_pwd.strip():
            flag, msg = reset_login_pwd(new_pwd)
            if flag:
                QMessageBox.information(self, "重置成功", msg)
            else:
                QMessageBox.critical(self, "重置失败", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pwd_dialog = PwdDialog()
    pwd_dialog.exec()
    if pwd_dialog.result_flag:
        window = HandBookWindow()
        window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)