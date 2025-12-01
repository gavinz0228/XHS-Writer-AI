from flask import Flask, render_template, request, jsonify
import concurrent.futures
from main import fetch_hot_topics, select_interesting_topics, process_single_topic_text_only, generate_images_for_post, search_with_tavily, generate_xiaohongshu_post, generate_xhs_card, select_theme, generate_hashtags, fetch_hot_topics_from_multiple_sources

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/events')
def events():
    return render_template('events.html')

@app.route('/api/events', methods=['POST'])
def api_events():
    data = request.json
    platforms = data.get('platforms', [])
    if not platforms:
        return jsonify({"events": []})
        
    events = fetch_hot_topics_from_multiple_sources(platforms)
    return jsonify({"events": events})

@app.route('/api/generate_text_from_event', methods=['POST'])
def generate_text_from_event():
    data = request.json
    title = data.get('title', '').strip()
    
    if not title:
        return jsonify({"error": "请输入话题内容"}), 400

    print(f"收到生成文本请求: {title}")

    try:
        # 1. 搜索
        search_results = search_with_tavily(title)
        
        # 2. 生成笔记
        post_content = generate_xiaohongshu_post(title, "", search_results)
        
        return jsonify({
            "topic": title,
            "post_content": post_content
        })

    except Exception as e:
        print(f"处理生成文本请求出错: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_hashtags_from_text', methods=['POST'])
def generate_hashtags_from_text():
    data = request.json
    title = data.get('title', '').strip()
    post_content = data.get('post_content', '').strip()
    
    if not title or not post_content:
        return jsonify({"error": "缺少话题或笔记内容"}), 400

    print(f"收到生成话题#请求: {title}")

    try:
        # 1. 生成话题#
        hashtags = generate_hashtags(title, post_content)
        
        return jsonify({
            "hashtags": hashtags
        })

    except Exception as e:
        print(f"处理生成话题#请求出错: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_image_from_text', methods=['POST'])
def generate_image_from_text():
    data = request.json
    title = data.get('title', '').strip()
    post_content = data.get('post_content', '').strip()
    
    if not title or not post_content:
        return jsonify({"error": "缺少话题或笔记内容"}), 400

    print(f"收到生成图片请求: {title}")

    try:
        # 1. 生成图片
        images_data = generate_images_for_post(post_content, title)
        
        return jsonify({
            "card_data": images_data
        })

    except Exception as e:
        print(f"处理生成图片请求出错: {e}")
        return jsonify({"error": str(e)}), 500

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
            executor.submit(process_single_topic_text_only, topic, i+1, len(selected_topics)): topic 
            for i, topic in enumerate(selected_topics)
        }
        
        for future in concurrent.futures.as_completed(future_to_topic):
            try:
                result = future.result()
                if result:
                    results.append({
                        "topic": result['topic'],
                        "post_file": result['post_file'],
                        "post_content": result.get('post_content', ''),
                        "hashtags": result.get('hashtags', [])
                    })
            except Exception as exc:
                print(f"处理话题时出错: {exc}")

    return jsonify({"results": results})

@app.route('/api/generate_images', methods=['POST'])
def generate_images():
    data = request.json
    post_content = data.get('post_content', '')
    topic_title = data.get('topic_title', '')

    if not post_content or not topic_title:
        return jsonify({"error": "缺少 'post_content' 或 'topic_title'"}), 400

    # This function now returns a dict with 'title_images' and 'content_images'
    images_data = generate_images_for_post(post_content, topic_title)

    if images_data and (images_data.get('title_images') or images_data.get('content_images')):
        return jsonify(images_data)
    else:
        return jsonify({"error": "无法生成图片"}), 500

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
        from main import search_with_tavily, generate_xiaohongshu_post, generate_xhs_card, select_theme, generate_hashtags
        
        search_results = search_with_tavily(topic)
        
        # 2. 生成笔记 (字数限制 120)
        post_content = generate_xiaohongshu_post(topic, "", search_results, word_limit=120)
        
        # 保存到文件
        import time
        file_name = f"xiaohongshu_custom_{int(time.time())}.md"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(post_content)
            
        # 3. 生成话题#
        hashtags = generate_hashtags(topic, post_content)

        # 4. 生成图片 (标题+内容)
        print(f"正在为自定义话题生成图片: {topic}...")
        images_data = generate_images_for_post(post_content, topic)

        all_image_urls = []
        if images_data:
            title_images = images_data.get('title_images', [])
            content_images = images_data.get('content_images', [])
            all_image_urls.extend(title_images)
            all_image_urls.extend(content_images)
        
        return jsonify({
            "topic": topic,
            "post_file": file_name,
            "post_content": post_content,
            "images": all_image_urls,
            "hashtags": hashtags
        })

    except Exception as e:
        print(f"处理自定义话题出错: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
