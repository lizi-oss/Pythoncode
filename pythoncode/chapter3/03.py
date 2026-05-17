s = input("请输入时间（格式 小时:分钟:秒）：")
h, m, sec = map(int, s.split(':'))
total = h * 60 * 60 + m * 60 + sec

before = total - 1*3600 - 5*60 - 30
if before < 0:
    before = 12 * 3600 + before
h1 = before // 3600
m1 = (before % 3600) // 60
sec1 = before % 60
h1 = 12 if h1 == 0 else h1


after = total + 1*3600 +5*60 +30
if after > 12 * 3600:
    after = after - 12 * 3600
h2 = after // 3600
m2 = (after % 3600) // 60
sec2 = after % 60
h2 = 12 if h2 == 0 else h2

print(f"往前1小时5分30秒：{h1:02d}:{m1:02d}:{sec1:02d}")
print(f"往后1小时5分30秒：{h2:02d}:{m2:02d}:{sec2:02d}")

