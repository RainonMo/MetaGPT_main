import asyncio
import re


import aiohttp

from aiocron import crontab
from bs4 import BeautifulSoup
import fire
from typing import Any
from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message


# Actions 的实现
TRENDING_ANALYSIS_PROMPT = """# 要求
你是一名GitHub趋势分析师，旨在根据最新消息为用户提供富有洞察力和个性化的推荐GitHub趋势。根据上下文，填写以下缺失信息，生成引人入胜、信息丰富的标题，
确保用户发现与其兴趣一致的存储库。

# 关于今日GitHub趋势的标题
## 今日趋势:今日揭秘最热门的GitHub项目！探索流行的编程语言，发现吸引开发人员注意力的关键领域。从**到**，见证前所未有的顶级项目。
## 趋势分类:深入当今的GitHub趋势领域！探索**和**等领域的特色项目。快速了解每个项目，包括编程语言、星号等。
## 榜单亮点:聚焦GitHub Trending上值得关注的项目，包括新工具、创新项目，并迅速获得人气，专注于为用户提供与众不同、引人注目的内容。
---
# 格式示例
```
# 标题
## 今日趋势
如今，**和**仍然是最流行的编程语言。感兴趣的关键领域包括**、**和**。
最受欢迎的项目是Project1和Project2。
## 趋势类别
1.生成型人工智能
- [项目1](https://github/xx/project1):[项目的细节，如明星总数和今天，语言，…]
- [项目2](https://github/xx/project2): ...
...
## 列表的亮点
1.[Project1](https://github/xx/project1):[提供推荐该项目的具体原因]。
...
```
---
# Github趋势
{trending}
"""


class CrawlOSSTrending(Action):
    async def run(self, url: str = "https://github.com/trending?spoken_language_code=zh"):
        async with aiohttp.ClientSession() as client:
            async with client.get(url) as response:
                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")

        repositories = []
        logger.info("来了",repositories)

        for article in soup.select("article.Box-row"):
            repo_info = {}

            repo_info["name"] = (
                article.select_one("h2 a")
                .text.strip()
                .replace("\n", "")
                .replace(" ", "")
            )
            repo_info["url"] = (
                "https://github.com" + article.select_one("h2 a")["href"].strip()
            )

            # Description
            description_element = article.select_one("p")
            repo_info["description"] = (
                description_element.text.strip() if description_element else None
            )

            # Language
            language_element = article.select_one(
                'span[itemprop="programmingLanguage"]'
            )
            repo_info["language"] = (
                language_element.text.strip() if language_element else None
            )

            # Stars and Forks
            stars_element = article.select("a.Link--muted")[0]
            forks_element = article.select("a.Link--muted")[1]
            repo_info["stars"] = stars_element.text.strip()
            repo_info["forks"] = forks_element.text.strip()

            # Today's Stars
            today_stars_element = article.select_one(
                "span.d-inline-block.float-sm-right"
            )
            repo_info["today_stars"] = (
                today_stars_element.text.strip() if today_stars_element else None
            )

            repositories.append(repo_info)
        logger.info("完成了",repositories)

        return repositories


class AnalysisOSSTrending(Action):
    async def run(self, trending: Any):
        return await self._aask(TRENDING_ANALYSIS_PROMPT.format(trending=trending))


# Role实现
class OssWatcher(Role):
    def __init__(
        self,
        name="Codey",
        profile="OssWatcher",
        goal="Generate an insightful GitHub Trending analysis report.",
        constraints="Only analyze based on the provided GitHub Trending data.",
    ):
        super().__init__(name=name, profile=profile, goal=goal, constraints=constraints)
        self.set_actions([CrawlOSSTrending, AnalysisOSSTrending])
        self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        # By choosing the Action by order under the hood
        # todo will be first SimpleWriteCode() then SimpleRunCode()
        todo = self.rc.todo

        msg = self.get_memories(k=1)[0]  # find the most k recent messages
        result = await todo.run(msg.content)

        msg = Message(content=str(result), role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg


def main():
    msg = "https://github.com/trending?spoken_language_code=zh"
    role = OssWatcher()
    # logger.info(msg)
    result = asyncio.run(role.run(msg))
    logger.info(result)


if __name__ == "__main__":
    fire.Fire(main)