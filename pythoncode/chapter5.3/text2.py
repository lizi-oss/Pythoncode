#2. 编写程序，将由1、2、3、4这4个数字组成的每位数都不相同的所有三位数存入一个列表中并输出该列表。请利用列表推导式解决该问题
result=[100*a+10*b+c for a in [1,2,3,4]for b in[1,2,3,4] for c in[1,2,3,4]if a!=b and b!=c and c!=a]
print(result)