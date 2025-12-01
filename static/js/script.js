document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const platformSelect = document.getElementById('platform');
    const countInput = document.getElementById('count');
    const resultsContainer = document.getElementById('results');
    const generateCustomBtn = document.getElementById('generateCustomBtn');
    const fetchBtn = document.getElementById('fetchBtn');

    if (generateCustomBtn) {
        const customTopicInput = document.getElementById('customTopic');

        generateCustomBtn.addEventListener('click', async () => {
            const topic = customTopicInput.value.trim();
            if (!topic) {
                alert('请输入话题内容');
                return;
            }

            generateCustomBtn.classList.add('loading');
            generateCustomBtn.disabled = true;
            resultsContainer.innerHTML = '';

            try {
                const response = await fetch('/api/generate_custom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic })
                });

                const data = await response.json();

                if (data.error) {
                    alert('生成失败: ' + data.error);
                } else {
                    const card = createResultCard(data);
                    resultsContainer.appendChild(card);
                }

            } catch (error) {
                console.error('Error:', error);
                alert('发生网络错误');
            } finally {
                generateCustomBtn.classList.remove('loading');
                generateCustomBtn.disabled = false;
            }
        });
    }

    if (generateBtn) {
        generateBtn.addEventListener('click', async () => {
            const platform = platformSelect.value;
            const count = countInput.value;

            // UI Loading State
            generateBtn.classList.add('loading');
            generateBtn.disabled = true;
            resultsContainer.innerHTML = ''; // Clear previous results

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ platform, count })
                });

                const data = await response.json();

                if (data.error) {
                    alert('生成失败: ' + data.error);
                    return;
                }

                if (data.results && data.results.length > 0) {
                    data.results.forEach(result => {
                        const card = createResultCard(result);
                        resultsContainer.appendChild(card);
                    });
                } else {
                    resultsContainer.innerHTML = '<p style="text-align:center; width:100%; color:#666;">未生成任何结果，请重试。</p>';
                }

            } catch (error) {
                console.error('Error:', error);
                alert('发生网络错误，请检查控制台。');
            } finally {
                // Reset UI
                generateBtn.classList.remove('loading');
                generateBtn.disabled = false;
            }
        });
    }

    if (fetchBtn) {
        fetchBtn.addEventListener('click', () => {
            const selectedPlatforms = Array.from(document.querySelectorAll('input[name="platform"]:checked')).map(cb => cb.value);
            if (selectedPlatforms.length === 0) {
                alert('请至少选择一个平台');
                return;
            }

            fetchBtn.classList.add('loading');
            resultsContainer.innerHTML = '';

            fetch('/api/events', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ platforms: selectedPlatforms })
            })
            .then(response => response.json())
            .then(data => {
                fetchBtn.classList.remove('loading');
                if (data.events && data.events.length > 0) {
                    data.events.forEach(event => {
                        const card = createEventCard(event);
                        resultsContainer.appendChild(card);
                    });
                } else {
                    resultsContainer.innerHTML = '<p>无法加载热点事件。</p>';
                }
            });
        });

        function createEventCard(event) {
            const card = document.createElement('div');
            card.classList.add('result-card');

            const content = document.createElement('div');
            content.classList.add('card-content');
            card.appendChild(content);

            const title = document.createElement('h3');
            title.classList.add('card-title');
            title.textContent = event.title;
            content.appendChild(title);

            const generatedContent = document.createElement('div');
            generatedContent.classList.add('generated-content');
            generatedContent.style.display = 'none';
            content.appendChild(generatedContent);

            title.addEventListener('click', () => {
                const isOpen = generatedContent.style.display === 'block';
                generatedContent.style.display = isOpen ? 'none' : 'block';
                if (!isOpen && !generatedContent.dataset.loaded) {
                    generateText(event.title, generatedContent);
                }
            });

            return card;
        }

        function generateText(title, contentElement) {
            contentElement.innerHTML = '<div class="loader-small"></div>';
            contentElement.dataset.loaded = true;

            fetch('/api/generate_text_from_event', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title })
            })
            .then(response => response.json())
            .then(data => {
                contentElement.innerHTML = '';
                if (data.error) {
                    contentElement.innerHTML = `<p style="color: var(--primary-color);">生成失败: ${data.error}</p>`;
                } else {
                    const postText = document.createElement('p');
                    postText.classList.add('card-text');
                    postText.textContent = data.post_content;

                    const generateImageBtn = document.createElement('button');
                    generateImageBtn.textContent = '生成图片';
                    generateImageBtn.classList.add('generate-image-btn');
                    generateImageBtn.onclick = (e) => {
                        e.stopPropagation();
                        generateImage(title, data.post_content, contentElement);
                    };

                    const generateHashtagsBtn = document.createElement('button');
                    generateHashtagsBtn.textContent = '生成关键字#';
                    generateHashtagsBtn.classList.add('generate-image-btn');
                    generateHashtagsBtn.onclick = (e) => {
                        e.stopPropagation();
                        generateHashtags(title, data.post_content, contentElement);
                    };

                    const imageContainer = document.createElement('div');
                    imageContainer.classList.add('image-container');

                    const hashtagsContainer = document.createElement('div');
                    hashtagsContainer.classList.add('card-hashtags');

                    contentElement.appendChild(postText);
                    contentElement.appendChild(generateImageBtn);
                    contentElement.appendChild(generateHashtagsBtn);
                    contentElement.appendChild(imageContainer);
                    contentElement.appendChild(hashtagsContainer);
                }
            });
        }

        function generateHashtags(title, postContent, contentElement) {
            const hashtagsContainer = contentElement.querySelector('.card-hashtags');
            hashtagsContainer.innerHTML = '<div class="loader-small"></div>';

            fetch('/api/generate_hashtags_from_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title, post_content: postContent })
            })
            .then(response => response.json())
            .then(data => {
                hashtagsContainer.innerHTML = '';
                if (data.error) {
                    hashtagsContainer.innerHTML = `<p style="color: var(--primary-color);">生成话题#失败: ${data.error}</p>`;
                } else if (data.hashtags && data.hashtags.length > 0) {
                    data.hashtags.forEach(tag => {
                        const tagElement = document.createElement('span');
                        tagElement.classList.add('hashtag');
                        tagElement.textContent = tag;
                        hashtagsContainer.appendChild(tagElement);
                    });
                } else {
                    hashtagsContainer.innerHTML = '<p>未生成任何话题#。</p>';
                }
            });
        }

        function generateImage(title, postContent, contentElement) {
            const imageContainer = contentElement.querySelector('.image-container');
            imageContainer.innerHTML = '<div class="loader-small"></div>';

            fetch('/api/generate_image_from_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title, post_content: postContent })
            })
            .then(response => response.json())
            .then(data => {
                imageContainer.innerHTML = '';
                if (data.error) {
                    imageContainer.innerHTML = `<p style="color: var(--primary-color);">生成图片失败: ${data.error}</p>`;
                } else if (data.card_data && data.card_data.content_images) {
                    data.card_data.content_images.forEach(imageUrl => {
                        const img = document.createElement('img');
                        img.src = imageUrl;
                        imageContainer.appendChild(img);
                    });
                }
            });
        }
    }

    function createResultCard(result) {
        const div = document.createElement('div');
        div.className = 'result-card';

        const imageContainer = document.createElement('div');
        imageContainer.className = 'card-images-container';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'card-content';

        let hashtagsHtml = '';
        if (result.hashtags && result.hashtags.length > 0) {
            hashtagsHtml = `<div class="card-hashtags">`;
            result.hashtags.forEach(tag => {
                hashtagsHtml += `<span class="hashtag">${tag}</span>`;
            });
            hashtagsHtml += `</div>`;
        }

        contentDiv.innerHTML = `
            <h3 class="card-title">${result.topic}</h3>
            <div class="card-text">${result.post_content || '暂无内容'}</div>
            ${hashtagsHtml}
        `;

        div.appendChild(imageContainer);
        div.appendChild(contentDiv);

        if (result.images && result.images.length > 0) {
            let imagesHtml = '';
            result.images.forEach(url => {
                imagesHtml += `<img src="${url}" alt="${result.topic}" class="card-image" onclick="window.open('${url}', '_blank')">`;
            });
            imageContainer.innerHTML = imagesHtml;
        } else {
            imageContainer.innerHTML = `<div class="placeholder">点击生成图片</div>`;
            imageContainer.addEventListener('click', async () => {
                if (imageContainer.classList.contains('loading')) return;

                imageContainer.classList.add('loading');
                imageContainer.innerHTML = '<div class="loader"></div>';

                try {
                    const response = await fetch('/api/generate_images', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            post_content: result.post_content,
                            topic_title: result.topic
                        })
                    });

                    const data = await response.json();

                    if (data.error) {
                        alert('图片生成失败: ' + data.error);
                        imageContainer.innerHTML = `<div class="placeholder error">生成失败，点击重试</div>`;
                    } else {
                        let imagesHtml = '';
                        const titleImages = data.title_images || [];
                        const contentImages = data.content_images || [];
                        const allImages = [...titleImages, ...contentImages];

                        if (allImages.length > 0) {
                            allImages.forEach(url => {
                                imagesHtml += `<img src="${url}" alt="${result.topic}" class="card-image" onclick="window.open('${url}', '_blank')">`;
                            });
                            imageContainer.innerHTML = imagesHtml;
                        } else {
                            imageContainer.innerHTML = `<div class="placeholder error">未返回图片</div>`;
                        }
                    }
                } catch (error) {
                    console.error('Error:', error);
                    alert('发生网络错误');
                    imageContainer.innerHTML = `<div class="placeholder error">网络错误，点击重试</div>`;
                } finally {
                    imageContainer.classList.remove('loading');
                }
            });
        }

        return div;
    }
});
