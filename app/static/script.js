document.addEventListener('DOMContentLoaded', () => {
    // --- DOM要素 ---
    const themeToggleButton = document.getElementById('theme-toggle');
    const threadListView = document.getElementById('thread-list-view');
    const chatView = document.getElementById('chat-view');
    const threadList = document.getElementById('thread-list');
    const createThreadForm = document.getElementById('create-thread-form');
    const backToThreadsButton = document.getElementById('back-to-threads');
    const chatTitle = document.getElementById('chat-title');
    const chatPosts = document.getElementById('chat-posts');
    const createPostForm = document.getElementById('create-post-form');
    const currentThreadIdInput = document.getElementById('current-thread-id');
    const aiGeneratingNotice = document.getElementById('ai-generating-notice');

    let pollingInterval = null;

    // --- APIベースURL ---
    const API_BASE_URL = '/api';

    // --- テーマ切替 ---
    const applyTheme = (theme) => {
        document.body.className = theme;
        localStorage.setItem('theme', theme);
    };

    themeToggleButton.addEventListener('click', () => {
        const currentTheme = localStorage.getItem('theme') || 'dark-theme';
        const newTheme = currentTheme === 'dark-theme' ? 'light-theme' : 'dark-theme';
        applyTheme(newTheme);
    });

    // --- 画面切替 ---
    const showThreadList = () => {
        threadListView.classList.remove('hidden');
        chatView.classList.add('hidden');
        stopPolling();
        fetchThreads();
    };

    const showChatView = (threadId, threadTitle) => {
        threadListView.classList.add('hidden');
        chatView.classList.remove('hidden');
        chatTitle.textContent = threadTitle;
        currentThreadIdInput.value = threadId;
        fetchPosts(threadId);
        startPolling(threadId);
    };

    // --- API呼び出し ---

    // スレッド一覧取得 (DEV-13)
    const fetchThreads = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/threads`);
            if (!response.ok) throw new Error('スレッドの取得に失敗しました');
            const threads = await response.json();
            
            threadList.innerHTML = '';
            threads.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)); // 新しい順にソート
            threads.forEach(thread => {
                const threadItem = document.createElement('div');
                threadItem.className = 'thread-item';
                threadItem.innerHTML = `<a href="#" data-thread-id="${thread.id}" data-thread-title="${thread.title}">${thread.title} (${thread.posts.length})</a>`;
                threadList.appendChild(threadItem);
            });
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    };

    // スレッド作成 (DEV-14)
    createThreadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('thread-title').value;
        const message = document.getElementById('thread-message').value;

        try {
            const response = await fetch(`${API_BASE_URL}/threads`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, message }),
            });
            if (!response.ok) throw new Error('スレッドの作成に失敗しました');
            const newThread = await response.json();
            
            createThreadForm.reset();
            showChatView(newThread.id, newThread.title); // 作成後すぐにチャット画面へ
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    });

    // 投稿一覧取得 (DEV-15)
    const fetchPosts = async (threadId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/threads/${threadId}/posts`);
            if (!response.ok) throw new Error('投稿の取得に失敗しました');
            const posts = await response.json();

            renderPosts(posts);
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    };
    
    const renderPosts = (posts) => {
        chatPosts.innerHTML = '';
        posts.forEach(post => {
            const postElement = document.createElement('div');
            postElement.className = 'post';
            postElement.innerHTML = `
                <div class="post-header">${post.post_id}: <span class="author">${post.author}</span> <span class="date">${new Date(post.created_at).toLocaleString()}</span></div>
                <div class="post-message">${escapeHTML(post.message)}</div>
            `;
            chatPosts.appendChild(postElement);
        });
        // 自動スクロール
        chatPosts.scrollTop = chatPosts.scrollHeight;
    };

    // 投稿作成 (DEV-16)
    createPostForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const threadId = currentThreadIdInput.value;
        const message = document.getElementById('post-message').value;

        try {
            const response = await fetch(`${API_BASE_URL}/threads/${threadId}/posts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message }),
            });
            if (!response.ok) throw new Error('投稿に失敗しました');
            
            document.getElementById('post-message').value = '';
            await fetchPosts(threadId); // 投稿後、即時反映
            startPolling(threadId); // AIのレスを待つためにポーリング開始
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    });

    // ポーリング処理 (DEV-17)
    const checkAiStatus = async (threadId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/threads`);
            if (!response.ok) return;
            const threads = await response.json();
            const currentThread = threads.find(t => t.id === threadId);

            if (currentThread) {
                if (currentThread.is_generating) {
                    aiGeneratingNotice.classList.remove('hidden');
                } else {
                    aiGeneratingNotice.classList.add('hidden');
                    // 生成が終わった可能性があるので、投稿を再取得してポーリングを止める
                    const currentPostCount = chatPosts.children.length;
                    if (currentThread.posts.length > currentPostCount) {
                        renderPosts(currentThread.posts);
                    }
                    stopPolling();
                }
            }
        } catch (error) {
            console.error('ポーリングエラー:', error);
        }
    };

    const startPolling = (threadId) => {
        if (pollingInterval) clearInterval(pollingInterval);
        // 3秒ごとにAIの生成状態を確認
        pollingInterval = setInterval(() => checkAiStatus(threadId), 3000);
    };

    const stopPolling = () => {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
            aiGeneratingNotice.classList.add('hidden');
        }
    };

    // --- イベントリスナー ---
    backToThreadsButton.addEventListener('click', showThreadList);

    threadList.addEventListener('click', (e) => {
        if (e.target.tagName === 'A') {
            e.preventDefault();
            const threadId = e.target.dataset.threadId;
            const threadTitle = e.target.dataset.threadTitle;
            showChatView(threadId, threadTitle);
        }
    });
    
    // --- ユーティリティ ---
    const escapeHTML = (str) => {
        return str.replace(/[&<>"']/g, (match) => {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[match];
        });
    };

    // --- 初期化 ---
    const initialTheme = localStorage.getItem('theme') || 'dark-theme';
    applyTheme(initialTheme);
    showThreadList();
});
