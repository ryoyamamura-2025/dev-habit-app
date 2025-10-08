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
                // 削除ボタンを追加
                threadItem.innerHTML = `
                    <a href="#" class="thread-link" data-thread-id="${thread.id}" data-thread-title="${thread.title}">${thread.title} (${thread.posts.length})</a>
                    <button class="delete-thread-button" data-thread-id="${thread.id}">削除</button>
                `;
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
            const data = await response.json();

            // APIレスポンスが {posts: [...]} 形式か、 [...] 形式かを判定
            const posts = Array.isArray(data) ? data : data.posts;

            if (!posts) {
                console.error("Could not find posts array in API response", data);
                renderPosts([]); // エラーでも画面をクリアするために空配列を渡す
                return;
            }
            renderPosts(posts);
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    };
    
    const renderPosts = (posts) => {
        chatPosts.innerHTML = '';
        if (!posts || posts.length === 0) return;

        appendPosts(posts, { scroll: 'auto' }); // 初期ロードは即時スクロール
    };

    // 新しい投稿をDOMに追加する関数
    const appendPosts = (posts, options = {}) => {
        if (!posts || posts.length === 0) return;

        const scrollBehavior = options.scroll || 'smooth'; // デフォルトはスムーズスクロール

        posts.forEach(post => {
            const postElement = document.createElement('div');
            postElement.className = 'post';
            postElement.id = `post-${post.post_id}`;
            postElement.innerHTML = `
                <div class="post-header">${post.post_id}: <span class="author">${post.author}</span> <span class="date">${new Date(post.created_at).toLocaleString()}</span></div>
                <div class="post-message">${convertAnchors(escapeHTML(post.message))}</div>
            `;
            chatPosts.appendChild(postElement);
        });

        const lastPost = chatPosts.lastElementChild;
        if (lastPost) {
            if (scrollBehavior === 'auto') {
                lastPost.scrollIntoView();
            } else {
                lastPost.scrollIntoView({ behavior: 'smooth' });
            }
        }
    };

    // 新しい投稿のみを取得する関数
    const fetchNewPosts = async (threadId) => {
        const lastPostElement = chatPosts.lastElementChild;
        const lastPostId = lastPostElement ? parseInt(lastPostElement.id.replace('post-', '')) : 0;

        try {
            const response = await fetch(`${API_BASE_URL}/threads/${threadId}/posts?since=${lastPostId}`);
            if (!response.ok) throw new Error('新しい投稿の取得に失敗しました');
            const newPosts = await response.json();
            appendPosts(newPosts);
        } catch (error) {
            console.error(error);
        }
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
            await fetchNewPosts(threadId); // 自分の投稿も差分取得で反映
            startPolling(threadId); // AIのレスを待つためにポーリング開始
        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    });

    // スレッド削除処理
    const handleDeleteThread = async (threadId) => {
        if (!confirm('本当にこのスレッドを削除しますか？')) {
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/threads/${threadId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('スレッドの削除に失敗しました');
            }

            // 削除成功後、スレッド一覧を再読み込み
            fetchThreads();

        } catch (error) {
            console.error(error);
            alert(error.message);
        }
    };

    // ポーリング処理 (DEV-17)
    const checkAiStatus = async (threadId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/threads/${threadId}/status`);
            if (!response.ok) {
                stopPolling();
                return;
            }
            const status = await response.json();

            if (status.is_generating) {
                aiGeneratingNotice.classList.remove('hidden');
            } else {
                aiGeneratingNotice.classList.add('hidden');
                stopPolling(); // 生成が完了したのでポーリングを停止

                // 投稿数が増えていれば、新しい投稿のみを取得
                const currentPostCount = chatPosts.children.length;
                if (status.post_count > currentPostCount) {
                    fetchNewPosts(threadId);
                }
            }
        } catch (error) {
            console.error('ポーリングエラー:', error);
            stopPolling(); // エラー時もポーリングを停止
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
        e.preventDefault();
        
        const link = e.target.closest('.thread-link');
        const deleteButton = e.target.closest('.delete-thread-button');

        if (link) {
            const threadId = link.dataset.threadId;
            const threadTitle = link.dataset.threadTitle;
            showChatView(threadId, threadTitle);
        } else if (deleteButton) {
            const threadId = deleteButton.dataset.threadId;
            handleDeleteThread(threadId);
        }
    });

    chatPosts.addEventListener('click', (e) => {
        const anchor = e.target.closest('.anchor-link');
        if (anchor) {
            e.preventDefault();
            const postId = anchor.dataset.postId;
            const targetPost = document.getElementById(`post-${postId}`);
            if (targetPost) {
                // スクロールしてハイライト
                targetPost.scrollIntoView({ behavior: 'smooth', block: 'center' });
                targetPost.classList.add('post-highlight');
                setTimeout(() => {
                    targetPost.classList.remove('post-highlight');
                }, 1500); // 1.5秒後にハイライトを消す
            }
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

    const convertAnchors = (text) => {
        return text.replace(/&gt;(\d+)/g, '<a href="#" class="anchor-link" data-post-id="$1">&gt;$1</a>');
    };

    // --- 初期化 ---
    const initialTheme = localStorage.getItem('theme') || 'dark-theme';
    applyTheme(initialTheme);
    showThreadList();
});
