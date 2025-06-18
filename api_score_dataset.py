# pip install openai==1.35.10
import datetime
import json
import openai
import time
import base64
import tqdm
from pathlib import Path
from PIL import Image
from io import BytesIO
import os
import argparse
import sys

with open('/mnt/workspace/xintong/api_key.txt', 'r') as f:
    lines = f.readlines()

API_KEY = lines[0].strip()
BASE_URL = lines[1].strip()

openai.api_key = API_KEY
openai.base_url = BASE_URL

text_temp = """
你是一个专业的翻译质量评估助手。你的任务是对一组翻译进行评估，判断它们是否有效地将原文的意思翻译出来，并根据评分系统给出量化结果。以下是具体的评估步骤和要求：

#### 任务说明：
- 每个样本包含三部分内容：
1. **原文**（图片中的文字内容或文本）。
2. **翻译结果**。
3. **翻译方向**（例如：en2zh 或 zh2en）。

- 你需要根据以下四个维度对翻译进行评估，并为每个维度打分（1-5 分）。最终根据各维度得分计算总体评价。

#### 评分标准：
1. **语义准确性**（1-5 分）：
- **5 分**：完全准确地表达了原文的核心意思，术语选择精确无误，完去符合行业惯例。
- **4 分**：基本准确，但存在轻微的术语选择不够精确的问题。
- **3 分**：部分准确，核心意思表达不完整或存在歧义。
- **2 分**：仅传达了部分核心意思，存在明显错误。
- **1 分**：完全未传达原文的核心意思。

2. **语法正确性**（1-5 分）：
- **5 分**：语法完全正确，符合目标语言的规则。
- **4 分**：语法基本正确，但存在轻微的语法问题。
- **3 分**：语法部分正确，存在一些明显的语法错误。
- **2 分**：语法错误较多，影响理解。
- **1 分**：语法严重错误，完全无法理解。

3. **流畅性**（1-5 分）：
- **5 分**：翻译自然、流畅，易于阅读和理解。
- **4 分**：翻译较为流畅，但存在轻微的生硬感。
- **3 分**：翻译一般，存在一定程度的不自然或拗口。
- **2 分**：翻译不流畅，难以阅读或理解。
- **1 分**：翻译非常不流畅，完全无法阅读。

4. **文化适应性**（1-5 分）：
- **5 分**：完全考虑了目标语言的文化背景，无任何误解或歧义。
- **4 分**：基本符合文化背景，但存在轻微的文化差异问题。
- **3 分**：部分符合文化背景，可能存在一定的误解或歧义。
- **2 分**：与文化背景不符，可能导致较大误解。
- **1 分**：完全忽视文化背景，导致严重误解。

#### 输出格式：
对于每个样本，请按照以下格式输出评估结果：
1. **原文**：[原文内容]
2. **翻译**：[翻译结果]
3. **翻译方向**：[翻译方向]
4. **评估结果**：
- **语义准确性**：[得分]，并简要说明理由。
- **语法正确性**：[得分]，并简要说明理由。
- **流畅性**：[得分]，并简要说明理由。
- **文化适应性**：[得分]，并简要说明理由。
5. **总体评价**：
- **评分公式**：(语义准确性 + 语法正确性 + 流畅性 + 文化适应性) ÷ 4 = 总分。
- **总分**：[总分，范围 1-5]，并总结翻译的整体质量。
最终结果：{{语义准确性：得分，语法正确性：得分，流畅性：得分，文化适应性：得分，总分：得分}}

#### 示例输入：
- 原文：Hello, how are you?
- 翻译：你好，你怎么样？
- 翻译方向：en2zh

#### 示例输出：
1. **原文**：Hello, how are you?
2. **翻译**：你好，你怎么样？
3. **翻译方向**：en2zh
4. **评估结果**：
- **语义准确性**：5 分。翻译完整地表达了原文的问候和询问。
- **语法正确性**：5 分。翻译符合中文语法规则。
- **流畅性**：5 分。翻译自然且易于理解。
- **文化适应性**：5 分。翻译符合中文日常交流习惯。
5. **总体评价**：
- **评分公式**：(5 + 5 + 5 + 5) ÷ 4 = 5。
- **总分**：5 分。翻译准确、流畅且符合文化背景，整体质量优秀。
最终结果：{{语义准确性：5, 语法正确性：5, 流畅性：5, 文化适应性：5, 总分：5}}

#### 当前样本：
- 原文：{src}
- 翻译： {ref}
- 翻译方向：{lang}

请根据上述要求完成评估。"""
            
lang_map = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    'de': "German",
    'fr': "French",
    'it': "Italian",
    'th': "Thai",
    'ru': "Russian",
    'pt': "Portuguese",
    'es': "Spanish",
    'hi': "Hindi",
    'tr': "Turkish",
    'ar': "Arabic",
}


def call_gpt4(text):
    
    response = openai.chat.completions.create(
        # model="模型",
        model = model_name, # 图文
        messages=[
                {
                "role": "user",
                "content": text
            }
        ],
    )
    return response.choices[0].message.content


def score(ref_path, lang, output_path):
    results = {}
    ref = json.load(open(ref_path, "r", encoding="utf-8"))
    src_lang, tgt_lang = lang.split("2")
   
    sleep_times = [5, 10, 20, 40, 60]
    for img, item in tqdm.tqdm(ref.items()):

        src = item["src"]
        tgt = item["mt"]

        if isinstance(src, list):
            src_text = "\n".join(src)
        else:
            src_text = src
        if isinstance(tgt, list):
            tgt_text = "\n".join(tgt)
        else:
            tgt_text = tgt
        
        text = text_temp.format(lang=lang, src=src_text, ref=tgt_text)

        last_error = None  # 用于存储最后一次尝试的错误

        for sleep_time in sleep_times:
            try:
                outputs = call_gpt4(text)
                # outputs = text
                break  # 成功调用时跳出循环
            except Exception as e:
                last_error = e  # 记录最后一次错误
                print(f"Error on {img}: {e}. Retry after sleeping {sleep_time} sec...")
                if "Error code: 400" in str(e) or "Error code: 429" in str(e):
                    time.sleep(sleep_time)
                else:
                    error_file[img] = str(e)
                    outputs = ""
                    break
        else:
            # 如果达到最大重试次数仍然失败，记录空结果, break不会进入else
            print(f"Skipping {img}")
            outputs = ""
            if last_error:  # 确保 last_error 不是 None
                error_file[img] = str(last_error)

        results[img] = {"output": outputs, "ref": item["mt"], "src": item["src"]} 

    json.dump(results, open(output_path, "w", encoding="utf-8"), ensure_ascii=False, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--terminal', 
        type=int, 
        required=False,  # 如果一定要提供terminal参数
        choices=list(range(1, 7)),  # 限定可选值为 1~6
        help="Specify which terminal block (1 to 6) to run"
    )
        
    # 解析命令行参数
    args = parser.parse_args()
    terminal = args.terminal


    # 使用用户输入的模型名
    model_name = "qwen-max-2025-01-25"
    print(f"Using model: {model_name}")

    error_file = {}
    root = f"/mnt/workspace/xintong/pjh/All_result/qwen-max对aibtrans打分结果/"
    # root = "qwen-max对aibtrans打分结果/"

    today=datetime.date.today()
     # dataset100
    langs = ["zh2en","zh2de", "zh2ar", "zh2hi", "zh2ja", "zh2ru", "zh2es"]

    if terminal == 1:
        eval_name = "deepseek-v3"
        print("eval_name:", eval_name)
        test_folder = Path(f"data/{eval_name}/dataset100")
        for lang in langs:
            for test_file in test_folder.rglob("*.json"):
                if test_file.name != f"{lang}.json":
                    continue  # 跳过不是当前语言的 json 文件

                output_path = root + f"{eval_name}_score-{today}/dataset100/{lang}/{test_file.parent.name}/"
                Path(output_path).mkdir(parents=True, exist_ok=True)
                print(output_path)
                score(test_file, lang, output_path + f"{test_file.stem}.json")
    
    elif terminal == 2:
        eval_name = "gemini-2.0-flash-001"
        print("eval_name:", eval_name)
        test_folder = Path(f"data/{eval_name}/dataset100")
        for lang in langs:
            for test_file in test_folder.rglob("*.json"):
                if test_file.name != f"{lang}.json":
                    continue  # 跳过不是当前语言的 json 文件

                output_path = root + f"{eval_name}_score-{today}/dataset100/{lang}/{test_file.parent.name}/"
                Path(output_path).mkdir(parents=True, exist_ok=True)
                print(output_path)
                score(test_file, lang, output_path + f"{test_file.stem}.json")

    elif terminal == 3:
        eval_name = "gpt-4o-2024-11-20"
        print("eval_name:", eval_name)
        test_folder = Path(f"data/{eval_name}/dataset100")
        for lang in langs:
            for test_file in test_folder.rglob("*.json"):
                if test_file.name != f"{lang}.json":
                    continue  # 跳过不是当前语言的 json 文件

                output_path = root + f"{eval_name}_score-{today}/dataset100/{lang}/{test_file.parent.name}/"
                Path(output_path).mkdir(parents=True, exist_ok=True)
                print(output_path)
                score(test_file, lang, output_path + f"{test_file.stem}.json")

    elif terminal == 4:
        eval_name = "qwen-vl-max-2025-01-25"
        print("eval_name:", eval_name)
        test_folder = Path(f"data/{eval_name}/dataset100")
        for lang in langs:
            for test_file in test_folder.rglob("*.json"):
                if test_file.name != f"{lang}.json":
                    continue  # 跳过不是当前语言的 json 文件

                output_path = root + f"{eval_name}_score-{today}/dataset100/{lang}/{test_file.parent.name}/"
                Path(output_path).mkdir(parents=True, exist_ok=True)
                print(output_path)
                score(test_file, lang, output_path + f"{test_file.stem}.json")

            

            

            
