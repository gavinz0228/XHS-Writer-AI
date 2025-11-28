from flask import Flask, render_template, request, jsonify
import concurrent.futures
from main import fetch_hot_topics, select_interesting_topics, process_single_topic, search_with_tavily, generate_xiaohongshu_post, generate_xhs_card

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    platform = data.get('platform', 'weibo')
    try:
        count = int(data.get('count', 1))
    except (ValueError, TypeError):
        count = 1

    print(f"收到请求: 平台={platform}, 数量={count}")

    # 1. 获取热点话题
    all_hot_topics = fetch_hot_topics(platform)
    if not all_hot_topics:
        return jsonify({"error": "无法获取热点话题"}), 500

    # 2. 挑选有趣话题
    selected_topics = select_interesting_topics(all_hot_topics, count=count)
    if not selected_topics:
        return jsonify({"error": "无法挑选出有趣话题"}), 500

    results = []
    # 3. 并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        future_to_topic = {
            executor.submit(process_single_topic, topic, i+1, len(selected_topics)): topic 
            for i, topic in enumerate(selected_topics)
        }
        
        for future in concurrent.futures.as_completed(future_to_topic):
            try:
                result = future.result()
                if result:
                    # 提取我们需要展示的数据
                    card_data = result.get('card_data', {})
                    images = card_data.get('images', [])
                    # 提取所有图片的URL
                    image_urls = [img['url'] for img in images] if images else []
                    
                    results.append({
                        "topic": result['topic'],
                        "post_file": result['post_file'],
                        "post_content": result.get('post_content', ''),
                        "images": image_urls
                    })
            except Exception as exc:
                print(f"处理话题时出错: {exc}")

    return jsonify({"results": results})

@app.route('/custom')
def custom():
    return render_template('custom.html')

@app.route('/api/generate_custom', methods=['POST'])
def generate_custom():
    data = request.json
    topic = data.get('topic', '').strip()
    
    if not topic:
        return jsonify({"error": "请输入话题内容"}), 400

    print(f"收到自定义话题请求: {topic}")

    try:
        # 1. 搜索
        from main import search_with_tavily, generate_xiaohongshu_post, generate_xhs_card
        
        search_results = search_with_tavily(topic)
        
        # 2. 生成笔记 (字数限制 1000)
        post_content = generate_xiaohongshu_post(topic, "", search_results, word_limit=1000)
        
        # 保存到文件
        import time
        file_name = f"xiaohongshu_custom_{int(time.time())}.md"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(post_content)
            
        # 3. 生成卡片 (分页处理已在 main.py 中实现，但这里我们手动调用了 generate_xhs_card，需要更新逻辑)
        # 为了复用 main.py 的分页逻辑，最好重构代码。但为了快速实现，这里复制分页逻辑。
        
        from main import select_theme
        theme = select_theme(post_content)
        
        chunk_size = 120
        chunks = [post_content[i:i+chunk_size] for i in range(0, len(post_content), chunk_size)]
        
        all_image_urls = []
        for i, chunk in enumerate(chunks):
            print(f"正在生成自定义话题卡片 ({i+1}/{len(chunks)}) (Theme: {theme})...")
            card_data = generate_xhs_card(chunk, count=1, theme=theme)
            if card_data and 'images' in card_data:
                all_image_urls.extend([img['url'] for img in card_data['images']])
        
        return jsonify({
            "topic": topic,
            "post_file": file_name,
            "post_content": post_content,
            "images": all_image_urls
        })

    except Exception as e:
        print(f"处理自定义话题出错: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)
