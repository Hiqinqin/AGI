## 尝试用 Function Calling 的方式实现第二课手机中流量包智能客服的例子。
## 需求：智能客服根据用户的咨询，推荐最适合的流量包。
# 初始化
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv
import json

_ = load_dotenv(find_dotenv())

client = OpenAI()


# 一个辅助函数，只为演示方便，不必关注细节
def print_json(data):
    """
    打印参数。如果参数是有结构的（如字典或列表），则以格式化的 JSON 形式打印；
    否则，直接打印该值。
    """
    if hasattr(data, 'model_dump_json'):
        data = json.loads(data.model_dump_json())

    if (isinstance(data, (list, dict))):
        print(json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        ))
    else:
        print(data)


#  描述数据库表结构
database_schema_string = """
CREATE TABLE packages (
    p_name STR NOT NULL, -- 套餐名称
    p_data INT NOT NULL, -- 每月数据流量
    p_price INT NOT NULL, -- 价格，不允许为空
    p_group STR NOT NULL -- 适用人群
);
"""


def get_sql_completion(messages, model="gpt-4o-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        tools=[{
            "type": "function",
            "function": {
                "name": "ask_database",
                "description": "Use this function to answer user questions about business. \
                            Output should be a fully formed SQL query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": f"""
                            SQL query extracting info to answer the user's question.
                            SQL should be written using this database schema:
                            {database_schema_string}
                            The query should be returned in plain text, not in JSON.
                            The query should only contain grammars supported by SQLite.
                            """,
                        }
                    },
                    "required": ["query"],
                }
            }
        }],
    )
    return response.choices[0].message


import sqlite3

# 创建数据库连接
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

# 创建套餐表
cursor.execute(database_schema_string)

# 插入4条明确的模拟记录
mock_data = [
    ('经济套餐', 10   , 50 , '无限制'),
    ('畅游套餐', 100  , 180, '无限制'),
    ('无限套餐', 1000 , 300, '无限制'),
    ('校园套餐', 200  , 150, '在校生'),
]

for record in mock_data:
    cursor.execute('''
    INSERT INTO packages (p_name, p_data, p_price, p_group)
    VALUES (?, ?, ?, ?)
    ''', record)

# 提交事务
conn.commit()

def ask_database(query):
    cursor.execute(query)
    records = cursor.fetchall()
    return records


# prompt = "办个200G的套餐"
# prompt = "有没有流量大的套餐"
prompt = "200元以下，流量大的套餐有啥"
# prompt = "你说那个10G的套餐，叫啥名字"
# prompt = "有没有土豪套餐"

messages = [
    {"role": "system", "content": "你是一个数据分析师，基于数据库的数据回答问题"},
    {"role": "user", "content": prompt}
]
response = get_sql_completion(messages)
if response.content is None:
    response.content = ""
messages.append(response)
print("====Function Calling====")
print_json(response)

if response.tool_calls is not None:
    tool_call = response.tool_calls[0]
    if tool_call.function.name == "ask_database":
        arguments = tool_call.function.arguments
        args = json.loads(arguments)
        print("====SQL====")
        print(args["query"])
        result = ask_database(args["query"])
        print("====DB Records====")
        print(result)

        messages.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": "ask_database",
            "content": str(result)
        })
        response = get_sql_completion(messages)
        messages.append(response)
        print("====最终回复====")
        print(response.content)

# print("=====对话历史=====")
# print_json(messages)