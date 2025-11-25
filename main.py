import os
import requests
import json
import concurrent.futures
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 初始化客户端
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MD2CARD_API_KEY = os.getenv("MD2CARD_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not OPENAI_API_KEY and not DEEPSEEK_API_KEY:
    raise ValueError("未在环境变量中找到 OPENAI_API_KEY 或 DEEPSEEK_API_KEY。")
if not TAVILY_API_KEY:
    raise ValueError("未在环境变量中找到 TAVILY_API_KEY。")
if not MD2CARD_API_KEY:
    raise ValueError("未在环境变量中找到 MD2CARD_API_KEY。")

# 优先使用 DeepSeek，如果未配置则回退到 OpenAI
if DEEPSEEK_API_KEY:
    print("使用 DeepSeek API...")
    llm_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    llm_model = "deepseek-chat"
else:
    print("使用 OpenAI API...")
    llm_client = OpenAI(api_key=OPENAI_API_KEY)
    llm_model = "gpt-4o"

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

def fetch_hot_topics(platform: str = "weibo"):
    """
    从 orz.ai 每日新闻 API 获取热点话题。
    参数:
        platform (str): 获取热点话题的平台（例如 "weibo", "baidu"）。
    返回:
        list: 包含热点话题 'title' 和 'url' 的字典列表。
    """
    base_url = "https://orz.ai/api/v1/dailynews"
    params = {"platform": platform}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "200" and data.get("data"):
            return [{"title": item["title"], "url": item["url"]} for item in data["data"]]
        else:
            print(f"获取热点话题出错: {data.get('msg', '未知错误')}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"获取热点话题时发生网络错误: {e}")
        return []

def select_interesting_topics(topics: list, count: int = 1):
    """
    使用 LLM 挑选最有趣且符合年轻人喜好的话题。
    参数:
        topics (list): 话题字典列表。
        count (int): 需要挑选的话题数量。
    返回:
        list: 选中的话题字典列表。
    """
    topics_with_indices = [{"index": i, "title": topic['title']} for i, topic in enumerate(topics)]
    
    prompt = f"""
    从以下热点话题列表中，首先过滤掉那些积极向上但内容无聊的话题，然后挑选出 {count} 个最有趣、最能影响年轻人情绪的话题（例如娱乐八卦、热门游戏、网络潮流等）。
    请以JSON格式返回这 {count} 个话题在列表中的索引（index），例如：
    [0, 5, 10]

    热点话题列表:
    {json.dumps(topics_with_indices, ensure_ascii=False)}
    """
    try:
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "你是一个善于发现有趣话题的助手。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        print(f"LLM 原始响应: {response.choices[0].message.content}")
        result = json.loads(response.choices[0].message.content)
        
        selected_indices = []
        if isinstance(result, dict):
            # 尝试在值中查找整数列表
            for key, value in result.items():
                if isinstance(value, list):
                    selected_indices = value
                    break
        elif isinstance(result, list):
            selected_indices = result
            
        print(f"解析出的选中索引: {selected_indices}")
        
        selected_topics = [topics[i] for i in selected_indices if isinstance(i, int) and 0 <= i < len(topics)]
        return selected_topics[:count]
    except Exception as e:
        print(f"挑选有趣话题时出错: {e}")
        return topics[:count]


def search_with_tavily(query: str):
    """
    使用 Tavily API 搜索详细信息。
    参数:
        query (str): 搜索查询词。
    返回:
        str: 搜索结果摘要。
    """
    try:
        response = tavily_client.search(query=query, search_depth="advanced")
        search_results_summary = ""
        if response and response.get("results"):
            for result in response["results"]:
                search_results_summary += result.get("content", "") + "\n"
        return search_results_summary.strip()
    except Exception as e:
        print(f"Tavily 搜索 '{query}' 时出错: {e}")
        return ""

def generate_xiaohongshu_post(topic_title: str, topic_url: str, search_results: str):
    """
    使用 LLM 生成小红书风格的笔记。
    参数:
        topic_title (str): 热点话题标题。
        topic_url (str): 热点话题链接。
        search_results (str): Tavily 搜索到的详细信息。
    返回:
        str: 生成的小红书笔记内容。
    """
    prompt = f"""
    你是一个小红书（Xiaohongshu）的时尚生活博主，请根据以下热点话题和详细信息，
    撰写一篇吸引人的小红书笔记。笔记内容要有趣，活泼，容易调动读者情绪，
    可以使用少量表情符号，多用网络流行语，字数严格控制在 100 字以内。
    请确保笔记内容原创，避免直接复制搜索结果。
    同时生成相关的少于10个的话题# 例如“#娱乐八卦”，“#吃瓜”， 显示在笔记的文本下面。

    热点话题: {topic_title}
    话题链接: {topic_url}
    详细信息:
    {search_results}

    请开始你的创作：
    """

    try:
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "你是一个小红书的时尚，搞笑，关注时事娱乐生活博主。你擅长于使用流行网络用语和编写抓人眼球的标题和内容。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200, # 限制 token 数以确保简短
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成 '{topic_title}' 的小红书笔记时出错: {e}")
        return "生成笔记失败。"

def generate_xhs_card(text: str, keywords: str = "hot topic", count: int = 1):
    """
    使用 md2card API 生成小红书卡片。
    参数:
        text (str): 小红书笔记内容。
        keywords (str): 笔记关键词。
        count (int): 生成图片的数量。
    返回:
        dict: md2card API 返回的 JSON 数据，包含封面、标题、描述、图片等。
    """
    url = "https://md2card.com/api/generate/cover"
    headers = {
        "x-api-key": MD2CARD_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "keywords": keywords,
        "count": count
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"生成小红书卡片时出错: {e}")
        return None

def process_single_topic(topic, index, total):
    """
    处理单个话题：搜索 -> 生成笔记 -> 生成卡片。
    """
    print(f"\n--- 正在处理话题 {index}/{total}: {topic['title']} ---")
    
    print(f"正在搜索详情: {topic['title']}...")
    search_results = search_with_tavily(topic['title'])
    
    if not search_results:
        print(f"未找到 '{topic['title']}' 的详细搜索结果。跳过生成。")
        return None

    print(f"正在生成小红书笔记: {topic['title']}...")
    xiaohongshu_post = generate_xiaohongshu_post(
        topic_title=topic['title'],
        topic_url=topic['url'],
        search_results=search_results
    )

    print(f"\n--- 已生成小红书笔记 ({topic['title']}) ---")
    print(xiaohongshu_post)
    
    file_name = f"xiaohongshu_post_{index}.md"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(f"# {topic['title']}\n\n")
        f.write(f"来源: {topic['url']}\n\n")
        f.write(xiaohongshu_post)
    print(f"笔记已保存至 {file_name}")

    # 生成小红书卡片
    print(f"正在生成小红书卡片: {topic['title']}...")
    keywords = topic['title']
    # 默认生成 1 张卡片
    card_data = generate_xhs_card(text=xiaohongshu_post, keywords=keywords, count=1)
    
    if card_data:
        print(f"'{topic['title']}' 的小红书卡片生成成功。")
        return {
            "topic": topic['title'],
            "post_file": file_name,
            "post_content": xiaohongshu_post,
            "card_data": card_data
        }
    else:
        print(f"'{topic['title']}' 的小红书卡片生成失败。")
        return None

def main():
    print("正在启动 XHSWriter...")
    
    platform = input("请输入获取热点话题的平台 (例如 weibo, baidu, zhihu) [默认: weibo]: ").strip()
    if not platform:
        platform = "weibo"
    
    try:
        topic_count_input = input("请输入要生成的话题数量 [默认: 1]: ").strip()
        topic_count = int(topic_count_input) if topic_count_input else 1
    except ValueError:
        print("输入无效，使用默认值 1。")
        topic_count = 1
        
    all_hot_topics = fetch_hot_topics(platform)

    if not all_hot_topics:
        print("未获取到热点话题。退出。")
        return

    print(f"从 {platform} 获取了 {len(all_hot_topics)} 个热点话题。")
    
    print(f"正在使用 LLM 挑选 {topic_count} 个最有趣的话题...")
    selected_topics = select_interesting_topics(all_hot_topics, count=topic_count)
    
    if not selected_topics:
        print("未选中任何话题。退出。")
        return
        
    print(f"选中的话题: {[topic['title'] for topic in selected_topics]}")

    results_data = []

    # 使用 ThreadPoolExecutor 并行处理话题
    with concurrent.futures.ThreadPoolExecutor(max_workers=topic_count) as executor:
        # 提交所有任务
        future_to_topic = {
            executor.submit(process_single_topic, topic, i+1, len(selected_topics)): topic 
            for i, topic in enumerate(selected_topics)
        }
        
        for future in concurrent.futures.as_completed(future_to_topic):
            topic = future_to_topic[future]
            try:
                result = future.result()
                if result:
                    results_data.append(result)
            except Exception as exc:
                print(f"处理话题 '{topic['title']}' 时产生异常: {exc}")

    # 将所有结果保存为 JSON
    if results_data:
        results_file = "xhs_card_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, ensure_ascii=False, indent=4)
        print(f"\n所有结果已保存至 {results_file}")

if __name__ == "__main__":
    main()