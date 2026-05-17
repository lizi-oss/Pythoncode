#请使用字典编程：从键盘输入学生的姓名和成绩，输出所有学生的姓名和成绩，并打印全班同学的人数和平均分数
# 先创建空字典
student ={}
while True:
    name = input("输入学生姓名，输入a结束：")
    if name == "a":
        break
    score = float(input("输入成绩："))

    student[name] = score

print(student)
for i in student:
    print("姓名：", i, "成绩：", student[i])

count = len(student)
total = sum(student.values())
avg = total / count
print("人数：", count)
print("平均分：", avg)