'''
基于 env 或 team 设计一个你的多智能体团队，尝试让他们完成 你画我猜文字版 ，
要求其中含有两个agent，其中一个agent负责接收来自用户提供的物体描述并转告另一个agent，另一个agent将猜测用户给出的物体名称，
两个agent将不断交互直到另一个给出正确的答案
（也可以在系统之上继续扩展，比如引入一个agent来生成词语，而人类参与你画我猜的过程中）
'''

# 我画的物体是太阳。我的描述是两个字，每天早上都会出现，每天晚上会看不见，它带来光明，带来能量。

import asyncio

from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.environment import Environment

from metagpt.const import MESSAGE_ROUTE_TO_ALL

game = Environment()


class Report(Action):

    name: str = "转述"

    PROMPT_TEMPLATE: str = """
    ## 背景
    现在进行你画我猜的游戏，你是描述者，需要描绘指定词语{word}，注意你的句子中不能出现指定词语{word}。
    只返回描述，不返回其他文本。
    根据上下文，你需要判断猜测者的答案，如果不是{word}，需先回复猜错了，然后继续描述，让他继续猜测；如果正确则回复答对了，游戏结束。
    ## 历史描述
    {msg}
    你的描述:
    """

    async def run(self, msg: str,word:str):

        prompt = self.PROMPT_TEMPLATE.format(msg = msg,word = word)

        rsp = await self._aask(prompt)

        return rsp

class Guess(Action):

    name: str = "猜测"

    PROMPT_TEMPLATE: str = """

     ## 背景
    现在进行你画我猜的游戏，你是猜测者，你需要根据描述者的描述猜测物体，只返回描述，不返回其他文本。
    根据上下文，如果描述者说不对，需要根据描述再次猜测，不得重复猜测物体，直到描述者说回复正确。游戏结束。
    ## 历史描述
    {msg}
    你的猜测:
    """

    async def run(self, msg: str):

        prompt = self.PROMPT_TEMPLATE.format(msg = msg)

        rsp = await self._aask(prompt)

        return rsp

class Describer(Role):

    name: str = "小明"
    profile: str = "描述人"
    word:str = "物体名称"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([Report])
        self._watch([UserRequirement,Guess])

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有记忆
        logger.info(f'描述人的记忆 : {msg}')
        game_text = await Report().run(msg,word=self.word)
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
        logger.info(f'猜测人的记忆 : {msg}')
        game_text = await Guess().run(msg)
        logger.info(f'猜测人 : {game_text}')
        msg = Message(content=game_text, role=self.profile,
                      cause_by=type(todo))

        return msg
    
async def main(word: str, n_round=5):

    game.add_roles([Describer(word=word), Guesser()])

    game.publish_message(
        Message(role="用户", content=word, cause_by=UserRequirement,
                send_to='小明'),
        peekable=False,
    )

    '''
     while n_round > 0:
        # self._save()
        n_round -= 1
        logger.debug(f"max {n_round=} left.")
    '''
    while n_round > 0:
        # self._save()
        n_round -= 1
        logger.debug(f"第 {n_round=} 轮.")

        await game.run()

    #await game.run()
    return game.history

#asyncio.run(main(topic='我的描述是两个字，每天早上都会出现，每天晚上会看不见，它带来光明，带来能量。'))
asyncio.run(main(word='一帆风顺'))