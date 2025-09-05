import time
from concurrent.futures import ThreadPoolExecutor

def print_sum(num1, num2):
    print('start' , num1 , num2, time.ctime())
    time.sleep(3)
    print('sum', num1 + num2, time.ctime())

def main():
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.submit(print_sum, 1, 2)
        executor.submit(print_sum, 2, 3)
        executor.submit(print_sum, 3, 4)
    print("done!")

if __name__ == "__main__":
    main()