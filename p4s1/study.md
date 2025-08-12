# venv
* python -v 버전확인
* pip list 설치된 라이브러리 확인
* pip freeze > requirements.txt 설치된 라이브로리 리스트를 저장
* pip uninstall -r requirements.txt -y 질문없이 리스트의 라이브러리를 삭제 공용 PC는 접근급지되어 있어 지울수가 없음
* 가상환경을 만들고 싶은 패스로 이동후 python venv .venv (.venv 디렉토리에 가상환경을 만든다) 
* .gitignore를 만들어 가상환경은 트랙킹 안되게 한다. __pycache__ .venv
* 리포지토리의 루트 폴드에서 . ./p4s1/.venv/bin/activate 이건 vc code에서 자동 반영이 안된다. 이것 하지말고
* vc code에서 ctrl+sht+P나 오른쪽 python 버전을 클릭후 패스를 지정해주면 다음 터미널이라 실행시 자동으로 가상환경이 적용된다. 안되면터미널을 외장으로 설정해줘야 한다고 한다
# python File 처리 

## 파일 읽기/쓰기
지금까지는 기초 학습을 위해 코드에 데이터를 입력하여 데이터를 처리하는 방식으로 진행  
실전에서는 대부분의 경우 데이터가 독립된 파일로 존재하며 데이터 처리를 위해서는 데이터가 저장되어 있는 파일을 열어야 하고 처리가 완료된 데이터를 별도의 파일로 써서 저장해야 함.  
파일 열기/쓰기는 open() 이라는 명령어를 사용  
 

파일 열기 : 파일을 불러와서 저장된 데이터를 처리 형태로 준비  
mode에서 'r' 은 read 를 의미  
open(filename, mode='r')  
 

파일 쓰기 : 처리가 완료된 데이터를 (나중에 다시 쓸 수 있게) 별도의 파일로 저장  
mode에서 'w'은 write 를 의미  
open(filename, mode='w')  
 

 

파일을 읽어서 텍스트 출력하기  
open(filename, mode='r')는 파일을 읽기 모드로 준비한다는 의미이며, 파일에 있는 텍스트를 읽으려면 read() 나 readlines() 사용
read()를 사용한 경우 : 파일의 텍스트 전체를 하나의 문자열로 출력
filename = 'test.txt'
f = open(filename, 'r')     # mode = 부분은 생략해도 됨
print(f)                    # open 자체는 읽기 모드의 정보를 출력

print('-'*10)               # 결과 사이 경계선
lines = f.read()
print(lines)                # 파일 전체의 텍스트를 하나의 문자열로 출력
결과 :

<_io.TextIOWrapper name='test.txt' mode='r' encoding='cp949'>
----------
Hi
My name is
Python.

 

 

readlines() 를 사용하는 경우 : 각 줄을 element 로 하는 리스트를 반환
줄마다 다른 element 로 존재하기 때문에 각 줄의 텍스트 마지막 줄바꿈 문자(\n)도 포함됨
리스트로 반환되기 때문에 FOR문을 이용하여 각 줄을 출력할 수 있음
이 때 print() 자체에도 줄바꿈 기능이 있어 print() 줄바꿈 + 텍스트 끝 줄바꿈이 중복되어 문장 사이에 빈 줄이 생성됨
filename = 'test.txt'
f = open(filename, 'r')
lines = f.readlines()
print(lines)
print('-' * 10)

for line in lines:
    print(line)
결과 :

['Hi\n', 'My name is\n', 'Python.']
----------
Hi

My name is

Python.

 

 

- readlines() 에서 각 줄 사이 빈 줄을 없앨 때는 line.strip() 를 사용
filename = 'test.txt'
f = open(filename, 'r')
lines = f.readlines()
print(lines)
print('-' * 10)

for line in lines:
    line = line.strip()
    print(line)
결과 : 

['Hi\n', 'My name is\n', 'Python.']
----------
Hi
My name is
Python.

 

 

read() vs readlines()
read() : 파일 내 텍스트를 하나의 문자열로 반환
readlines() : 파일 내 텍스트에서 각 줄을 element 로 하는 리스트로 반환
실제 코딩에서는 각 줄을 분석하여 처리하는 경우가 더 흔하기 때문에 readlines() 를 활용
또한 텍스트의 양이 많을 때 불필요하게 전체를 다 반환하는 read() 보다는 줄마다 필요한 정보를 처리할 수 있는 readlines() 를 더 선호
 

처리된 결과를 새로운 파일에 저장하기 (쓰기)
결과로 result_list = ['aaa', 'Hello', 123] 라는 리스트가 나왔다고 가정
이를 새로운 텍스트 파일에 다음과 같이 저장해야함
aaa

Hello

123

 

이번에는 open(filename, 'w') 를 사용해서 result.txt 파일로 저장 해보기

여기서도 mode='w' 대신 'w' 로 생략 가능
우선 쓰기 모드의 open 까지만 실행하면 디렉토리에 result.txt 만 생성되고 아직 아무런 정보를 저장하지 않았기 때문에 빈 파일 상태
쓰기모드로 준비한 후 FOR 문을 통해 result_list 의 element 를 하나씩 저장
이 때 result.txt 에 쓸 때는 w.write(입력 텍스트)를 사용 (참고 : w는 open(~, 'w') 할 때 사용한 변수)
입력 유형은 텍스트여야하기 때문에 element 중 숫자인 123 은 문자형으로 변환해야 함
 

 123 : 숫자형 --> str(123) : 문자형

result_list = ['aaa', 'Hello', 123]

save_filename = 'result.txt'
w = open(save_filename, 'w')

for element in result_list :
    # element 가 문자형이 아니면 문자형으로 변환
    if type(element) != 'str' :
        element = str(element)
    # 텍스트 입력시 마지막에 줄바꿈 문자도 함께 포함
    w.write(element + '\n')

# w.close() 를 해줘야 텍스트 파일에 저장됨
w.close()
 

결과 :


 

 

IF문 대신 str() 을 이용해서 바로 입력 유형 텍스트로 변환

result = ['Hi', 'Hello', 123]

save_filename = 'result.txt'

www = open(save_filename, 'w')

for k in result :
    www.write(str(k) + '\n')
    
www.close()
 

결과:


 

 

쓰기 모드 사용시 주의점
- open(filename, 'w') 는 빈 파일을 생성하는 명령어

- 기존에 있는 텍스트 파일을 열어서 이어서 쓰고 싶어서 w 모드를 사용하면 빈 파일로 바꾼 후 새로 입력하는 텍스트로 덮어쓰기 됨

- 방금 만든 result.txt 를 통한 예시


 

이어쓰기 방법
방법 1 (안전주의)

기존 파일을 먼저 read 모드로 불러서 읽은 후, 기존 텍스트를 다른 이름의 새로운 파일에 write 모드로 저장 + 새로 추가하고 싶은 내용도 새로운 파일에 이어서 w.write() 로 저장
기존 파일은 읽기만 하고 건드리지 않으면서 별도 새 파일에서 이어서 쓰기
filename = 'test.txt'
f = open(filename, 'r')
new_filename = 'test2.txt'
w = open(new_filename, 'w')

# 새파일에 이어서 쓰기
lines = f.read()
w.write(lines + '\n')
w.write('add new lines')
w.close()
 

결과 : 


 

방법 2 (편함주의)

mode = 'w' 대신 mode = 'a' (a는 append 의미)를 사용하여 이어서 쓰기
기존 파일에 이어서 쓰는 방식이기 때문에 방법 1처럼 새로운 별도 파일이 생성되지 않음
편하긴 하지만 수고롭더라도 단계를 이해하면서 백업 데이터(수정하지 않는 기존 파일)를 만들어 두는 방법 1을 선호
filename = 'test.txt'
a = open(filename, 'a')

# 새파일에 이어서 쓰기
a.write('\n' + 'add new lines with mode a')
a.close()
 

결과 :


 

함수, 파일 읽기/쓰기 예제
다음과 같이 두 개의 텍스트 파일이 있다. 

 

grade.txt : 성적-점수 표 정보

student_list.txt : 학생별 성적 리스트

평균이 3.7이 넘는 학생에게는 장학금을 주려고 한다. 위 두 개의 텍스트 파일을 활용하여, 학생별로 누가 장학금을 받을 수 있는지 결과를 result.txt 라는 새 파일에 저장하시오.

result.txt 는 아래와 같이 각 줄이 (학생) : (장학금 여부) 형태로 되어 있어야 함.

 

Python : Scholarship!

Phaethon : No scholarship

Applepiethon : Scholarship!

 

# grade.txt 파일 불러오기

filename = 'grade.txt'
f = open(filename, 'r')
grade = f.readlines()
print(grade)


# 성적 딕셔너리 만들기

grade_dic = {}
for i in range(len(grade)):
    grade_alphabet = grade[i][:2]
    grade_num = float(grade[i][3:6])
    grade_dic[grade_alphabet] = grade_num
f.close()
print(grade_dic)


# student_list.txt 파일 불러오기

filename = 'student_list.txt'
f = open(filename, 'r')
student_list = f.readlines()
print(student_list)


# student grade 딕셔너리 만들기
student_dic = {}

for i in range(len(student_list)) :
    student = student_list[i]
    student = student.strip('\n')
    student = student.split(',')
    student_dic[student[0]] = student[1:]

print(student_dic)


# 학생 이름 넣으면 장학금 여부 나오는 함수 작성

def check_scholarship(student_name):
    student_score = student_dic[student_name]               # 학생 이름 넣으면 student_dic 에서 해당 학생의 성적 리스트 반환
    score_total = 0
    for score in student_score:
        score_total = score_total + grade_dic[score]        # 성적 리스트에서 하나씩 점수 변환하여 total 에 누적
    avg = score_total / len(student_score)                  # 성적 평균내기
    
    if avg > 3.7:
        msg = "Scholarship!"
    else :
        msg = "No scholarship"
        
    return msg                                              # 장학금 지급 여부를 결과로 반환


# result.txt 작성

save_filename = 'result.txt'
w = open(save_filename, 'w')

for student in student_dic :
    w.write(student + ': ' + check_scholarship(student) + '\n')
w.close()


# 작성된 result.txt 확인

filename = 'result.txt'
f = open(filename, 'r')

result = f.read()
print(result)
f.close()
 

result.txt 결과 :


 

 

파이썬 기초 정리
모든 파이썬 코딩의 톱니바퀴가 되는 제어문 3가지 

IF문 : 만약~
FOR문 : ~동안 (~부터 ~까지)
WHILE문 : ~동안 (~가 되지 않는 한 무한 반복)
 

파이썬 코딩에서 반드시 익숙해져야 하는 함수 : 중급 수준 파이썬 사용자가 되기 위해서는 함수 위주로 코딩 해야 함
파일 읽기/쓰기를 통해 튜토리얼 수준이 아닌 실전을 가정하여 파일을 불러오고 처리된 결과를 새로운 파일에 저장
구글 검색을 통해 그때 그때 필요한 코드 사용법을 익히는 것이 매우 중요
코딩 초기 (모르는게 너무 많고 해도해도 끝이 없는 시기)
코딩 안정기/초기 개발 단계 (코드 읽기는 되고, 필요한 세부적인 내용을 찾으며 개발하는 시기)
본격 개발 단계 (큰 틀에서부터 함수/파일 읽기 쓰기 전문적으로 활용하면서 코드를 작성하면서 진행하는 시기)