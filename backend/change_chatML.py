import json

# 원본 파일명과 저장할 파일명 설정
input_file = "eval_fixed_600.jsonl" # 기존 파일
output_file = "train2.jsonl" # MLX용 파일 (my_data 폴더에 넣을 것)

with open(input_file, 'r', encoding='utf-8') as f_in, \
     open(output_file, 'w', encoding='utf-8') as f_out:
    
    for line in f_in:
        data = json.loads(line.strip())
        
        # MLX가 요구하는 대화형(Chat) 포맷으로 조립
        mlx_format = {
            "messages": [
                {"role": "system", "content": data["instruction"]},
                # input은 JSON 형태 그대로 텍스트로 전달
                {"role": "user", "content": json.dumps(data["input"], ensure_ascii=False)},
                # assistant는 최종적으로 뱉어야 할 깔끔한 문자열(response)만 학습
                {"role": "assistant", "content": data["output"]["response"]}
            ]
        }
        
        f_out.write(json.dumps(mlx_format, ensure_ascii=False) + "\n")

print("✨ MLX용 데이터 변환 완료!")