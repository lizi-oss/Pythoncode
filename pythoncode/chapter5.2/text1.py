list1=[34,45,67,89,89,98,20,34,560]
list2=[]
a=sum(list1)/len(list1)
for i in range(len(list1)):
    print(f"{i+list1[i]}")
    if list1[i]>a:
        list2.append(list1[i])
print(f"{a}")
print(f"{list2}")

