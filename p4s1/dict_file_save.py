import json
def json_readwrite():
    d = {str(i): i*10 for i in range(10)}

    print('dict d', d)
    print('str(d):', str(d))
    print('json.dumps(d):', json.dumps(d))  # 큰따옴표로 변환!

    # JSON 형식으로 파일에 저장
    with open('dic_test.json', 'w') as f:
        f.write(json.dumps(d))

    # 읽기
    with open('dic_test.json', 'r') as f:
        file_content = f.read()
        
    print('file content:', file_content)

    # JSON으로 파싱
    read_d = json.loads(file_content)
    print('converted back:', read_d)
    print(type(read_d))
    
def json_handwrite():
    d = { str(i) : i*10 for i in range(10)}

    print('dict d',d)
    print('str(d)', str(d))
    f = open('dic_test.json','w')
    f.write(str(d).replace("'",'"'))
    f = open('dic_test.json','r')
    read_d = f.read()
    print('read',eval(read_d))
    
json_readwrite()