import os
import requests
import json
import concurrent.futures
from dotenv import load_dotenv
from tavily import TavilyClient
from openai import OpenAI
import logging

# Configure logging
logging.basicConfig(filename='hashtag_debug.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
    从以下热点话题列表中，首先过滤掉那些积极向上但内容无聊的话题，然后挑选出 {count} 个生活资讯/网络焦点（任何和时政的话题除外！）。
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
            # 尝试在值中查找整数列表或单个整数
            for key, value in result.items():
                if isinstance(value, list):
                    selected_indices = value
                    break
                elif isinstance(value, int):
                    selected_indices = [value]
                    break
        elif isinstance(result, list):
            selected_indices = result
            
        print(f"解析出的选中索引: {selected_indices}")
        
        selected_topics = [topics[i] for i in selected_indices if isinstance(i, int) and 0 <= i < len(topics)]
        return selected_topics[:count]
    except Exception as e:
        print(f"挑选有趣话题时出错: {e}")
        return []


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

def generate_xiaohongshu_post(topic_title: str, topic_url: str, search_results: str, word_limit: int = 120):
    """
    使用 LLM 生成小红书风格的笔记。
    参数:
        topic_title (str): 热点话题标题。
        topic_url (str): 热点话题链接。
        search_results (str): Tavily 搜索到的详细信息。
        word_limit (int): 笔记的字数限制。
    返回:
        str: 生成的小红书笔记内容。
    """
    print(f"正在生成小红书笔记: {topic_title} (字数限制: {word_limit})...")

    prompt = f"""
    你是一个小红书爆款笔记创作者。请根据以下热点话题和搜索结果，
    撰写一篇吸引人的小红书笔记。
    可以使用少量表情符号，多用网络流行语，字数严格控制在 {word_limit} 字以内。
    请确保笔记内容原创，避免直接复制搜索结果。
    请不要在笔记内容中包含任何话题#。

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
                {"role": "system", "content": "你是一个关注时事娱乐生活小红书博主。你擅长于你使用讽刺，戏虐的预期调用用户情绪，担内容决定不涉及政治话题。"},
                {"role": "user", "content": prompt}
            ],
            #max_tokens=200, # 限制 token 数以确保简短
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成 '{topic_title}' 的小红书笔记时出错: {e}")
        return "生成笔记失败。"

def generate_hashtags(topic_title: str, xiaohongshu_post: str) -> list:
    """
    使用 LLM 为小红书笔记生成相关的少于10个的话题#。
    参数:
        topic_title (str): 热点话题标题。
        xiaohongshu_post (str): 生成的小红书笔记内容。
    返回:
        list: 包含话题#的字符串列表。
    """
    logging.info(f"正在为 '{topic_title}' 生成话题#...")
    prompt = f"""
    请根据以下小红书笔记内容和话题标题，生成少于10个相关的话题#。
    例如：“#娱乐八卦”，“#吃瓜”，“#时尚穿搭”。
    请以JSON格式返回话题#列表，key为"hashtags"，例如：
    {{"hashtags": ["#话题1", "#话题2", "#话题3"]}}

    话题标题: {topic_title}
    小红书笔记内容:
    {xiaohongshu_post}
    """
    raw_response_content = "" # Initialize to empty string
    try:
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "你是一个善于生成小红书爆款话题#的助手。"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        raw_response_content = response.choices[0].message.content
        logging.info(f"LLM 原始话题#响应: {raw_response_content}")
        result = json.loads(raw_response_content)
        if isinstance(result, list):
            # Ensure each item starts with #
            hashtags = [tag if tag.startswith('#') else f'#{tag}' for tag in result[:10]]
            logging.info(f"生成的话题#: {hashtags}")
            return hashtags
        elif isinstance(result, dict) and "hashtags" in result and isinstance(result["hashtags"], list):
            hashtags = [tag if tag.startswith('#') else f'#{tag}' for tag in result["hashtags"][:10]]
            logging.info(f"生成的话题#: {hashtags}")
            return hashtags
        elif isinstance(result, dict) and "topics" in result and isinstance(result["topics"], list):
            hashtags = [tag if tag.startswith('#') else f'#{tag}' for tag in result["topics"][:10]]
            logging.info(f"生成的话题#: {hashtags}")
            return hashtags
        else:
            logging.warning(f"LLM 返回的话题#格式不正确，返回空列表。原始响应: {result}")
            return []
    except json.JSONDecodeError as e:
        logging.error(f"JSON 解析错误，尝试从原始响应中提取话题#: {e}")
        # Fallback: try to extract hashtags using regex if JSON parsing fails
        import re
        # This regex looks for strings that start with # and contain Chinese characters, letters, or numbers
        # It also handles cases where there might be a missing quote before a hashtag
        potential_hashtags = re.findall(r'#[\w\u4e00-\u9fa5]+', raw_response_content)
        hashtags = [tag for tag in potential_hashtags if tag.startswith('#')][:10]
        logging.info(f"通过正则提取的话题#: {hashtags}")
        return hashtags
    except Exception as e:
        logging.error(f"生成话题#时出错: {e}")
        return []

def select_theme(content: str) -> str:
    """
    根据笔记内容选择最合适的主题
    """
    themes = [
        "apple-notes",
        "coil-notebook",
        "pop-art",
        "bytedance",
        "alibaba",
        "art-deco",
        "glassmorphism",
        "warm",
        "minimal",
        "minimalist",
        "dreamy",
        "nature",
        "xiaohongshu",
        "notebook",
        "darktech",
        "typewriter",
        "watercolor",
        "traditional-chinese",
        "fairytale",
        "business",
        "japanese-magazine",
        "cyberpunk",
        "meadow-dawn"
    ]
    themes = ["pop-art"]
    prompt = f"""
    请根据以下小红书笔记内容，从给定的主题列表中选择一个最合适的主题。
    
    笔记内容:
    {content[:500]}...

    主题列表: {', '.join(themes)}

    请只返回选中的主题名称，不要包含任何其他文字。
    """
    
    try:
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": "你是一个设计专家，擅长为内容匹配视觉风格。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        selected_theme = response.choices[0].message.content.strip().lower()
        
        # 简单的验证
        if selected_theme not in themes:
            print(f"LLM 返回了未知主题 '{selected_theme}'，使用默认主题 'minimal'")
            return 'minimal'
            
        print(f"为笔记选择了主题: {selected_theme}")
        return selected_theme
        
    except Exception as e:
        print(f"选择主题时出错: {e}，使用默认主题 'minimal'")
        return 'minimal'

def generate_xhs_card(text: str, keywords: str = "hot topic", count: int = 1, theme: str = "minimal"):
    """
    使用 md2card API 生成小红书卡片。
    参数:
        text (str): 小红书笔记内容。
        keywords (str): 笔记关键词。
        count (int): 生成图片的数量。
    返回:
        dict: md2card API 返回的 JSON 数据，包含封面、标题、描述、图片等。
    """
    print(f"正在调用 md2card API (Theme: {theme})...")
    url = "https://md2card.com/api/generate"
    headers = {
        "x-api-key": MD2CARD_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "markdown": text,
        "themeMode": "",
        "theme": theme,
        "keywords": keywords,
        "overHiddenMode": True,
        "mdxMode": False,
        "width": 440,
        "height": 586,
        "splitMode": "autoSplit",
        "background": "",
        "font": {
            "family": "MaokenAssortedSans",
            "style": "normal",
            "weight": "400",
            "display": "swap",
            "value": "default",
            "level": 4
        },
        "weChatMode": False
        }
    
    print(f"Request URL: {url}")
    # Mask API Key for logging
    safe_headers = headers.copy()
    if "x-api-key" in safe_headers:
        safe_headers["x-api-key"] = "******"
    print(f"Request Headers: {json.dumps(safe_headers, ensure_ascii=False)}")
    print(f"Request Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"生成小红书卡片时出错: {e}")
        return None

def process_single_topic_text_only(topic, index, total):
    """
    处理单个话题：搜索 -> 生成笔记。
    """
    print(f"\n--- 正在处理话题 {index}/{total}: {topic['title']} ---")
    
    print(f"正在搜索详情: {topic['title']}...")
    search_results = search_with_tavily(topic['title'])
    
    if not search_results:
        print(f"未找到 '{topic['title']}' 的详细搜索结果。跳过生成。")
        return None

    print(f"正在生成小红书笔记: {topic['title']}...")
    # 3. 生成小红书笔记
    xiaohongshu_post = generate_xiaohongshu_post(topic['title'], topic['url'], search_results)
    
    print(f"\n--- 已生成小红书笔记 ({topic['title']}) ---")
    print(xiaohongshu_post)
    
    # 保存笔记到文件
    file_name = f"xiaohongshu_post_{index}.md"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(xiaohongshu_post)
    print(f"笔记已保存至 {file_name}")

    return {
        "topic": topic['title'],
        "post_file": file_name,
        "post_content": xiaohongshu_post
    }

def generate_images_for_post(post_content: str, topic_title: str):
    """
    为指定的笔记内容和标题生成图片。
    """
    
    def generate_for_type(text, theme_override=None, keywords=""):
        theme = theme_override if theme_override else select_theme(text)
        print(f"正在为 '{keywords}' 生成小红书卡片 (Theme: {theme})...")
        card_data = generate_xhs_card(text, keywords=keywords, count=1, theme=theme)
        if card_data and 'images' in card_data and card_data['images']:
            print(f"'{keywords}' 的卡片生成成功 (共 {len(card_data['images'])} 张)。")
            return [img['url'] for img in card_data['images']]
        else:
            print(f"'{keywords}' 的卡片生成失败。")
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # 并行生成标题图和内容图
        future_title = executor.submit(generate_for_type, f"<br/><br/>\n<br/>\n<br/># {topic_title}", theme_override="apple-notes", keywords=topic_title)
        future_content = executor.submit(generate_for_type, post_content, theme_override="pop-art", keywords=topic_title)

        title_images = future_title.result()
        content_images = future_content.result()

    return {
        "title_images": title_images,
        "content_images": content_images
    }

def fetch_hot_topics_from_multiple_sources(platforms: list):
    """
    从多个平台并行获取热点话题。
    参数:
        platforms (list): 平台名称列表。
    返回:
        list: 包含所有平台热点话题的字典列表。
    """
    all_topics = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(platforms)) as executor:
        future_to_platform = {executor.submit(fetch_hot_topics, platform): platform for platform in platforms}
        for future in concurrent.futures.as_completed(future_to_platform):
            platform = future_to_platform[future]
            try:
                topics = future.result()
                if topics:
                    all_topics.extend(topics)
            except Exception as exc:
                print(f"从 {platform} 获取热点话题时产生异常: {exc}")
    return all_topics

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
            executor.submit(process_single_topic_text_only, topic, i+1, len(selected_topics)): topic 
            for i, topic in enumerate(selected_topics)
        }
        
        for future in concurrent.futures.as_completed(future_to_topic):
            topic = future_to_topic[future]
            try:
                result = future.result()
                if result:
                    # Now generate the image
                    images_data = generate_images_for_post(result['post_content'], result['topic'])
                    if images_data:
                        result['card_data'] = images_data
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