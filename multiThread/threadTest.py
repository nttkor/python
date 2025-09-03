import threading
import time

def print_sum(num1, num2):
    time.sleep(3)
    print(num1 + num2, time.ctime())

def main():
    thread1 = threading.Thread(target=print_sum, args=(1, 2))
    thread2 = threading.Thread(target=print_sum, args=(2, 3))
    thread3 = threading.Thread(target=print_sum, args=(3, 4))

    thread1.start()
    thread2.start()
    thread3.start()

    main_thread = threading.currentThread()
    for thread in threading.enumerate():
        if thread is main_thread:
            continue
        thread.join()
        print(thread.name, thread.is_alive())

    print("done!")

    for thread in threading.enumerate():
        print(thread.name, thread.is_alive())

if __name__ == "__main__":
    main()