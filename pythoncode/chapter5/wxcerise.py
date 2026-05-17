"""
列表的颠倒和排序
"""
vehicle=[1,2,4,5,6,77,88,5556]
vehicle.reverse()
print(f"{vehicle}")
"""
我写这个纯属是为了试试多行注释，好多一点点来，还有就是reverse这个是颠倒列表，
"""

vehicle.sort()
print(f"{vehicle}")#sort方法用来排序，那个傻叉还看书呢，不赶紧练习，傻叉，默认情况下是升序排序，从小到大排序

vehicle.sort(reverse=True)
print(f"{vehicle}")#如果在sort里面，如果等于true表示降序排序。

vehicle.sort(reverse=False)
print(f"{vehicle}")#如果等于false，那么就表示升序排序

vehicle.sort(key=str)
print(f"{vehicle}")#转换成字符串的大小后升序排列

vehicle.sort(key=len)
print(f"{vehicle}")#按字符串的长度升序排序


number=["xixi","haha","wawa","wowo","popo","ee","wuyule","zhenkaixin","nanguo","xingfu","xiwang","mengxiangchengzhen","ruowuqishi","zhuanghuo","youzhi"]
number.sort()
print(f"{number}")#默认升序排序

number=["xixi","haha","wawa","wowo","popo","ee","wuyule","zhenkaixin","nanguo","xingfu","xiwang","mengxiangchengzhen","ruowuqishi","zhuanghuo","youzhi"]
number.sort(key=len)
print(f"{number}")#按照字符串长度排序

number=["xixi","haha","wawa","wowo","popo","ee","wuyule","zhenkaixin","nanguo","xingfu","xiwang","mengxiangchengzhen","ruowuqishi","zhuanghuo","youzhi"]
number.sort(key=len,reverse=True)
print(f"{number}")
"""
这个的方法是什么？
这是按字符串长度排序，而且是从长到短降序排列。
拆开讲：
key=len
→ 排序的依据不是字符串本身，而是每个字符串的长度
reverse=True
→ 降序（从大到小）
→ 如果是 reverse=False 或不写，就是从小到大
所以这一行的意思是：
把列表按字符串长度从长到短排序
"""
nv=[44,"傻叉","低俗",00,99]
nv.sort()
print(f"{nv}")#python不能直接比较大小

nv=[44,"傻叉","低俗",00,99]
nv.sort(key=len)
print(f"{nv}")#len() 只能给字符串、列表用，数字不能用 len ()！

nv=[44,"傻叉","低俗",00,99]
nv.sort(key=str)
print(f"{nv}")#把所有元素都先转成字符串，再按字符串排序。