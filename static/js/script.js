document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const platformSelect = document.getElementById('platform');
    const countInput = document.getElementById('count');
    const resultsContainer = document.getElementById('results');
    const generateCustomBtn = document.getElementById('generateCustomBtn');
    const fetchBtn = document.getElementById('fetchBtn');

    // --- Unified Card Generation Logic ---
    
    async function generateImages(topic, postContent, imageContainer, button) {
        if (button.classList.contains('loading')) return;
        button.classList.add('loading');
        button.disabled = true;
        imageContainer.innerHTML = '<div class="loader-small"></div>';

        try {
            const response = await fetch('/api/generate_images', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    post_content: postContent,
                    topic_title: topic
                })
            });

            const data = await response.json();
            imageContainer.innerHTML = '';

            if (data.error) {
                imageContainer.innerHTML = `<p style="color: var(--primary-color);">生成图片失败: ${data.error}</p>`;
                button.disabled = false; // Allow retry
            } else {
                const allImages = [...(data.title_images || []), ...(data.content_images || [])];
                if (allImages.length > 0) {
                    allImages.forEach(url => {
                        const img = document.createElement('img');
                        img.src = url;
                        img.alt = topic;
                        img.className = 'card-image';
                        img.onclick = () => window.open(url, '_blank');
                        imageContainer.appendChild(img);
                    });
                     button.style.display = 'none'; // Hide button on success
                } else {
                    imageContainer.innerHTML = `<p>未返回图片。</p>`;
                    button.disabled = false; // Allow retry
                }
            }
        } catch (error) {
            console.error('Error:', error);
            imageContainer.innerHTML = `<p style="color: var(--primary-color);">网络错误，无法生成图片。</p>`;
            button.disabled = false; // Allow retry
        } finally {
            button.classList.remove('loading');
        }
    }

    async function generateHashtags(topic, postContent, hashtagsContainer, button) {
        if (button.classList.contains('loading')) return;
        button.classList.add('loading');
        button.disabled = true;
        hashtagsContainer.innerHTML = '<div class="loader-small"></div>';

        try {
            const response = await fetch('/api/generate_hashtags_from_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: topic, post_content: postContent })
            });
            const data = await response.json();
            hashtagsContainer.innerHTML = '';

            if (data.error) {
                hashtagsContainer.innerHTML = `<p style="color: var(--primary-color);">生成关键字#失败: ${data.error}</p>`;
                button.disabled = false; // Allow retry
            } else if (data.hashtags && data.hashtags.length > 0) {
                data.hashtags.forEach(tag => {
                    const tagElement = document.createElement('span');
                    tagElement.className = 'hashtag';
                    tagElement.textContent = tag;
                    hashtagsContainer.appendChild(tagElement);
                });
                button.style.display = 'none'; // Hide button on success
            } else {
                hashtagsContainer.innerHTML = '<p>未生成任何关键字#。</p>';
                button.disabled = false; // Allow retry
            }
        } catch (error) {
            console.error('Error:', error);
            hashtagsContainer.innerHTML = `<p style="color: var(--primary-color);">网络错误，无法生成关键字#。</p>`;
            button.disabled = false; // Allow retry
        } finally {
            button.classList.remove('loading');
        }
    }

    function createCardWithContent(result) {
        const card = document.createElement('div');
        card.className = 'result-card';

        const cardContent = document.createElement('div');
        cardContent.className = 'card-content';

        const title = document.createElement('h3');
        title.className = 'card-title';
        title.textContent = result.topic;

        const text = document.createElement('p');
        text.className = 'card-text';
        text.textContent = result.post_content;

        const actions = document.createElement('div');
        actions.className = 'card-actions';

        const generateImagesBtn = document.createElement('button');
        generateImagesBtn.textContent = '生成图片';
        generateImagesBtn.className = 'generate-image-btn';

        const generateHashtagsBtn = document.createElement('button');
        generateHashtagsBtn.textContent = '生成关键字#';
        generateHashtagsBtn.className = 'generate-image-btn';

        const imageContainer = document.createElement('div');
        imageContainer.className = 'image-container';

        const hashtagsContainer = document.createElement('div');
        hashtagsContainer.className = 'card-hashtags';
        
        generateImagesBtn.onclick = (e) => {
            e.stopPropagation();
            generateImages(result.topic, result.post_content, imageContainer, generateImagesBtn);
        };
        
        generateHashtagsBtn.onclick = (e) => {
            e.stopPropagation();
            generateHashtags(result.topic, result.post_content, hashtagsContainer, generateHashtagsBtn);
        };

        actions.appendChild(generateImagesBtn);
        actions.appendChild(generateHashtagsBtn);
        
        cardContent.appendChild(title);
        cardContent.appendChild(text);
        cardContent.appendChild(actions);
        cardContent.appendChild(imageContainer);
        cardContent.appendChild(hashtagsContainer);
        
        card.appendChild(cardContent);
        return card;
    }

    // --- Page-specific Logic ---

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
                    const card = createCardWithContent(data);
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

            generateBtn.classList.add('loading');
            generateBtn.disabled = true;
            resultsContainer.innerHTML = '';

            try {
                const response = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ platform, count })
                });
                const data = await response.json();

                if (data.error) {
                    alert('生成失败: ' + data.error);
                } else if (data.results && data.results.length > 0) {
                    data.results.forEach(result => {
                        const card = createCardWithContent(result);
                        resultsContainer.appendChild(card);
                    });
                } else {
                    resultsContainer.innerHTML = '<p style="text-align:center; width:100%;">未生成任何结果，请重试。</p>';
                }
            } catch (error) {
                console.error('Error:', error);
                alert('发生网络错误，请检查控制台。');
            } finally {
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
                        const card = createEventTitleCard(event);
                        resultsContainer.appendChild(card);
                    });
                } else {
                    resultsContainer.innerHTML = '<p>无法加载热点事件。</p>';
                }
            });
        });

        function createEventTitleCard(event) {
            const card = document.createElement('div');
            card.className = 'result-card event-title-card';
            
            const title = document.createElement('h3');
            title.className = 'card-title';
            title.textContent = event.title;
            card.appendChild(title);

            card.addEventListener('click', () => {
                if (card.classList.contains('loading')) return;
                card.classList.add('loading');
                title.textContent = '正在生成笔记...';

                fetch('/api/generate_text_from_event', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: event.title })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.error) {
                        alert('生成失败: ' + result.error);
                        card.classList.remove('loading');
                        title.textContent = event.title; // Restore title
                    } else {
                        const fullCard = createCardWithContent(result);
                        card.replaceWith(fullCard);
                    }
                }).catch(err => {
                    console.error(err);
                    alert('网络错误');
                    card.classList.remove('loading');
                    title.textContent = event.title;
                });
            }, { once: true }); // Only allow one click

            return card;
        }
    }
});
