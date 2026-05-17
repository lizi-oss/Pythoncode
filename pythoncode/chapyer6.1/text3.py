 #编写函数get_ poker：
 # 输入参数n(n为1到10之间的正整数)，
 # 要求从52张扑克牌（即一副完整的扑克牌中去掉大小王）中随机抽取n张牌，
 # 并输出这n张牌的花色及牌面，如红桃K、方块A、梅花10、黑桃7等。调用该函数，并验证函数的正确性。
import random
def get_poker():
    suits=["红桃","方块","梅花","黑桃"]
    ranks=["A","2","3","4","5","6","7","8","9","10","J","Q","K"]

    while True:
        n=int(input("请输入从1到10之间的正整数"))
        if 1<=n<=10:
            break;
        print("输入不合法，请重新输入。")
    all_pokers=[suit+rank for suit in suits for rank in ranks]
    #这句话等价于双层循环嵌套的列表元素相加再给另一个列表增加元素
    #random这个用法感觉跟c语言的rand的用法
    selected_pokers=random.sample(all_pokers,n)
    #输出抽取纸牌
    for poker in selected_pokers:
        print(poker,end="、")
#主函数
get_poker()