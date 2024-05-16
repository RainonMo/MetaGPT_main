'''
目前为止我们设计的所有思考模式都可以总结为是链式的思考（chain of thought），
能否利用 MetaGPT 框架实现树结构的思考（tree of thought）图结构的思考（graph of thought）？
'''

from metagpt.actions import Action,UserRequirement
from metagpt.roles import Role
from metagpt.logs import logger
from metagpt.schema import Message
from metagpt.team import Team

import random

def guess(digit_position,digit_value):
    password = "483"
    if digit_position not in [1,2,3]:
        return False
    digit_vale_str = str(digit_value)
    if password[digit_position-1] == digit_vale_str:
        return True
    else:
        return False

class Guess(Action):
   async def run(self,pos:int,val:int):
       logger.info(f"我猜 第 {pos} 位是 {val}")
       right = guess(pos,val)
       logger.info(f"{'猜对了' if right else '猜错了'}")
       return right

class Guesser(Role):
    name:str="Guesser"
    profile:str="Guesser"
    goal:str="Guesser"
    pos:int=1
    right:bool=False
    guessed:list = []
    guessnum:int = 0
    def __init__(self,pos:int=1,right:bool=False,**kwargs):
        super().__init__(**kwargs)
    #def __init__(self,name:str="Guesser",profile:str="Guesser",goal:str="Guesser",pos:int=1,**kwargs):
        #super().__init__(name=name,profile=profile,goal=goal,pos=pos,**kwargs)
        self.pos=pos
        self.right = False
        self.guessed = []
        self.guessnum = 0
        # self.init_actions([Guess])
        self.set_actions([Guess])
        if self.pos == 1:
            self._watch([UserRequirement])
        else:
            self._watch([Guess])
    
    async def _think(self) -> None:
        if self.right:
            self.rc.max_react_loop = 0
            logger.info(f"我猜对了,第 {self.pos} 位是 {self.guessnum}")
        else:
            self.rc.max_react_loop = 10
            new_num = random.randint(0,9)
            while new_num in self.guessed:
                new_num = random.randint(0,9)
            self.guessed.append(new_num)
            self.guessnum = new_num
            self.rc.memory.add(Message(content=str(new_num)))
            self._set_state(0)
    async def _act(self) -> Message:
        todo = self.rc.todo
        msg  = self.get_memories(k=1)[0]
        result = await todo.run(self.pos,msg.content)
        logger.info(f"{result} 执行结果 ")
        if result:
            self._set_state(-1)
            self.right = True
            msg = Message(content=str(result),role=self.profile,cause_by=type(todo))
            self.rc.memory.add(msg)
        return msg
    
async def main(idea:str = "Start guess",inverstment:float=3.0,n_round:int=3,add_human:bool=False):
    team = Team()
    team.hire([
        Guesser(name="Guesser1",profile="Guesser1",pos=1),
        Guesser(name="Guesser2",profile="Guesser2",pos=2),
        Guesser(name="Guesser3",profile="Guesser3",pos=3),
    ])
    team.run_project(idea)
    await team.run(n_round=n_round)


if __name__ == "__main__":
    import fire

    fire.Fire(main) 