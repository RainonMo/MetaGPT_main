
import asyncio
import platform
from typing import Any

import fire

from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team

#from metagpt.config2 import Config
#gpt4 = Config.default()
#glm4 = Config.from_home("zhipu-glm4.yaml")




class Draw(Action):
    """Action: By given an object, describe it without saying the name itself."""

    PROMPT_TEMPLATE: str = """
    ## BACKGROUND
    Suppose you are playing the game "You draw, I Guess". You are the actor to 'draw'. 
    ### The question
    {question} 
    ## Previous guess
    {previous}
    ## YOUR TURN
    Now it's your turn, Describe the question without saying the word itself. 
    If "Previous guess" have content, try something new other then previous used. 
    DO NOT mention the question itself in your response!
    If the question is a combination of multiple words, ANY SINGLE word arr NOT allowed be present in your response.
    技巧：
    1. 如果意思正确但是字数不同，请描述正确答案的文字长度，如“三个字”，“四个字”
    2. 如果是数字表示方式不同，请描述正确答案的数字类型，如“中文数字”，“阿拉伯数字“
    3. 如果给出的答案意思正确但是语言不匹配时，请描述正确答案的语言，如“改用中文”，“答案是英文”
    注意，不要强调规则，请直接说出描述本身。
    Your will respone in Chinese:
    """
    name: str = "draw"

    async def run(self, previous: str, question:str, topic: str):
        prompt = self.PROMPT_TEMPLATE.format(previous=previous, question=question, topic=topic)
        # logger.info(prompt)

        rsp = await self._aask(prompt)

        return rsp

class Guess(Action):
    """Action: By given a descriptin, guess the word or phase."""

    PROMPT_TEMPLATE: str = """
    ## BACKGROUND
    Suppose you are playing the game "You draw, I Guess". You are the actor to 'guess'. 
    ### The topic
    {topic}
    ## The description
    {context}
    ## YOUR TURN
    Now it's your turn, observe the description. Guess what it is, wihtout any other characters. 
    Use the same language as the description.
    再次强调，请直接说答案，不要带有任何其他描述；也不要带有任何标点符号
    Your respone:
    """
    name: str = "Guesser"

    async def run(self, context: str, topic: str):
        prompt = self.PROMPT_TEMPLATE.format(context=context, topic=topic)
        # logger.info(prompt)

        rsp = await self._aask(prompt)

        return rsp


class Drawer(Role):
    name: str = "Drawer"
    profile: str = "Drawer"
    topic: str = ""

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.set_actions([Draw])
        self._watch([UserRequirement, Guess])

    async def _observe(self) -> int:
        await super()._observe()
        # accept messages sent (from opponent) to self, disregard own messages from the last round
        self.rc.news = [msg for msg in self.rc.news if msg.send_to == {self.name}]
        return len(self.rc.news)


    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo 

        memories = self.get_memories()
        mem0 = memories.pop(0)
        if mem0.role == "Human":
            question = f"{mem0.content}" 
        else:
            raise ValueError(f"Question not found: {mem0}")
        
        if len(memories) > 0:
            mem9 = memories[-1]
            latestAnswer = f"{mem9.content}"
            previousTry = "\n".join(f"{msg.sent_from}: {msg.content}" for msg in memories)
        else:
            latestAnswer = ""
            previousTry = ""
        
        if latestAnswer == question:
            totalTries = len([msg for msg in memories if msg.role == "Guesser"])
            rsp = f"Win after {totalTries} tries!"
            logger.info(rsp)

            next_to = "Human"
        else:
            rsp = await todo.run(previous=previousTry, topic=self.topic, question=question)
            next_to = "Guesser"

        msg = Message(
            content=rsp,
            role=self.profile,
            cause_by=type(todo),
            sent_from=self.name,
            send_to=next_to,
        )
        self.rc.memory.add(msg)

        return msg

class Guesser(Role):
    name: str = "Guesser"
    profile: str = "Guesser"
    topic: str = ""

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.set_actions([Guess])
        self._watch([Draw])

    async def _observe(self) -> int:
        await super()._observe()
        # accept messages sent (from opponent) to self, disregard own messages from the last round
        self.rc.news = [msg for msg in self.rc.news if msg.send_to == {self.name}]
        return len(self.rc.news)
    
    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo 

        memories = self.get_memories(k=1)
        context = "\n".join(f"{msg.sent_from}: {msg.content}" for msg in memories)
        # print(context)

        rsp = await todo.run(context=context, topic=self.topic)

        msg = Message(
            content=rsp,
            role=self.profile,
            cause_by=type(todo),
            sent_from=self.name,
            send_to="Drawer"
        )
        self.rc.memory.add(msg)

        return msg

async def drawAguess(idea: str, topic: str, investment: float = 3.0, n_round: int = 5):
    """Run a team of presidents and watch they quarrel. :)"""
    team = Team()
    team.hire([
        #Drawer(topic=topic,config=glm4) ,
        #Guesser(topic=topic,config=gpt4)
        Drawer(topic=topic) ,
        Guesser(topic=topic)
        ])
    team.invest(investment)
    team.run_project(idea, send_to="Drawer")
    await team.run(n_round=n_round)

def main(q: str, topic:str, investment: float = 3.0, n_round: int = 10):
    """
    :param topic: Guess topic, such as "Sports/Movie/Star"
    :param q(uestion): A word, phase to play. Should be a subject belong to the topic.
    :param investment: contribute a certain dollar amount to watch the debate
    :param n_round: maximum rounds of the debate
    :return:
    """
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(drawAguess(q, topic, investment, n_round))


if __name__ == "__main__":
    fire.Fire(main)

# python drawdemo.py --q="一帆风顺" --topic="成语" --investment=3.0 --n_round=10