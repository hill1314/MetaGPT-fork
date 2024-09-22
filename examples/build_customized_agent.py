"""
Filename: MetaGPT/examples/build_customized_agent.py
Created Date: Tuesday, September 19th 2023, 6:52:25 pm
Author: garylin2099
"""
import asyncio
import re
import subprocess

import fire

from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message


# 定义一个简单的编写代码的动作
class SimpleWriteCode(Action):
    PROMPT_TEMPLATE: str = """
    Write a python function that can {instruction} and provide two runnable test cases.
    Return ```python your_code_here ``` with NO other texts,
    your code:
    """

    name: str = "SimpleWriteCode"

    async def run(self, instruction: str):
        prompt = self.PROMPT_TEMPLATE.format(instruction=instruction)

        # 核心调用
        rsp = await self._aask(prompt)
        # 解析返回的代码
        code_text = SimpleWriteCode.parse_code(rsp)

        return code_text

    @staticmethod
    def parse_code(rsp):
        # 正则匹配
        pattern = r"```python(.*)```"
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        return code_text


# 代码执行动作
class SimpleRunCode(Action):
    name: str = "SimpleRunCode"

    async def run(self, code_text: str):
        # 执行python代码
        result = subprocess.run(["python3", "-c", code_text], capture_output=True, text=True)
        code_result = result.stdout
        logger.info(f"{code_result=}")
        return code_result


# 定义 程序员角色
class SimpleCoder(Role):
    name: str = "Alice"
    profile: str = "SimpleCoder"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化时，绑定动作
        self.set_actions([SimpleWriteCode])

    async def _act(self) -> Message:
        # rc : RoleContext, 角色上下文
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        # 角色可执行的动作
        todo = self.rc.todo  # todo will be SimpleWriteCode()
        # 获取历史消息
        msg = self.get_memories(k=1)[0]  # find the most recent messages
        # 异步执行动作
        code_text = await todo.run(msg.content)
        msg = Message(content=code_text, role=self.profile, cause_by=type(todo))

        return msg

# 定义 具备编写和执行代码 两个功能的角色
class RunnableCoder(Role):
    name: str = "Alice"
    profile: str = "RunnableCoder"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([SimpleWriteCode, SimpleRunCode])
        # 顺序执行模式
        self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)

    async def _act(self) -> Message:
        # 会顺序执行角色所有的的动作
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        # By choosing the Action by order under the hood
        # todo will be first SimpleWriteCode() then SimpleRunCode()
        todo = self.rc.todo

        msg = self.get_memories(k=1)[0]  # find the most k recent messages
        result = await todo.run(msg.content)

        msg = Message(content=result, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg


def main(msg="write a function that calculates the product of a list and run it"):
    role = SimpleCoder()
    # role = RunnableCoder()
    logger.info(msg)
    result = asyncio.run(role.run(msg))
    logger.info(result)


if __name__ == "__main__":
    fire.Fire(main)

# 运行异常：需要设置 API key
#   Value error, Please set your API key in /Users/huleilei9/source/github/ai/MetaGPT-fork/config/config2.yaml
#   [type=value_error, input_value='YOUR_API_KEY', input_type=str]