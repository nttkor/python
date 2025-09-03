import multiprocessing
import time

def print_sum(num1, num2):
    time.sleep(3)
    print(num1 + num2, time.ctime())

def main():
    process1 = multiprocessing.Process(target=print_sum, args=(1, 2))
    process2 = multiprocessing.Process(target=print_sum, args=(2, 3))
    process3 = multiprocessing.Process(target=print_sum, args=(3, 4))

    process1.start()
    process2.start()
    process3.start()

    for process in multiprocessing.active_children():
        process.join()
        print(process.name, process.pid, process.is_alive())

    print("done!")

    for process in multiprocessing.active_children():
        print(process.name, process.is_alive())

if __name__ == "__main__":
    main()