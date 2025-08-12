# json 라이브러리 사용 버전
import json


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
    로그 리스트를 사전 객체로 변환합니다 (JSON 포맷 제한사항 준수).
    
    Args:
        log_list: 변환할 로그 리스트
        
    Returns:
        변환된 사전 객체 (중첩 구조 없음)
    """
    result_dict = {}
    
    # 각 로그 엔트리를 인덱스 기반으로 평면화
    for i, log_entry in enumerate(log_list):
        key_prefix = 'log_' + str(i)
        result_dict[key_prefix + '_timestamp'] = log_entry['timestamp']
        result_dict[key_prefix + '_event'] = log_entry['event']
        result_dict[key_prefix + '_message'] = log_entry['message']
    
    # 메타데이터 추가 (평면 구조)
    result_dict['total_entries'] = len(log_list)
    result_dict['sorted_by'] = 'timestamp_desc'
    result_dict['format'] = 'mission_computer_log'
    
    return result_dict

def save_to_json(data_dict, filename):
    """
    사전 객체를 JSON 파일로 저장합니다.
    
    Args:
        data_dict: 저장할 사전 객체
        filename: 저장할 파일명
    """
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data_dict, file, ensure_ascii=False, indent=2)
        print('JSON 파일로 성공적으로 저장되었습니다: ' + filename)
    except Exception as e:
        print('JSON 파일 저장 오류: ' + str(e))
        raise


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
        print('총 키 개수: ' + str(len(result_dict)))
        print('total_entries: ' + str(result_dict['total_entries']))
        
        # 5. JSON 파일로 저장
        print_separator('5. JSON 파일로 저장')
        save_to_json(result_dict, json_filename)
        
        print_separator('작업 완료')
        print('로그 분석 프로그램이 성공적으로 완료되었습니다!')
        print('결과 파일: ' + json_filename)
        
    except FileNotFoundError:
        print('\n' + log_filename + ' 파일이 현재 디렉토리에 있는지 확인해주세요.')
    except Exception as e:
        print('\n프로그램 실행 중 오류가 발생했습니다: ' + str(e))

if __name__ == '__main__':
    main()