import math
def circle(r):
    area =math.pi*r*r
    perimeter=2*math.pi*r
    return area,perimeter
#主程序
r=input("请输入您的变量")
rr=(circle(r))
print("半径为：",r"的圆面积为：",rr[0])
print("半径为：",r"的圆周长为：",rr[0])
#在这里的本质就是返回元组，我们输出的时候只需要在解包就行。
#c或者c++用指针传参或者返回struct结构体
#Java用自定义的类或者数组来。
#go的话支持多返回值
#还有一种方法就是对返回的元组进行解包
cr,cp=circle(4)
print("半径为：",r"的圆面积为：",cr)
print("半径为：",r"的圆周长为：",cp)

