from zhipuai import ZhipuAI
import json
from openai import OpenAI




client = ZhipuAI(api_key="4198d249d529406f8b9571bc10aa2142")  # 请填写您自己的APIKey

deepseek_apikey = 'sk-ae89b4e492104945ae83c6a2647410c9'
deepseek_client = OpenAI(api_key=deepseek_apikey, base_url="https://api.deepseek.com")


def zhiputest():
    client = ZhipuAI(api_key="4198d249d529406f8b9571bc10aa2142.Qvg8SQRV9GiKweid")  # 填写您自己的APIKey
    response = client.chat.completions.create(
        model="glm-4",
        messages=[
            {"role": "user",
             "content": "  我对太阳系的行星非常感兴趣，特别是土星。请提供关于土星的基本信息，包括其大小、组成、环系统和任何独特的天文现象。"
             },
        ],
        response_format = {
            'type': 'json_object'
        },
        #stream=True #流式调用
    )
    print(response.choices[0].message)

#异步调用
def zhipu2():
    client = ZhipuAI(api_key="4198d249d529406f8b9571bc10aa2142")  # 请填写您自己的APIKey
    response = client.chat.asyncCompletions.create(
        model="glm-4-0520",  # 填写需要调用的模型编码
        messages=[
            {
                "role": "user",
                "content": "请你作为童话故事大王，写一篇短篇童话故事，故事的主题是要永远保持一颗善良的心，要能够激发儿童的学习兴趣和想象力，同时也能够帮助儿童更好地理解和接受故事中所蕴含的道理和价值观。"
            }
        ],
    )
    print(response)


def zhipufunction():
    client = ZhipuAI(api_key="4198d249d529406f8b9571bc10aa2142")  # 请填写您自己的APIKey
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_train_info",  #函数名
                "description": "根据用户提供的信息查询火车时刻",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "departure": {
                            "type": "string",
                            "description": "出发城市或车站",
                        },
                        "destination": {
                            "type": "string",
                            "description": "目的地城市或车站",
                        },
                        "date": {
                            "type": "string",
                            "description": "要查询的火车日期",
                        },
                    },
                    "required": ["departure", "destination", "date"],
                },
            }
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "你能帮我查一下2024年1月1日从北京南站到上海的火车票吗？"
        }
    ]
    response = client.chat.completions.create(
        model="glm-4-plus",  # 请填写您要调用的模型名称
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    print(response)

def get_flight_number(date:str , departure:str , destination:str):
    flight_number = {
        "北京":{
            "上海" : "1234",
            "广州" : "8321",
        },
        "上海":{
            "北京" : "1233",
            "广州" : "8123",
        }
    }
    return { "flight_number":flight_number[departure][destination] }
def get_ticket_price(date:str , flight_number:str):
    return {"ticket_price": "1000"}

def parse_function_call(model_response,messages):
    # 处理函数调用结果，根据模型返回参数，调用对应的函数。
    # 调用函数返回结果后构造tool message，再次调用模型，将函数结果输入模型
    # 模型会将函数调用结果以自然语言格式返回给用户。
    if model_response.choices[0].message.tool_calls:
        tool_call = model_response.choices[0].message.tool_calls[0]
        args = tool_call.function.arguments
        function_result = {}
        if tool_call.function.name == "get_flight_number":
            function_result = get_flight_number(**json.loads(args))
        if tool_call.function.name == "get_ticket_price":
            function_result = get_ticket_price(**json.loads(args))
        messages.append({
            "role": "tool",
            "content": f"{json.dumps(function_result)}",
            "tool_call_id":tool_call.id
        })
        response = client.chat.completions.create(
            model="glm-4",  # 填写需要调用的模型名称
            messages=messages,
            tools=tools,
        )
        print(response.choices[0].message)
        messages.append(response.choices[0].message.model_dump())


def deepseekOpen():
    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ],
        stream=False
    )
    print(response.choices[0].message.content)

if __name__ == '__main__':
    # zhiputest()
    deepseekOpen()

