str=[input("请输入您的整数列表")]
vehicle={str}
str0=[vehicle]
str1=[]
str2=[]
for i in str0:
    if str[i] % 2 == 1:
        str1.append(str[i])
    if str[i] % 2 == 0:
        str1.append(str[i])
vehile=str1+str2
print(vehile)
输入一个整数列表，返回一个新列表，要求其中：
(1) 删除所有重复元素
(2) 将奇数放在偶数前面
(3) 保持原有顺序（对于不重复的元素，如原列表中偶数8排在偶数6的前面，则新列表中8也要在6的前面）提示：可以分别创建奇数列表和偶数列表，然后将两个列表合并即为新列表(25分)


