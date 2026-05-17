while (True):
    str1=[]
    s = input("请输入您的短语（输入y/yes结束）：")
    if s.lower() == 'y' or s.lower() == 'yes':
        break
    for i in s:
        s.capitalize()
        if 'A'<=s <='Z':
            str1.append(s)
        s.pop(i)
print(str)
#缩写词由一个短语中每个单词的第一个字母组成且全为大写。
# 例如，CPU是短语 central processing unit的缩写。
# 编写程序，输入短语（短语各个单词间用空格隔开），然后输出对应的缩写。
# 输出缩写后，提示用户是否继续输入，若用户输入“y”或者“Y”时则继续，否则退出。 (25分)


