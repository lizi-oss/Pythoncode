#用户从键盘输入若干个字符串组成一个列表list1，当输入提示为“y”或者“yes”（大小写无关）的时候结束输入，然后将该列表转换为元组tuple1，分别输出list1和tuple1
list1 =[]

while True:
    s = input("请输入字符串（输入y/yes结束）：")
    if s.lower() == 'y' or s.lower() == 'yes':
        break

    list1.append(s)

tuple1 = tuple(list1)

print("列表list1：", list1)
print("元组tuple1：", tuple1)