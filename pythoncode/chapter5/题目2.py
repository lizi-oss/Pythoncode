vehicle=[1,9,8,7,6,5,13,3,2,1]
for i in range(len(vehicle)-1, -1, -1):
    if vehicle[i]%2==1:
        vehicle.pop(i)
print(f"{vehicle}")