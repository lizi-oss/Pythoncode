#输入5个整数放到列表list1中，输出下标及值，然后将列表list1中大于平均值的元素组成一个新列表list2，输出平均值和列表list2。请利用列表推导式解决该问题
list1 = [int(input()) for _ in range(5)]

for i in range(len(list1)):
    print(f"下标{i}，值{list1[i]}")

avg = sum(list1) / len(list1)

list2 = [x for x in list1 if x > avg]

print("平均值：", avg)
print("大于平均值的元素列表list2：", list2)
