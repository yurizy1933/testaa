# python -m venv aitrain
# source aitrain/bin/activate
#
# pip install 'ms-swift'
#
# nvidia-smi 英伟达显卡的命令
#
# watch -n 2 nvidia-smi 每两秒展示一次显卡的消耗
#
# nproc_per_node=1
#
# CUDA_VISIBLE_DEVICES=0 \
# swift sft \
#     --model ZhipuAI/glm-4-9b-chat \
#     --train_type lora \
#     --dataset '/ai_train/new_train_02.jsonl' \
#     --num_train_epochs 1 \
#     --per_device_train_batch_size 1 \
#     --per_device_eval_batch_size 1 \
#     --learning_rate 1e-4 \
#     --lora_rank 8 \
#     --lora_alpha 32 \
#     --target_modules all-linear \
#     --gradient_accumulation_steps 16 \
#     --eval_steps 50 \
#     --save_steps 50 \
#     --save_total_limit 5 \
#     --logging_steps 5 \
#     --max_length 10240 \
#     --output_dir output/ai-train-out \
#     --system 'You are a helpful assistant.' \
#     --warmup_ratio 0.05 \
#     --dataloader_num_workers 4 \
#     --dataset_num_proc 4 \
#     --model_name 'api-train-test' \
#     --model_author 'octopus'
#
# 命令行调用自己的模型
# CUDA_VISIBLE_DEVICES=0 \
# swift infer \
#     --adapters output/ai-train-out \  #路径选择你自己的checkpoint 目录
#     --stream true \
#     --temperature 0 \
#     --max_new_tokens 2048


from openai import OpenAI

def test():
    client = OpenAI(
        api_key='EMPTY',
        base_url=f'http://36.213.71.118:30549/v1',
    )
    model = client.models.list().data[0].id
    print(f'model: {model}')

    messages = [{'role': 'user', 'content': '你是谁'}]

    resp = client.chat.completions.create(model=model, messages=messages, max_tokens=512, temperature=0)
    query = messages[0]['content']
    response = resp.choices[0].message.content
    print(f'query: {query}')
    print(f'response: {response}')

if __name__ == '__main__':
    test()