#输入一个包含小括号、中括号和花括号的表达式，判断表达式中的各种括号是否匹配，如：{1+[(2+3)*5/7]} 括号匹配，而{1+[(2+3)*5/7}] 括号则不匹配
s=input("请输入您要检查的表达式")
stack=[]
match={')':'(','}':'{',']':'['}
for i in s:
    if i in match.values():
        stack.append(i)
    elif i in match.keys():
        if not stack:
            print("括号不匹配")
            exit()
        top = stack.pop()
        if top !=match[i]:
            print("括号不匹配")
            exit()
if not stack:
    print("括号匹配")
else:
    print("括号不匹配")