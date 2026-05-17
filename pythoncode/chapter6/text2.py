import math


def circle():
    flag = True  # 这里写错了应该令flag等于True那么not true就一直是错的无法进入
    r = float(input("请输入您的半径："))
    while flag:
        if r <= 0:
            print("要求输入应当大于0")
            r = input("请输入您的半径：")
        else:
            flag = False
        area = math.pi * r * r
        perimeter = 2 * math.pi * r
        return (area, perimeter)
    # 主函数
    print(circle())
