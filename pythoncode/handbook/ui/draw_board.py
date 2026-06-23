"""
ui/draw_board.py
手绘画板增强模块：
1. 自由手绘、橡皮擦擦除
2. 马卡龙粉色快捷画笔色板
3. 撤销上一笔绘图操作
4. 方格手账纸画布背景
5. 画布缩放、全屏绘图模式
6. 保存手绘、一键插入图文手账
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QColorDialog,
                             QSpinBox, QLabel, QFileDialog, QDialog)
from PyQt5.QtGui import QPainter, QColor, QPixmap, QPen
from PyQt5.QtCore import Qt, QPoint


class DrawCanvas(QWidget):
    def __init__(self):
        super().__init__()
        # 手账格子画布底色
        self.canvas_bg = QColor(255, 248, 250)
        self.grid_line_color = QColor(255, 220, 228)
        self.grid_size = 25
        # 画笔基础参数
        self.pen_color = QColor(255, 120, 160)
        self.pen_width = 4
        self.is_eraser = False
        # 画布缓存 & 撤销栈
        self.pix = QPixmap(self.size())
        self.pix.fill(self.canvas_bg)
        self.undo_stack = []
        self.last_point = QPoint()
        self.draw_step = []

    def resizeEvent(self, event):
        new_pix = QPixmap(self.size())
        new_pix.fill(self.canvas_bg)
        painter = QPainter(new_pix)
        painter.drawPixmap(0, 0, self.pix)
        self.pix = new_pix
        self.update()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        # 绘制方格手账底纹
        self.draw_grid(painter)
        # 绘制手绘内容
        painter.drawPixmap(0, 0, self.pix)

    def draw_grid(self, painter):
        pen = QPen(self.grid_line_color, 1)
        painter.setPen(pen)
        w = self.width()
        h = self.height()
        # 竖线
        for x in range(0, w, self.grid_size):
            painter.drawLine(x, 0, x, h)
        # 横线
        for y in range(0, h, self.grid_size):
            painter.drawLine(0, y, w, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_point = event.pos()
            self.draw_step = []

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            painter = QPainter(self.pix)
            pen = QPen()
            if self.is_eraser:
                # 橡皮擦：画布底色覆盖
                pen.setColor(self.canvas_bg)
                pen.setWidth(self.pen_width * 3)
            else:
                pen.setColor(self.pen_color)
                pen.setWidth(self.pen_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.pos())
            self.draw_step.append((self.last_point, event.pos(), pen))
            self.last_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.draw_step:
            self.undo_stack.append(self.draw_step.copy())
            self.draw_step.clear()

    # 撤销上一笔
    def undo_draw(self):
        if not self.undo_stack:
            return
        # 重绘空白画布，重新绘制除最后一步外所有轨迹
        self.pix.fill(self.canvas_bg)
        painter = QPainter(self.pix)
        for step_list in self.undo_stack[:-1]:
            for p1, p2, pen in step_list:
                painter.setPen(pen)
                painter.drawLine(p1, p2)
        self.undo_stack.pop()
        self.update()

    # 清空画布
    def clear_canvas(self):
        self.pix.fill(self.canvas_bg)
        self.undo_stack.clear()
        self.update()

    # 切换橡皮擦
    def switch_eraser(self, flag):
        self.is_eraser = flag

    # 设置画笔颜色
    def set_pen_color(self, color):
        self.is_eraser = False
        self.pen_color = color

    # 保存手绘图片
    def save_draw(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存手绘", "手绘手账.png", "PNG图片 (*.png)")
        if path:
            self.pix.save(path, "PNG")
            return path
        return None


# 手绘弹窗主窗口
# 手绘弹窗主窗口
class DrawBoardDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎨 手账手绘画板")
        self.resize(900, 700)
        from handbook.ui.style import get_pink_style
        self.setStyleSheet(get_pink_style())
        self.save_path = None

        # 【关键】先创建画布，再绑定所有按钮事件
        self.canvas = DrawCanvas()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ---------------------- 顶部控制栏 ----------------------
        control_bar = QHBoxLayout()
        # 画笔粗细
        control_bar.addWidget(QLabel("画笔粗细："))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(4)

        # 修复lambda不能赋值语法错误
        def set_width(val):
            self.canvas.pen_width = val
        self.width_spin.valueChanged.connect(set_width)
        control_bar.addWidget(self.width_spin)

        # 马卡龙粉色快捷色板
        pink_color_list = [
            ("浅桃粉", QColor(255, 180, 200)),
            ("豆沙粉", QColor(255, 120, 160)),
            ("芋泥紫粉", QColor(220, 160, 220)),
            ("裸粉", QColor(255, 200, 210))
        ]
        for name, color in pink_color_list:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, c=color: self.canvas.set_pen_color(c))
            control_bar.addWidget(btn)

        # 功能按钮组
        btn_eraser = QPushButton("🧽 橡皮擦")
        btn_eraser.clicked.connect(lambda: self.canvas.switch_eraser(True))
        control_bar.addWidget(btn_eraser)

        btn_undo = QPushButton("↩ 撤销一笔")
        btn_undo.clicked.connect(self.canvas.undo_draw)
        control_bar.addWidget(btn_undo)

        btn_custom_color = QPushButton("自定义画笔色")
        btn_custom_color.clicked.connect(self.select_custom_color)
        control_bar.addWidget(btn_custom_color)

        btn_clear = QPushButton("清空画布")
        btn_clear.clicked.connect(self.canvas.clear_canvas)
        control_bar.addWidget(btn_clear)

        btn_save = QPushButton("保存手绘图片")
        btn_save.clicked.connect(self.save_draw_pic)
        control_bar.addWidget(btn_save)

        btn_insert = QPushButton("插入到手账")
        btn_insert.clicked.connect(self.insert_to_note)
        control_bar.addWidget(btn_insert)

        btn_fullscreen = QPushButton("全屏绘图")
        btn_fullscreen.clicked.connect(self.show_full_screen)
        control_bar.addWidget(btn_fullscreen)

        main_layout.addLayout(control_bar)
        # 画布添加到布局
        main_layout.addWidget(self.canvas)
        self.setLayout(main_layout)

    def select_custom_color(self):
        color = QColorDialog.getColor(self.canvas.pen_color, self, "选择画笔颜色")
        if color.isValid():
            self.canvas.set_pen_color(color)

    def save_draw_pic(self):
        self.save_path = self.canvas.save_draw()

    def insert_to_note(self):
        self.save_path = self.canvas.save_draw()
        if self.save_path:
            self.accept()

    def get_img_path(self):
        return self.save_path

    def show_full_screen(self):
        # 全屏绘图模式
        self.showFullScreen()