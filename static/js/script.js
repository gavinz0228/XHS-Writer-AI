document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    const platformSelect = document.getElementById('platform');
    const countInput = document.getElementById('count');
    const resultsContainer = document.getElementById('results');

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

    function createResultCard(result) {
        const div = document.createElement('div');
        div.className = 'result-card';

        const imageUrl = result.image_url || 'https://via.placeholder.com/300x400?text=No+Image';

        div.innerHTML = `
            <img src="${imageUrl}" alt="${result.topic}" class="card-image" onclick="window.open('${imageUrl}', '_blank')">
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
