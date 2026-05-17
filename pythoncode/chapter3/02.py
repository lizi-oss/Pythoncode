a, b = 0, 1
n = int(input("请输入您的数字"))
c = 0
for i in range(n):
    c = c + a
    a, b = b, a + b
print(f"您的前n项和是{c}")
