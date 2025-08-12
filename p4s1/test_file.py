def main():
    filename = 'p4s1/mission_computer_main.log'
    json_filename = 'p4s1/mission_computer_main.json'
    # with open(filename, 'r', encoding='utf-8') as file: 

    file = open(filename, 'r', encoding='utf-8')
    
    print('로그 파일 읽기 완료:', filename)
    print('로그 항목 수:', len(log_data))
    print('로그 내용:', log_data[:5])  # 처음 5줄만 출력
    # log_list = []
    # for line in log_data:
    #     parts = line.strip().split(' - ')
    #     if len(parts) == 3:
    #         timestamp, event, message = parts
    #         log_list.append({'timestamp': timestamp, 'event': event, 'message': message})
    # with open(json_filename, 'w', encoding='utf-8') as json_file:
    #     json.dump(log_data, json_file)
        # log_list = read_log_file(log_filename)
        # print('로그 파일 내용:', log_content)
        # print('로그 항목 수:', len(log_list))
        # result_dict = convert_log_to_dict(log_list)
        # print('로그 항목을 사전으로 변환:', result_dict)
        # save_to_json_manual(result_dict, json_filename)
        # print('JSON 파일로 저장 완료:', json_filename)
        # print_separator('2. 로그 항목을 사전으로 변환')
        # log_list = convert_log_to_dict(log_content)
        # print('로그 항목을 사전으로 변환:', log_list)
        # print_separator('3. 사전 객체를 JSON 파일로 저장')
        # save_to_json_manual(log_list, json_filename)
        # print('JSON 파일로 저장 완료:', json_filename)  
if __name__ == "__main__":  
    main()