import re

import fire

from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team

class Report(Action):

    name: str = "转述"

    PROMPT_TEMPLATE: str = """
    这是历史对话记录: {msg} .
    你获取了用户的描述和他的描述答案，你需要转述给猜测人，不能转述答案。
    如果猜测人的猜测不对，继续描述答案，直到猜测人猜对。
    只返回描述，不返回其他文本。
    你的转述:
    """

    async def run(self, msg: str):

        prompt = self.PROMPT_TEMPLATE.format(msg = msg)

        rsp = await self._aask(prompt)

        return rsp

class Guess(Action):

    name: str = "猜测"

    PROMPT_TEMPLATE: str = """

    这是历史对话记录 : {msg} .
    根据转述人的描述猜测物体的名称。只返回你猜测的物体名称，不返回其他文本。
    如果转述人说猜测不正确，请继续根据新的描述猜测物体，直到猜测正确。
    你的猜测:
    """

    async def run(self, msg: str):

        prompt = self.PROMPT_TEMPLATE.format(msg = msg)

        rsp = await self._aask(prompt)

        return rsp

class Describer(Role):

    name: str = "小明"
    profile: str = "描述人"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([Report])
        self._watch([UserRequirement,Guess])

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有记忆
        game_text = await Report().run(msg)
        logger.info(f'描述人 : {game_text}')
        msg = Message(content=game_text, role=self.profile,
                      cause_by=type(todo))

        return msg

class Guesser(Role):

    name: str = "小红"
    profile: str = "猜测人"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([Guess])
        self._watch([Report])

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有记忆
        logger.info(msg)
        game_text = await Guess().run(msg)
        logger.info(f'猜测人 : {game_text}')
        msg = Message(content=game_text, role=self.profile,
                      cause_by=type(todo))

        return msg
    
async def main(
    idea: str = "我的描述是四个字，出远门会说的祝福语。答案是一路顺风",
    investment: float = 3.0,
    n_round: int = 5,
    add_human: bool = False,
):
    logger.info(idea)

    team = Team()
    team.hire(
        [
            Describer(),
            Guesser()
        ]
    )

    team.invest(investment=investment)
    team.run_project(idea)
    await team.run(n_round=n_round)

if __name__ == "__main__":
    fire.Fire(main)
