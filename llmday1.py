import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
load_dotenv()
import json

# -------------------------
# 1. Calculator Tool
# -------------------------

def calculate(expression):
    parts = expression.split()

    first_number = int(parts[0])
    operation = parts[1]
    second_number = int(parts[2])

    if operation == "+":
        result = first_number + second_number
    elif operation == "-":
        result = first_number - second_number
    elif operation == "*":
        result = first_number * second_number
    elif operation == "/":
        result = first_number / second_number

    return result


# -------------------------
# 2. LLM Function
# -------------------------

def ask_llm(prompt, tools=None):

    client = InferenceClient(
        api_key=os.environ["HF_TOKEN"]
    )

    response = client.chat.completions.create(
        model="Qwen/Qwen3-32B",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=100,
        tools=tools,
        tool_choice="auto"
    )

    print(response)

    return response.choices[0].message


# -------------------------
# 3. Agent
# -------------------------

def agent(user_input):

    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a mathematical calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "A mathematical expression such as 25 * 4"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    ]

    decision = ask_llm(
        f"""Decide what to do with this user request.

If it requires mathematical calculation, use the calculate tool

User request: {user_input}

/no_think""",
        tools=tools
    )

    if decision.tool_calls:
        tool_call = decision.tool_calls[0]

        arguments = json.loads(tool_call.function.arguments)

        result = calculate(arguments["expression"])

        return result
    else:
        result =  decision.content


# -------------------------
# 4. Test Agent
# -------------------------

print(agent("what is an AI agent"))