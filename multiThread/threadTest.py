'''
print_sum() 함수는 3초 대기 후 두 수의 합과 현재 시간을 출력합니다.
main() 함수에서는 이 함수를 실행하는 3개의 스레드를 생성하고 시작합니다.
join()을 통해 각 스레드가 끝날 때까지 기다립니다.
모든 스레드가 종료되면 "done!"을 출력하고, 남아 있는 스레드 목록과 상태를 출력합니다.
'''
import threading  # 파이썬 내장 스레딩 모듈을 임포트
import time       # 시간 관련 함수가 들어있는 모듈을 임포트

# 두 수를 더하고 결과를 출력하는 함수 정의
def print_sum(num1, num2):
    time.sleep(3)  # 3초간 대기 (스레드 동작 확인용)
    print(num1 + num2, time.ctime())  # 두 수의 합과 현재 시간을 출력

def main():
    # 각각 print_sum 함수를 실행하는 스레드 3개 생성
    thread1 = threading.Thread(target=print_sum, args=(1, 2))
    thread2 = threading.Thread(target=print_sum, args=(2, 3))
    thread3 = threading.Thread(target=print_sum, args=(3, 4))

    # 각 스레드를 시작함 → 비동기적으로 실행됨
    thread1.start()
    thread2.start()
    thread3.start()

    # 현재 실행 중인 메인 스레드를 가져옴
    main_thread = threading.current_thread()

    # 현재 실행 중인 모든 스레드를 순회
    for thread in threading.enumerate():
        if thread is main_thread:
            continue  # 메인 스레드는 건너뜀

        thread.join()  # 해당 스레드가 종료될 때까지 대기
        print(thread.name, thread.is_alive())  # 스레드 이름과 종료 여부 출력

    print("done!")  # 모든 스레드가 종료된 후 출력

    # 모든 스레드 상태를 다시 출력 (보통 메인 스레드만 남음)
    for thread in threading.enumerate():
        print(thread.name, thread.is_alive())

# 이 파일이 직접 실행될 때만 main 함수 실행
if __name__ == "__main__":
    main()
