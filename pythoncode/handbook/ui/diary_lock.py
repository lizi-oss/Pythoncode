from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from handbook.ui.style import get_pink_style
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
class DiaryLockDialog(QDialog):
    def __init__(self, target_pwd):
        super().__init__()
        self.setStyleSheet(get_pink_style())
        self.target_pwd = target_pwd
        self.setWindowTitle("私密笔记解锁")
        self.resize(300,150)
        lay = QVBoxLayout()
        lay.setContentsMargins(30,30,30,30)
        lay.setSpacing(15)
        lay.addWidget(QLabel("该笔记已加密，请输入查看密码"))
        self.input_pwd = QLineEdit()
        self.input_pwd.setEchoMode(QLineEdit.Password)
        btn_ok = QPushButton("解锁查看")
        btn_ok.clicked.connect(self.check)
        lay.addWidget(self.input_pwd)
        lay.addWidget(btn_ok)
        self.setLayout(lay)
        self.unlock_ok = False

    def check(self):
        if self.input_pwd.text() == self.target_pwd:
            self.unlock_ok = True
            self.close()
        else:
            QMessageBox.warning(self, "错误", "密码不正确，无法查看")