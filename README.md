# 官方文档

https://docs.deepwisdom.ai/main/zh/guide/get_started/quickstart.html


## 下载
```bash
pip install metagpt
```

## 配置

使用config2.yaml

在当前工作目录中创建一个名为config的文件夹，并在其中添加一个名为config2.yaml的新文件。

将示例config2.yaml文件的内容复制到您的新文件中。
将您自己的值填入文件中：

``` yaml
llm:
  api_type: 'openai' # or azure / ollama / groq etc. Check LLMType for more options
  api_key: 'sk-...' # YOUR_API_KEY
  model: 'gpt-4-turbo' # or gpt-3.5-turbo
  # base_url: 'https://api.openai.com/v1'  # or any forward url.
  # proxy: 'YOUR_LLM_PROXY_IF_NEEDED'  # Optional. If you want to use a proxy, set it here.
  # pricing_plan: 'YOUR_PRICING_PLAN' # Optional. If your pricing plan uses a different name than the `model`.
```
## 入门代码
参考官网文档

## 运行

``` bash
python demo.py
```

# 版本

## 0.6
```python
self._init_actions([SimpleWriteCode])
```

## 0.8(最新2024.5.9)
```python
self.set_actions([SimpleWriteCode])
```

# 案例

## GitHubTrending汇总发送
```bash
# import os
# os.environ["WXPUSHER_TOKEN"]

export WXPUSHER_TOKEN=AT_xxxxxxxxxxxxxxxxxxxxxx
export WXPUSHER_UIDS=UID_xxxxxxxxxxxxxxxxxxxxxxxxx

python GithubTrendingSend.py
```