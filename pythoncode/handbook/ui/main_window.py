from PyQt5.QtCore import Qt
from handbook.data.diary_ops import save_remind, save_diary
from PyQt5.QtWidgets import (QMainWindow, QWidget, QTabWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QDateTimeEdit, QHBoxLayout, QVBoxLayout, QListWidget, QInputDialog, QDialog)
from PyQt5.QtCore import QDateTime, QTimer
from handbook.ui.draw_board import DrawBoardDialog
from handbook.ui.style import get_pink_style
from handbook.data.diary_ops import load_diary, add_diary, load_remind, add_remind
from handbook.security.password import check_login_pwd, encrypt_note
from handbook.file_download.resource import open_url, download_book

class HandBookWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("粉色流光学习手账日程本")
        self.resize(1500, 1000)
        self.setStyleSheet(get_pink_style())
        self.diary_data = load_diary()
        self.check_remind_timer = QTimer()
        self.check_remind_timer.timeout.connect(self.check_remind_task)
        self.check_remind_timer.start(30000)
        self.init_ui()

    def init_ui(self):
        center_widget = QWidget()
        self.setCentralWidget(center_widget)
        main_layout = QVBoxLayout(center_widget)
        tab = QTabWidget()
        tab.addTab(self.create_diary_tab(), "📝 新建日记")
        tab.addTab(self.history_diary_tab(), "📔 历史日记")
        tab.addTab(self.create_draw_tab(), "🎀 图文手账")
        tab.addTab(self.create_resource_tab(), "📚 学习资源")
        tab.addTab(self.create_remind_tab(), "⏰ 定时提醒")
        main_layout.addWidget(tab)

    def create_diary_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        top_lay = QHBoxLayout()
        self.diary_title = QLineEdit()
        self.diary_title.setPlaceholderText("日记标题/学习主题")
        btn_save_diary = QPushButton("保存日记")
        btn_save_diary.clicked.connect(self.save_diary_func)
        btn_del = QPushButton("清空当前")
        btn_del.clicked.connect(self.clear_diary_input)
        top_lay.addWidget(self.diary_title)
        top_lay.addWidget(btn_save_diary)
        top_lay.addWidget(btn_del)
        lay.addLayout(top_lay)
        self.diary_content = QTextEdit()
        self.diary_content.setPlaceholderText("写下今日日程、学习笔记...")
        lay.addWidget(self.diary_content)
        self.empty_tip = QLabel("暂无日记，快来记录你的日常吧✨")
        self.empty_tip.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.empty_tip)
        return widget

    def create_draw_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        top_bar = QHBoxLayout()
        btn_insert_img = QPushButton("插入本地图片到手账")
        btn_insert_img.clicked.connect(self.insert_image)
        btn_open_draw = QPushButton("🎨 打开手绘画板")
        btn_open_draw.clicked.connect(self.open_draw_board)
        btn_save_handbook = QPushButton("保存到手账历史记录")
        btn_save_handbook.clicked.connect(self.save_handbook_to_history)
        top_bar.addWidget(btn_insert_img)
        top_bar.addWidget(btn_open_draw)
        top_bar.addWidget(btn_save_handbook)
        lay.addLayout(top_bar)
        self.draw_text = QTextEdit()
        self.draw_text.setPlaceholderText("图文手账区域，可插入手绘/本地图片...")
        lay.addWidget(self.draw_text)
        return widget

    def clear_diary_input(self):
        self.diary_title.clear()
        self.diary_content.clear()

    def save_diary_func(self):
        title = self.diary_title.text().strip()
        content = self.diary_content.toPlainText().strip()
        if not title or not content:
            QMessageBox.warning(self, "提示", "标题和内容不能为空！")
            return
        try:
            msg = add_diary(title, content)
            QMessageBox.information(self, "保存成功", msg)
            self.clear_diary_input()
            self.diary_data = load_diary()
            self.empty_tip.setVisible(False)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def save_handbook_to_history(self):
        title, ok = QInputDialog.getText(self, "保存图文手账", "请输入手账标题：")
        if not ok or not title.strip():
            return
        full_html = self.draw_text.toHtml()
        plain_text = self.draw_text.toPlainText().strip()
        if not plain_text:
            QMessageBox.warning(self, "提示", "手账内容不能为空！")
            return
        try:
            add_diary(title, plain_text, img_html=full_html)
            QMessageBox.information(self, "保存成功", "图文手账已存入历史记录，切换历史日记查看！")
            self.draw_text.clear()
            self.diary_data = load_diary()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def create_resource_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        link_lay = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("粘贴学习网页链接")
        btn_link = QPushButton("打开链接")
        btn_link.clicked.connect(lambda: self.open_link_func(self.url_input.text()))
        link_lay.addWidget(self.url_input)
        link_lay.addWidget(btn_link)
        lay.addLayout(link_lay)
        down_lay = QHBoxLayout()
        self.book_url = QLineEdit()
        self.book_url.setPlaceholderText("课本下载地址")
        btn_down = QPushButton("下载课本")
        btn_down.clicked.connect(self.download_book_func)
        down_lay.addWidget(self.book_url)
        down_lay.addWidget(btn_down)
        lay.addLayout(down_lay)
        return widget

    def create_remind_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        self.remind_title = QLineEdit()
        self.remind_title.setPlaceholderText("提醒内容，如：背单词、交作业")
        self.remind_time = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.remind_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        btn_add_remind = QPushButton("创建定时提醒")
        btn_add_remind.clicked.connect(self.add_remind_func)
        btn_clear_remind = QPushButton("删除全部提醒")
        btn_clear_remind.clicked.connect(self.clear_all_remind)
        lay.addWidget(self.remind_title)
        lay.addWidget(self.remind_time)
        lay.addWidget(btn_add_remind)
        lay.addWidget(btn_clear_remind)
        lay.addWidget(QLabel("已创建提醒列表："))
        self.remind_list_widget = QListWidget()
        self.remind_empty_tip = QLabel("暂无定时提醒")
        self.remind_empty_tip.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.remind_empty_tip)
        lay.addWidget(self.remind_list_widget)
        self.refresh_remind_list()
        return widget

    def refresh_remind_list(self):
        self.remind_list_widget.clear()
        remind_list = load_remind()
        if len(remind_list) == 0:
            self.remind_empty_tip.setVisible(True)
            return
        self.remind_empty_tip.setVisible(False)
        for item in remind_list:
            show_text = f"【{item['time']}】 {item['title']}"
            self.remind_list_widget.addItem(show_text)

    def clear_all_remind(self):
        save_remind([])
        self.refresh_remind_list()
        QMessageBox.information(self, "操作完成", "所有提醒已清空")

    def insert_image(self):
        try:
            path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片(*.png *.jpg *.jpeg)")
            if path:
                self.draw_text.insertHtml(f'<img src="{path}" width="300">')
                QMessageBox.information(self, "成功", "图片已插入手账！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"图片加载失败：{str(e)}")

    def open_draw_board(self):
        try:
            dialog = DrawBoardDialog()
            if dialog.exec():
                img_path = dialog.get_img_path()
                if img_path:
                    self.draw_text.insertHtml(f'<img src="{img_path}" width="600">')
        except Exception as err:
            QMessageBox.critical(self, "画板启动失败", f"错误详情：{str(err)}")

    def open_link_func(self, url):
        flag, msg = open_url(url)
        if flag:
            QMessageBox.information(self, "提示", msg)
        else:
            QMessageBox.critical(self, "错误", msg)

    def download_book_func(self):
        url = self.book_url.text().strip()
        save_path, _ = QFileDialog.getSaveFileName(self, "保存课本", "课本.pdf", "PDF(*.pdf)")
        if url and save_path:
            flag, msg = download_book(url, save_path)
            if flag:
                QMessageBox.information(self, "完成", msg)
            else:
                QMessageBox.critical(self, "失败", msg)

    def check_remind_task(self):
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm")
        remind_list = load_remind()
        for item in remind_list:
            if item["time"] == now:
                QMessageBox.information(self, "⏰日程提醒", f"待办：{item['title']}")

    def add_remind_func(self):
        title = self.remind_title.text().strip()
        time_str = self.remind_time.dateTime().toString("yyyy-MM-dd HH:mm")
        try:
            msg = add_remind(title, time_str)
            QMessageBox.information(self, "提醒创建成功", msg)
            self.remind_title.clear()
            self.refresh_remind_list()
        except Exception as e:
            QMessageBox.critical(self, "创建失败", str(e))

    def history_diary_tab(self):
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(15)
        tip = QLabel("全部历史日记（按保存时间倒序）")
        tip.setAlignment(Qt.AlignCenter)
        lay.addWidget(tip)
        self.diary_table = QTableWidget()
        self.diary_table.setColumnCount(4)
        self.diary_table.setHorizontalHeaderLabels(["保存时间", "标题", "内容预览", "查看详情"])
        lay.addWidget(self.diary_table)
        btn_bar = QHBoxLayout()
        refresh_btn = QPushButton("刷新日记列表")
        refresh_btn.clicked.connect(self.load_history_diary)
        del_btn = QPushButton("删除选中日记")
        del_btn.clicked.connect(self.delete_selected_diary)
        btn_bar.addWidget(refresh_btn)
        btn_bar.addWidget(del_btn)
        lay.addLayout(btn_bar)
        self.load_history_diary()
        return widget

    def delete_selected_diary(self):
        selected_ranges = self.diary_table.selectedRanges()
        if not selected_ranges:
            QMessageBox.information(self, "提示", "请先选中要删除的日记行！")
            return
        confirm = QMessageBox.question(self, "确认删除", "删除后无法恢复，确定要删除选中日记吗？",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm != QMessageBox.Yes:
            return
        diary_list = load_diary()
        delete_rows = []
        for r in selected_ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                delete_rows.append(row)
        delete_rows.sort(reverse=True)
        for table_row in delete_rows:
            real_index = len(diary_list) - 1 - table_row
            del diary_list[real_index]
        save_diary(diary_list)
        self.load_history_diary()
        QMessageBox.information(self, "完成", "选中日记已删除！")

    def load_history_diary(self):
        diary_list = load_diary()
        self.diary_table.setRowCount(len(diary_list))
        for row, item in enumerate(reversed(diary_list)):
            time_text = item.get("date", "无记录时间")
            title_text = item["title"]
            if item.get("img_html", ""):
                title_text += " 【图文手账】"
            if len(item["content"]) > 30:
                content_text = item["content"][:30] + "……"
            else:
                content_text = item["content"]
            self.diary_table.setItem(row, 0, QTableWidgetItem(time_text))
            self.diary_table.setItem(row, 1, QTableWidgetItem(title_text))
            self.diary_table.setItem(row, 2, QTableWidgetItem(content_text))
            # 查看按钮
            view_btn = QPushButton("查看完整内容")
            view_btn.clicked.connect(lambda checked, row_data=item: self.show_full_diary(row_data))
            btn_box = QWidget()
            btn_layout = QHBoxLayout(btn_box)
            btn_layout.addWidget(view_btn)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            self.diary_table.setCellWidget(row, 3, btn_box)

    # 修复：改用QDialog模态弹窗，窗口不会消失
    def show_full_diary(self, diary_data):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"日记详情 - {diary_data['title']}")
        dialog.resize(950, 650)
        layout = QVBoxLayout(dialog)
        time_label = QLabel(f"记录时间：{diary_data['date']}")
        layout.addWidget(time_label)
        content_edit = QTextEdit()
        content_edit.setReadOnly(True)
        html = diary_data.get("img_html", "")
        if html:
            content_edit.setHtml(html)
        else:
            content_edit.setPlainText(diary_data["content"])
        layout.addWidget(content_edit)
        dialog.exec()