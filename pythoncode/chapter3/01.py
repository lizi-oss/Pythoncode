mimacode = 123456
i = 1
while i <= 3:
    text = int(input("请输入您的密码"))
    if text == mimacode:
        print("密码正确")
        break
    else:
        left = 3 - i
        print(f"您还有{left}次机会")
    i = i + 1
if i > 3:
    print("密码错误 ，账户已锁定")
