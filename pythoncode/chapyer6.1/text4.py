#编写my_range 函数，实现与rang函数相同的功能。my_range函数头部如下所示：
#def my_range(start=0, stop=None, step=1):
def my_range(start=0, stop=None, step=1):
    if stop is None:
        stop = start
        start = 0

    current = start
    while True:
        if step > 0 and current >= stop:
            break
        if step < 0 and current <= stop:
            break

        yield current

        current += step


if __name__ == "__main__":
    print(list(my_range(5)))
    print(list(my_range(2, 7)))
    print(list(my_range(1, 10, 2)))
    print(list(my_range(10, 1, -2)))