document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const platformSelect = document.getElementById('platform');
    const countInput = document.getElementById('count');
    const resultsContainer = document.getElementById('results');

    const generateCustomBtn = document.getElementById('generateCustomBtn');
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

    function createResultCard(result) {
        const div = document.createElement('div');
        div.className = 'result-card';

        let imagesHtml = '';
        if (result.images && result.images.length > 0) {
            imagesHtml = `<div class="card-images-container">`;
            result.images.forEach(url => {
                imagesHtml += `<img src="${url}" alt="${result.topic}" class="card-image" onclick="window.open('${url}', '_blank')">`;
            });
            imagesHtml += `</div>`;
        } else {
            imagesHtml = `<img src="https://via.placeholder.com/225x300?text=No+Image" class="card-image">`;
        }

        div.innerHTML = `
            ${imagesHtml}
            <div class="card-content">
                <h3 class="card-title">${result.topic}</h3>
                <div class="card-text">${result.post_content || '暂无内容'}</div>
                <div class="card-meta">
                    <span>📄 <a href="/static/${result.post_file}" target="_blank">查看 Markdown</a></span>
                </div>
            </div>
        `;

        return div;
    }
});
