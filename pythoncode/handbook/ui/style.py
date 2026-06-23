# 粉色细沙流光渐变样式，马卡龙/莫兰迪粉色系，所有窗口控件统一美化
def get_pink_style():
    return """
QMainWindow{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 #FFE6EF, stop:0.4 #FFD6E4, stop:0.8 #FFC8DD, stop:1 #F8D7E8);
}
/* 顶部分页标签 */
QTabBar::tab {
    font-size:16px;
    padding:14px 24px;
}
/* 所有提示文字标签 */
QLabel{
    font-size:15px;
    color:#66394F;
}
/* 单行输入框 */
QLineEdit{
    background:rgba(255,255,255,200);
    border:1px solid #FFB8CC;
    border-radius:10px;
    padding:13px 16px;
    font-size:15px;
}
/* 大文本编辑框（日记/图文手账） */
QTextEdit{
    background:rgba(255,255,255,220);
    border:1px solid #FFC0D4;
    border-radius:12px;
    padding:14px;
    font-size:15px;
}
/* 所有按钮文字+高度加宽 */
QPushButton{
    background:rgba(255,220,232,200);
    border:1px solid #FFA8C0;
    border-radius:10px;
    padding:14px 20px;
    font-size:15px;
    color:#582F40;
    box-shadow: 0 0 6px rgba(255,170,195,0.45);
}
QPushButton:hover{
    background:rgba(255,200,218,230);
    box-shadow: 0 0 10px rgba(255,150,180,0.7);
}
QGroupBox{
    border:1px solid #FFB8CC;
    border-radius:10px;
    font-size:15px;
}
/* 时间选择框 */
QDateTimeEdit{
    padding:11px 14px;
    font-size:15px;
    border:1px solid #FFB8CC;
    border-radius:10px;
}
/* 弹窗全局文字统一放大 */
QDialog QLabel{font-size:15px;}
QDialog QLineEdit{font-size:15px;}
QDialog QPushButton{font-size:15px;}
"""