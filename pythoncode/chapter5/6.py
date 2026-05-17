#适用于序列的常用函数,进一步深入理解为什么数与字符串不能混在一起比较，带着引号的是字符串
vehicle = ['train', 'bus', 'car', 'plan', 'subeay', 'ship']
print(len(vehicle))#得到元素的个数

number = [00, 99, 89, 98, 78, 87, 86, 68, 69]
print(max(number))#得到列表中的最大值

number=[00, 99, 89, 98, 78, 87, 86, 68, 69]
#sort() 没有返回值，所以 a = number.sort(...) 是错的,a=number.sort(key=str)
#min(a)list.sort() 是原地排序，直接改列表本身
print(number)
print(min(number))
print(sum(number))