import json
def read_log_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            log_data = json.load(file)
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
    """
    로그 파일을 읽어서 전체 내용을 반환합니다.
    
    Args:
        filename: 읽을 로그 파일명
        
    Returns:
        파일의 전체 내용 문자열
        
    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        UnicodeDecodeError: 파일 디코딩 오류 시
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            print('파일을 성공적으로 읽었습니다: ' + filename)
            return content
    except FileNotFoundError:
        print('오류: 파일을 찾을 수 없습니다 - ' + filename)
        raise
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


def sort_by_time_desc(log_list):
    """
    로그 리스트를 시간 역순으로 정렬합니다.
    
    Args:
        log_list: 정렬할 로그 리스트
        
    Returns:
        시간 역순으로 정렬된 로그 리스트
    """
    # ISO 8601 형식이므로 문자열 정렬로도 정확한 시간순 정렬 가능
    sorted_list = sorted(log_list, key=lambda x: x['timestamp'], reverse=True)
    return sorted_list


def convert_to_dict(log_list):
    """
    로그 리스트를 사전 객체로 변환합니다.
    간단한 구조: {timestamp: (event, message)}
    
    Args:
        log_list: 변환할 로그 리스트
        
    Returns:
        변환된 사전 객체
    """
    result_dict = {}
    
    for log_entry in log_list:
        timestamp = log_entry['timestamp']
        event = log_entry['event']
        message = log_entry['message']
        result_dict[timestamp] = (event, message)
    
    return result_dict


def save_to_json_manual(data_dict, filename):
    """
    사전 객체를 수동으로 JSON 파일로 저장합니다.
    
    Args:
        data_dict: 저장할 사전 객체 {timestamp: (event, message)}
        filename: 저장할 파일명
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write('{\n')
            
            items = list(data_dict.items())
            for i, (timestamp, event_message) in enumerate(items):
                event, message = event_message
                
                # JSON 형식으로 수동 작성
                file.write('  "' + timestamp + '": ["' + event + '", "' + message + '"]')
                
                # 마지막 항목이 아니면 콤마 추가
                if i < len(items) - 1:
                    file.write(',')
                file.write('\n')
            
            file.write('}\n')
        
        print('JSON 파일로 성공적으로 저장되었습니다: ' + filename)
    except Exception as e:
        print('JSON 파일 저장 오류: ' + str(e))
        raise


def read_json_file(filename):
    """
    JSON 파일을 읽어서 Dict 객체로 변환합니다.
    
    Args:
        filename: 읽을 JSON 파일명
        
    Returns:
        파싱된 Dict 객체
        
    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: JSON 파싱 오류 시
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            print('JSON 파일을 성공적으로 읽었습니다: ' + filename)
            
            # 수동으로 JSON 파싱
            result_dict = parse_json_manual(content)
            return result_dict
            
    except FileNotFoundError:
        print('오류: JSON 파일을 찾을 수 없습니다 - ' + filename)
        raise
    except Exception as e:
        print('JSON 파일 읽기 오류: ' + str(e))
        raise


def parse_json_manual(json_content):
    """
    JSON 문자열을 수동으로 파싱하여 Dict 객체로 변환합니다.
    
    Args:
        json_content: JSON 형식의 문자열
        
    Returns:
        파싱된 Dict 객체
    """
    result_dict = {}
    
    # 중괄호 제거 및 정리
    content = json_content.strip()
    if content.startswith('{') and content.endswith('}'):
        content = content[1:-1].strip()
    
    # 빈 JSON 처리
    if not content:
        return result_dict
    
    # 줄바꿈으로 분할하여 각 라인 처리
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line == ',':
            continue
            
        # 콤마 제거
        if line.endswith(','):
            line = line[:-1]
        
        # key: value 분리
        if ':' in line:
            # 첫 번째 콜론을 기준으로 분리
            colon_index = line.find(':')
            key_part = line[:colon_index].strip()
            value_part = line[colon_index + 1:].strip()
            
            # 키에서 따옴표 제거
            if key_part.startswith('"') and key_part.endswith('"'):
                key = key_part[1:-1]
            else:
                key = key_part
            
            # 값이 배열인지 확인 ["event", "message"]
            if value_part.startswith('[') and value_part.endswith(']'):
                # 배열 파싱
                array_content = value_part[1:-1].strip()
                if array_content:
                    # 콤마로 분리
                    parts = array_content.split(',', 1)  # 최대 2개로 분리
                    if len(parts) >= 2:
                        event = parts[0].strip()
                        message = parts[1].strip()
                        
                        # 따옴표 제거
                        if event.startswith('"') and event.endswith('"'):
                            event = event[1:-1]
                        if message.startswith('"') and message.endswith('"'):
                            message = message[1:-1]
                        
                        result_dict[key] = (event, message)
    
    return result_dict


def display_dict_contents(data_dict):
    """
    Dict 객체의 내용을 보기 좋게 출력합니다.
    
    Args:
        data_dict: 출력할 Dict 객체
    """
    print('Dict 객체 내용:')
    print('총 ' + str(len(data_dict)) + '개의 항목')
    print('구조: {timestamp: (event, message)}')
    print()
    
    count = 0
    for timestamp, event_message in data_dict.items():
        event, message = event_message
        print('  [' + str(count + 1) + '] "' + timestamp + '": ("' + event + '", "' + message + '")')
        count += 1
        
        # 너무 많으면 일부만 표시
        if count >= 10:
            remaining = len(data_dict) - count
            if remaining > 0:
                print('  ... (추가 ' + str(remaining) + '개 항목)')
            break


def print_separator(title):
    """구분선과 제목을 출력합니다."""
    print('\n' + '=' * 60)
    print(' ' + title)
    print('=' * 60)


def main():
    """메인 함수 - 로그 분석 프로그램의 전체 워크플로우를 실행합니다."""
    log_filename = 'mission_computer_main.log'
    json_filename = 'mission_computer_main.json'
    
    try:
        # 1. 로그 파일 읽기
        print_separator('1. 로그 파일 읽기')
        log_content = read_log_file(log_filename)
        print('\n전체 로그 파일 내용:')
        print(log_content)
        
        # 2. 로그를 리스트 객체로 변환
        print_separator('2. 로그를 리스트 객체로 변환')
        log_list = parse_log_to_list(log_content)
        print('총 ' + str(len(log_list)) + '개의 로그 엔트리를 파싱했습니다.')
        print('\n리스트 객체 내용:')
        for i, entry in enumerate(log_list):
            print('  [' + str(i + 1) + '] ' + str(entry))
        
        # 3. 시간 역순으로 정렬
        print_separator('3. 시간 역순으로 정렬')
        sorted_log_list = sort_by_time_desc(log_list)
        print('시간 역순으로 정렬된 리스트:')
        for i, entry in enumerate(sorted_log_list):
            print('  [' + str(i + 1) + '] ' + str(entry))
        
        # 4. 사전 객체로 변환
        print_separator('4. 사전(Dict) 객체로 변환')
        result_dict = convert_to_dict(sorted_log_list)
        print('Dict 객체로 변환 완료')
        print('구조: {timestamp: (event, message)}')
        print('총 키 개수: ' + str(len(result_dict)))
        
        # 처음 3개 항목만 미리보기
        print('\nDict 객체 내용 (처음 3개):')
        count = 0
        for timestamp, event_message in result_dict.items():
            if count < 3:
                print('  "' + timestamp + '": ' + str(event_message))
                count += 1
            else:
                break
        
        # 5. JSON 파일로 저장
        print_separator('5. JSON 파일로 저장')
        save_to_json_manual(result_dict, json_filename)
        
        # 6. JSON 파일 읽기 테스트
        print_separator('6. JSON 파일 읽기 테스트')
        loaded_dict = read_json_file(json_filename)
        print('JSON 파일에서 Dict 객체로 로드 완료')
        display_dict_contents(loaded_dict)
        
        # 7. 데이터 무결성 확인
        print_separator('7. 데이터 무결성 확인')
        if len(result_dict) == len(loaded_dict):
            print('✅ 데이터 개수 일치: ' + str(len(result_dict)) + '개')
        else:
            print('❌ 데이터 개수 불일치')
            print('  원본: ' + str(len(result_dict)) + '개')
            print('  로드: ' + str(len(loaded_dict)) + '개')
        
        # 몇 개 항목 비교
        match_count = 0
        total_check = min(5, len(result_dict))
        
        for i, (timestamp, original_data) in enumerate(result_dict.items()):
            if i >= total_check:
                break
            if timestamp in loaded_dict:
                if original_data == loaded_dict[timestamp]:
                    match_count += 1
        
        print('처음 ' + str(total_check) + '개 항목 중 ' + str(match_count) + '개 일치')
        
        if match_count == total_check:
            print('✅ 데이터 무결성 검증 성공')
        else:
            print('❌ 데이터 무결성 검증 실패')
        
        print_separator('작업 완료')
        print('로그 분석 프로그램이 성공적으로 완료되었습니다!')
        print('결과 파일: ' + json_filename)
        print('JSON 파일 읽기/쓰기 모두 성공!')
        
    except FileNotFoundError:
        print('\n' + log_filename + ' 파일이 현재 디렉토리에 있는지 확인해주세요.')
    except Exception as e:
        print('\n프로그램 실행 중 오류가 발생했습니다: ' + str(e))


if __name__ == '__main__':
    main()