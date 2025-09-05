import json
def read_log_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            log_data = json.load(file)
    # 예외 상황(파일 없음, 디코딩 오류 등)에 대비한 예외 처리 구현
    except FileNotFoundError:
        print('오류: 파일을 찾을 수 없습니다 - ' + filename)
        raise
    except json.JSONDecodeError as e:
        print('JSON 파싱 오류: ' + str(e))
        raise
    except Exception as e:
        print('예상치 못한 오류 발생: ' + str(e))
        raise
    return log_data

def read_log_file(filename):
    try:
        # 로그 파일을 읽어서 전체 내용을 반환합니다.
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            print('파일을 성공적으로 읽었습니다: ' + filename)
            return content
    # 예외 상황(파일 없음, 디코딩 오류 등)에 대비한 예외 처리 구현
    except FileNotFoundError:
        print('오류: 파일을 찾을 수 없습니다 - ' + filename)
        raise
    # 파일 디코딩 오류 시
    except UnicodeDecodeError as e:   
        print('디코딩 오류: ' + str(e))
        raise
    except Exception as e:
        print('예상치 못한 오류 발생: ' + str(e))
        raise
def parse_log_to_list(log_content):
    """
    로그 내용을 파싱하여 리스트 객체로 변환합니다.
    
    Args:
        log_content: 로그 파일의 전체 내용
        
    Returns:
        파싱된 로그 데이터의 리스트
    """
    log_list = []
    lines = log_content.strip().split('\n')
    
    # 헤더 라인 건너뛰기
    for line in lines[1:]:  # 첫 번째 라인(헤더) 제외
        if line.strip():  # 빈 라인 무시
            parts = line.split(',', 2)  # 최대 3개로 분할 (timestamp, event, message)
            if len(parts) >= 3:
                log_entry = {
                    'timestamp': parts[0].strip(),
                    'event': parts[1].strip(),
                    'message': parts[2].strip()
                }
                log_list.append(log_entry)
    
    return log_list
def print_log(log_list, count=5, msg=''):
    print(f'{msg} , 로그 항목 수: {len(log_list)}')
    for i, entry in enumerate(log_list[:count]):
        print(f'{i+1:3}: {entry}')

def main():
    filename = 'p4s1/mission_computer_main.log'
    # json_filename = 'p4s1/mission_computer_main.json'
    log_data = read_log_file(filename) #file.readlines()
    log_data = log_data.splitlines()  # 줄 단위로 분리
    print('\n로그 파일 읽기 완료:', filename)
    print('로그 항목 수:', len(log_data))
  
    # 처음 5줄만 출력
    print('mission_computer_main.log 파일을 읽어 전체 내용을 화면에 출력:\n', log_data)  # 처음 5줄만 출력
    print('\n로그 항목, 라인별로 5개만 출력')
    for i in range(5):
        print(f'{i+1}: {log_data[i].strip()}')
    
    # 로그 파일 내용을 콤마(,)를 기준으로 날짜/시간과 메시지를 분리하여 Python의 리스트(List) 객체로 전환
    log_list = []
    headers = log_data[0].strip().split(',')
    header_count = len(headers)  # 0열 헤더의 항목 수를 저장
    for i, line in enumerate(log_data[1:]):
        parts = line.strip().split(',')
        if len(parts) == header_count:
            # 로그 항목이 헤더와 일치하는 경우에만 처리):
            log_entry = [parts[0],parts[1:]]
            log_list.append(log_entry)
    
    print("\n리스트로 만들고 처음 5개 항목만 출력")  # 처음 5개 항목만 출력
    print(log_list[:5])  # 처음 5개 항목만 출력

    # 리스트 객체를 시간 역순으로 정렬하여 출력
    sorted_log_list = sorted(log_list, key=lambda x: x[0], reverse=True)  # 첫 번째 요소(타임스탬프)를 기준으로 정렬
    print_log(sorted_log_list, 5, "날자순으로 소트된 처음 5개 항목만 출력")  # 처음 5개 항목만 출력 # 처음 5개 항목만 출력

    dict_log = dict(sorted_log_list)  # 첫 번째 요소를 키로 사용하여 딕셔너리 생성

    print('\n소팅된 Dict을 5개만 출력')
    for i, (key, value) in enumerate(dict_log.items()):
        if i < 5:
            print(f'{key}: {value}')

        # JSON 파일로 저장0
        # save_to_json_manual(dict_log, json_filename)  # JSON 파일로 저장
        # print(f'로그 데이터를 JSON 파일로 저장했습니다: {json_filename}')
        # JSON 파일로 저장
    try:
        with open('p4s1/mission_computer_main.json', 'w', encoding='utf-8') as json_file:
            json.dump(dict_log, json_file, ensure_ascii=False, indent=4)
        print('로그 데이터를 JSON 파일로 저장했습니다: p4s1/mission_computer_main.json')
    except IOError as e:
        print('파일 저장 오류:', str(e))    
    #사고원인 추론
    print('\n사고원인 추론')
    for entry in sorted_log_list:
        if 'error' in entry[1][1].lower() or 'fail' in entry[1][1].lower():
            print(f"오류 발생: {entry[0]} - {entry[1][1]}") 
if __name__ == "__main__":  
    main()