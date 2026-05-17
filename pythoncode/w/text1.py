while (True):
    str = input("请输入您的字符串")
    if len(str) < 8:
        print("“字符串位数应不少于8位，请重新输入！”")
    else:
        count = 0
        for i in range(len(str)):
            if 1<=int(str)<=9:
                count+=1
                break
        for i in range(len(str)):
            if 'a'<=str<='z' or'A'<=str<='Z':
                count+=1
                break
        for i in range(len(str)):
            a=0;
            if 1<=str<=9 or 'a'<=str<='z' or'A'<=str<='Z':
                a+=1
        if a!=len(str):
            count+=1
        if(count==1):
            print("“字符串中只包含一类字符”")
            break
        if (count == 2):
            print("“字符串中包含两类字符”")
            break
        if (count == 1):
            print("“字符串中包含三类字符”")
            break

#编写Python程序实现以下功能：输入一个不少于8位的字符串（如”12abc@#%12y”）
# 然后输出字符串的分析结果。字符串中可包含数字字符、字母和其他符号三类
# 。若输入的字符串位数少于8位，则不进行分析，并给出提示“字符串位数应不少于8位，请重新输入！”，这时需要用户重新输入一个字符串直至符合要求。
# 若字符串位数在8位及以上，则进行分析：若字符串中字符属于同一类字符(即数字字符、字母或其他符号)，则输出：“字符串中只包含一类字符”；
# 若字符属于不同的两类字符，则输出：“字符串中包含两类字符”；若字符属于不同的三类字符，则输出：“字符串中包含三类字符”。 (25分)




