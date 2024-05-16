import asyncio
import os

import aiohttp
from bs4 import BeautifulSoup
import fire
from typing import Any,Optional
from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message
import smtplib
from email.mime.text import MIMEText

# Actions 的实现
TRENDING_ANALYSIS_PROMPT = """# Requirements
You are a GitHub Trending Analyst, aiming to provide users with insightful and personalized recommendations based on the latest
GitHub Trends. Based on the context, fill in the following missing information, generate engaging and informative titles, 
ensuring users discover repositories aligned with their interests.Reply with Chinese output content.

# The title about Today's GitHub Trending
## Today's Trends: Uncover the Hottest GitHub Projects Today! Explore the trending programming languages and discover key domains capturing developers' attention. From ** to **, witness the top projects like never before.
## The Trends Categories: Dive into Today's GitHub Trending Domains! Explore featured projects in domains such as ** and **. Get a quick overview of each project, including programming languages, stars, and more.
## Highlights of the List: Spotlight noteworthy projects on GitHub Trending, including new tools, innovative projects, and rapidly gaining popularity, focusing on delivering distinctive and attention-grabbing content for users.
---
# Format Example

```
# [Title]

## Today's Trends
Today, ** and ** continue to dominate as the most popular programming languages. Key areas of interest include **, ** and **.
The top popular projects are Project1 and Project2.

## The Trends Categories
1. Generative AI
    - [Project1](https://github/xx/project1): [detail of the project, such as star total and today, language, ...]
    - [Project2](https://github/xx/project2): ...
...

## Highlights of the List
1. [Project1](https://github/xx/project1): [provide specific reasons why this project is recommended].
...
```

---
# Github Trending
{trending}
"""


class CrawlOSSTrending(Action):
    async def run(self, url: str = "https://github.com/trending"):
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
        logger.info("分析是",trending)
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

class WxPusherClient:
    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "http://wxpusher.zjiecode.com",
    ):
        self.base_url = base_url
        self.token = token or os.environ["WXPUSHER_TOKEN"]
        #self.token = 'AT_Y6******7y'

    async def send_message(
        self,
        content,
        summary: Optional[str] = None,
        content_type: int = 1,
        topic_ids: Optional[list[int]] = None,
        uids: Optional[list[int]] = None,
        verify: bool = False,
        url: Optional[str] = None,
    ):
        payload = {
            "appToken": self.token,
            "content": content,
            "summary": summary,
            "contentType": content_type,
            "topicIds": topic_ids or [],
            #"uids": uids or os.environ["WXPUSHER_UIDS"].split(","),
            "uids": ["UID_lS******BG"],
            "verifyPay": verify,
            "url": url,
        }
        url = f"{self.base_url}/api/send/message"
        return await self._request("POST", url, json=payload)

    async def _request(self, method, url, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()



class EmailSender:
    def __init__(self, mail_host, mail_user, mail_pass, sender):
        self.mail_host = mail_host #如：163邮箱服务器地址
        self.mail_user = mail_user #如：163用户名
        self.mail_pass = mail_pass #密码(部分邮箱为授权码)
        self.sender = sender #邮件发送方邮箱地址

    def send_email(self, receivers, subject, content):
        message = MIMEText(content, 'plain', 'utf-8') #邮件内容设置
        message['Subject'] = subject #邮件主题
        message['From'] = self.sender #发送方信息
        message['To'] = receivers[0] #邮件接受方邮箱地址，注意需要[]包裹，这意味着你可以写多个邮件地址群发

        try:
            smtpObj = smtplib.SMTP()
            smtpObj.connect(self.mail_host, 25)
            smtpObj.login(self.mail_user, self.mail_pass)
            smtpObj.sendmail(self.sender, receivers, message.as_string())
            smtpObj.quit()
            print('success')
        except smtplib.SMTPException as e:
            print('error', e)




def main():
    msg = "https://github.com/trending"
    role = OssWatcher()
    result = asyncio.run(role.run(msg))
    logger.info(result.content)

    # 使用示例
    email_sender = EmailSender(mail_host='smtp.163.com', mail_user='mo******t@163.com', mail_pass='WP******KC', sender='mo******t@163.com')
    email_sender.send_email(receivers=['17******9@qq.com'], subject='今日GitHub趋势分析报告', content=result.content)


if __name__ == "__main__":
    fire.Fire(main)