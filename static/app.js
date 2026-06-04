class ChatApp {
    constructor() {
        this.currentConversationId = null;
        this.currentMode = null;
        this.conversations = [];
        this.selectedFile = null;
        this.lastQuestion = null;
        this.authToken = localStorage.getItem('rag_token') || null;
        this.currentUsername = localStorage.getItem('rag_username') || null;


        this.initElements();
        this.bindEvents();
        this.initAuth();
    }

    initElements() {
        this.newChatBtn = document.getElementById('newChatBtn');
        this.searchModes = document.getElementById('searchModes');
        this.conversationsList = document.getElementById('conversationsList');
        this.chatHeader = document.getElementById('chatHeader');
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.chatMessages = document.getElementById('chatMessages');
        this.inputArea = document.getElementById('inputArea');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearHistoryBtn = document.getElementById('clearHistoryBtn');

        this.listDocsBtn = document.getElementById('listDocsBtn');
        this.uploadDocBtn = document.getElementById('uploadDocBtn');
        this.addDocsBtn = document.getElementById('addDocsBtn');
        this.clearDocsBtn = document.getElementById('clearDocsBtn');
        this.countDocsBtn = document.getElementById('countDocsBtn');

        this.listConvsBtn = document.getElementById('listConvsBtn');
        this.updateTitleBtn = document.getElementById('updateTitleBtn');
        this.deleteConvBtn = document.getElementById('deleteConvBtn');

        this.docsModal = document.getElementById('docsModal');
        this.docsModalClose = document.getElementById('docsModalClose');
        this.docsModalBody = document.getElementById('docsModalBody');

        this.uploadDocModal = document.getElementById('uploadDocModal');
        this.uploadDocModalClose = document.getElementById('uploadDocModalClose');
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.uploadProgress = document.getElementById('uploadProgress');
        this.uploadFileBtn = document.getElementById('uploadFileBtn');

        this.addDocsModal = document.getElementById('addDocsModal');
        this.addDocsModalClose = document.getElementById('addDocsModalClose');
        this.docQuestion = document.getElementById('docQuestion');
        this.docAnswer = document.getElementById('docAnswer');
        this.submitDocBtn = document.getElementById('submitDocBtn');

        this.updateTitleModal = document.getElementById('updateTitleModal');
        this.updateTitleModalClose = document.getElementById('updateTitleModalClose');
        this.newTitle = document.getElementById('newTitle');
        this.submitTitleBtn = document.getElementById('submitTitleBtn');
    }

    bindEvents() {
        this.newChatBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.searchModes.style.display = this.searchModes.style.display === 'block' ? 'none' : 'block';
            this.newChatBtn.classList.toggle('active');
        });

        this.searchModes.querySelectorAll('.mode-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const mode = e.currentTarget.dataset.mode;
                this.createNewConversation(mode);
            });
        });

        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        document.querySelectorAll('.quick-question').forEach(item => {
            item.addEventListener('click', () => {
                const question = item.textContent;
                this.createNewConversation('summary-post');
                this.messageInput.value = question;
                this.sendMessage();
            });
        });

        this.clearHistoryBtn.addEventListener('click', () => {
            if (confirm('纭畾瑕佹竻绌烘墍鏈夊巻鍙插璇濆悧锛?)) {
                this.clearAllConversations();
            }
        });

        document.addEventListener('click', (e) => {
            if (!this.newChatBtn.contains(e.target) && !this.searchModes.contains(e.target)) {
                this.searchModes.style.display = 'none';
                this.newChatBtn.classList.remove('active');
            }
        });

        this.listDocsBtn.addEventListener('click', () => this.listDocuments());
        this.uploadDocBtn.addEventListener('click', () => {
            this.selectedFile = null;
        this.lastQuestion = null;
        this.authToken = localStorage.getItem('rag_token') || null;
        this.currentUsername = localStorage.getItem('rag_username') || null;
        this.initAuth();
            this.uploadProgress.style.display = 'none';
            this.uploadFileBtn.style.display = 'none';
            this.uploadArea.style.display = 'flex';
            this.uploadDocModal.classList.add('show');
        });
        this.addDocsBtn.addEventListener('click', () => {
            this.docQuestion.value = '';
            this.docAnswer.value = '';
            this.addDocsModal.classList.add('show');
        });
        this.clearDocsBtn.addEventListener('click', () => {
            if (confirm('纭畾瑕佹竻绌烘墍鏈夋枃妗ｅ悧锛熸鎿嶄綔涓嶅彲鎭㈠锛?)) {
                this.clearDocuments();
            }
        });
        this.countDocsBtn.addEventListener('click', () => this.getDocumentCount());

        this.listConvsBtn.addEventListener('click', () => {
            this.loadConversations();
            alert('浼氳瘽鍒楄〃宸插埛鏂?);
        });
        this.updateTitleBtn.addEventListener('click', () => {
            if (!this.currentConversationId) {
                alert('璇峰厛閫夋嫨涓€涓細璇?);
                return;
            }
            this.newTitle.value = '';
            this.updateTitleModal.classList.add('show');
        });
        this.deleteConvBtn.addEventListener('click', () => {
            if (!this.currentConversationId) return;
            if (confirm('纭畾瑕佸垹闄ゅ綋鍓嶄細璇濆悧锛?)) {
                this.deleteConversation(this.currentConversationId);
            }
        });

        this.docsModalClose.addEventListener('click', () => this.docsModal.classList.remove('show'));
        this.uploadDocModalClose.addEventListener('click', () => this.uploadDocModal.classList.remove('show'));
        this.addDocsModalClose.addEventListener('click', () => this.addDocsModal.classList.remove('show'));
        this.updateTitleModalClose.addEventListener('click', () => this.updateTitleModal.classList.remove('show'));
        this.submitDocBtn.addEventListener('click', () => this.addDocument());
        this.submitTitleBtn.addEventListener('click', () => this.updateConversationTitle());
        this.uploadFileBtn.addEventListener('click', () => this.uploadFile());

        // 鏂囦欢涓婁紶浜嬩欢
        this.uploadArea.addEventListener('click', () => {
            this.fileInput.click();
        });
        this.fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.selectedFile = file;
                this.uploadArea.innerHTML = `<p style="color:#10b981;">宸查€夋嫨鏂囦欢: ${file.name}</p>`;
                this.uploadFileBtn.style.display = 'block';
            }
        });

        // 鎷栨嫿涓婁紶
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('drag-over');
        });
        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('drag-over');
        });
        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) {
                this.selectedFile = file;
                this.uploadArea.innerHTML = `<p style="color:#10b981;">宸查€夋嫨鏂囦欢: ${file.name}</p>`;
                this.uploadFileBtn.style.display = 'block';
            }
        });
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/v1/conversations', { headers: this.getAuthHeaders() });
            const data = await response.json();
            this.conversations = data.conversations || [];
            this.renderConversations();
        } catch (error) {
            console.error('鍔犺浇浼氳瘽澶辫触:', error);
        }
    }

    renderConversations() {
        if (!this.conversationsList) return;
        this.conversationsList.innerHTML = '';

        if (this.conversations.length === 0) {
            const emptyMsg = document.createElement('div');
            emptyMsg.className = 'empty-conversations';
            emptyMsg.textContent = '鏆傛棤鍘嗗彶瀵硅瘽';
            emptyMsg.style.padding = '20px';
            emptyMsg.style.textAlign = 'center';
            emptyMsg.style.color = '#999';
            emptyMsg.style.fontSize = '14px';
            this.conversationsList.appendChild(emptyMsg);
            return;
        }

        this.conversations.forEach(conv => {
            const item = document.createElement('div');
            item.className = `conversation-item ${this.currentConversationId === conv.conversation_id ? 'active' : ''}`;
            item.dataset.id = conv.conversation_id;

            const titleDiv = document.createElement('div');
            titleDiv.className = 'conversation-title';
            titleDiv.textContent = conv.title || '鏂颁細璇?;

            const idDiv = document.createElement('div');
            idDiv.className = 'conversation-id';
            idDiv.textContent = conv.conversation_id.slice(0, 8) + '...';

            item.appendChild(titleDiv);
            item.appendChild(idDiv);

            item.addEventListener('click', () => {
                this.loadConversation(conv.conversation_id);
            });

            this.conversationsList.appendChild(item);
        });
    }

    createNewConversation(mode) {
        this.currentMode = mode;
        this.currentConversationId = null;
        this.searchModes.style.display = 'none';
        this.newChatBtn.classList.remove('active');

        this.welcomeScreen.style.display = 'none';
        this.chatMessages.style.display = 'block';
        this.inputArea.style.display = 'flex';
        this.deleteConvBtn.style.display = 'none';
        this.chatMessages.innerHTML = '';

        const modeNames = {
            'agent': '鏅鸿兘闂瓟',
            'summary-post': '蹇€熸煡璇?
        };
        this.chatHeader.querySelector('h2').textContent = modeNames[mode] || '鏅鸿兘瀹㈡湇';

        setTimeout(() => this.messageInput.focus(), 100);
    }

    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/v1/conversations/${conversationId}`, { headers: this.getAuthHeaders() });
            const data = await response.json();

            this.currentConversationId = conversationId;
            this.welcomeScreen.style.display = 'none';
            this.chatMessages.style.display = 'block';
            this.inputArea.style.display = 'flex';
            this.deleteConvBtn.style.display = 'flex';

            this.chatHeader.querySelector('h2').textContent = data.title || '鏅鸿兘瀹㈡湇';

            this.chatMessages.innerHTML = '';
            data.messages.forEach(msg => {
                this.renderMessage(msg.role, msg.content, msg.sources);
            });

            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
                if (item.dataset.id === conversationId) {
                    item.classList.add('active');
                }
            });

            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        } catch (error) {
            console.error('鍔犺浇浼氳瘽澶辫触:', error);
        }
    }

    async sendMessage() {
        const question = this.messageInput.value.trim();
        if (!question) return;

        this.sendBtn.disabled = true;
        this.messageInput.disabled = true;

        this.renderMessage('user', question);
        this.messageInput.value = '';

        // 娣诲姞"妯″瀷鎬濊€冧腑"鍔犺浇鎻愮ず
        const loadingMessage = this.renderLoadingMessage();
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        try {
            let response;
            let data;

            if (this.currentMode === 'summary-post') {
                // 璺緞浜岋細杞婚噺绾?- 鎼滅储骞剁敓鎴愭€荤粨
                const endpoint = '/rag/search/summary';
                response = await fetch(endpoint, {
                    method: 'POST',
                    headers: this.getAuthHeaders(),
                    body: JSON.stringify({ question, enable_rewrite: true })
                });

                data = await response.json();

                let reply = '';
                let sources = [];
                if (data.summary) {
                    reply = data.summary;
                    sources = data.sources || [];
                } else if (data.results && data.results.length > 0) {
                    reply = data.results.map(r => `${r.question}\n${r.answer}`).join('\n\n');
                    sources = data.results.map(r => r.source).filter(Boolean);
                } else {
                    reply = '鏈壘鍒扮浉鍏崇瓟妗?;
                }

                this.renderMessage('assistant', reply, sources, null, null, null, null, loadingMessage);

                if (!this.currentConversationId) {
                    const chatResponse = await fetch('/api/v1/chat', {
                        method: 'POST',
                        headers: this.getAuthHeaders(),
                        body: JSON.stringify({
                            question: question,
                            conversation_id: null,
                            sources: sources.length > 0 ? sources : null,
                            reply: reply
                        })
                    });
                    const chatData = await chatResponse.json();
                    this.currentConversationId = chatData.conversation_id;
                    this.deleteConvBtn.style.display = 'flex';
                } else {
                    await fetch('/api/v1/chat', {
                        method: 'POST',
                        headers: this.getAuthHeaders(),
                        body: JSON.stringify({
                            question: question,
                            conversation_id: this.currentConversationId,
                            sources: sources.length > 0 ? sources : null,
                            reply: reply
                        })
                    });
                }

            } else {
                // 璺緞涓€锛氬畬鏁存祦绋?- Agent (SSE streaming)
                this.lastQuestion = question;
                const response = await fetch('/api/v1/chat/stream', {
                    method: 'POST',
                    headers: this.getAuthHeaders(),
                    body: JSON.stringify({
                        question,
                        conversation_id: this.currentConversationId
                    })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                let streamMsgDiv = null;
                let streamContentDiv = null;
                let sourcesData = null;
                let rewrittenQuestion = null;
                let finalPrompt = null;

                // Remove loading message, create streaming bubble
                if (loadingMessage && loadingMessage.parentNode) {
                    loadingMessage.parentNode.removeChild(loadingMessage);
                }
                const result = this.createStreamingBubble();
                streamMsgDiv = result.div;
                streamContentDiv = result.contentDiv;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    const lines = buffer.split('\n');
                    buffer = '';
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();
                        if (!line) continue;
                        if (line.startsWith('event: ')) {
                            const eventType = line.slice(7).trim();
                            const dataLine = (lines[i + 1] || '').trim();
                            if (dataLine.startsWith('data: ')) {
                                const dataJson = dataLine.slice(6);
                                try {
                                    const data = JSON.parse(dataJson);
                                    this.handleSSEEvent(eventType, data, streamContentDiv, streamMsgDiv);
                                    if (eventType === 'sources') sourcesData = data.sources || [];
                                    if (eventType === 'done') {
                                        if (data.conversation_id) {
                                            this.currentConversationId = data.conversation_id;
                                            this.deleteConvBtn.style.display = 'flex';
                                            if (data.title) {
                                                this.chatHeader.querySelector('h2').textContent = data.title;
                                            }
                                        }
                                        sourcesData = data.sources || sourcesData;
                                        rewrittenQuestion = data.rewritten_question || rewrittenQuestion;
                                        finalPrompt = data.final_prompt || finalPrompt;
                                        if (data.message_id) {
                                            streamMsgDiv.dataset.messageId = data.message_id;
                                        }
                                    }
                                } catch (e) { /* partial */ }
                            }
                            i++;
                        }
                    }
                }
                this.finalizeStreamingBubble(streamMsgDiv, streamContentDiv, sourcesData, rewrittenQuestion, finalPrompt);
            }

            await this.loadConversations();

        } catch (error) {
            this.renderMessage('assistant', `璇锋眰澶辫触: ${error.message}`, null, null, null, null, null, loadingMessage);
        } finally {
            this.sendBtn.disabled = false;
            this.messageInput.disabled = false;
            this.messageInput.focus();
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    renderLoadingMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant loading';
        messageDiv.id = 'loading-message';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<span class="loading-spinner"></span>妯″瀷鎬濊€冧腑...';

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        return messageDiv;
    }

    renderMessage(role, content, sources = null, thinking = null, action = null, rewrittenQuestion = null, finalPrompt = null, loadingMessage = null) {
        // 濡傛灉鏈夊姞杞芥秷鎭紝鍏堢Щ闄ゅ畠
        if (loadingMessage && loadingMessage.parentNode) {
            loadingMessage.parentNode.removeChild(loadingMessage);
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        if (thinking) {
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'message-thinking';
            thinkingDiv.textContent = `鎬濊€? ${thinking}`;
            contentDiv.appendChild(thinkingDiv);
        }

        if (action) {
            const actionDiv = document.createElement('div');
            actionDiv.className = 'message-action';
            actionDiv.textContent = `鍔ㄤ綔: ${action}`;
            contentDiv.appendChild(actionDiv);
        }

        if (rewrittenQuestion) {
            const rewriteDiv = document.createElement('div');
            rewriteDiv.className = 'message-rewrite';
            rewriteDiv.innerHTML = `<strong>馃攧 閲嶅啓鍚庣殑闂锛?/strong><br><pre style="margin: 5px 0 0 0; white-space: pre-wrap; word-break: break-all;">${this.escapeHtml(rewrittenQuestion)}</pre>`;
            contentDiv.appendChild(rewriteDiv);
        }

        if (finalPrompt) {
            const promptDiv = document.createElement('div');
            promptDiv.className = 'message-prompt';
            promptDiv.innerHTML = `<strong>馃摑 LLM Prompt 涓婁笅鏂囷細</strong><br><pre style="margin: 5px 0 0 0; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto;">${this.escapeHtml(finalPrompt)}</pre>`;
            contentDiv.appendChild(promptDiv);
        }

        // 娣诲姞鏉ユ簮淇℃伅
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            
            // 妫€鏌ユ枃妗ｇ姸鎬侊紝status 涓?'deleted' 琛ㄧず鏂囨。宸茶鍒犻櫎
            const processedFiles = new Set();
            const displaySources = [];
            
            for (const s of sources) {
                if (processedFiles.has(s.file)) continue;
                processedFiles.add(s.file);
                displaySources.push(s);
            }
            
            if (displaySources.length > 0) {
                const sourcesHtml = displaySources.map(s => {
                    const displayName = this.truncateFilename(s.file, 15);
                    const titleAttr = `title="${this.escapeHtml(s.file)}"`;
                    if (s.status === 'deleted') {
                        return `<span class="source-tag deleted" ${titleAttr}>${displayName} (宸插垹闄?</span>`;
                    }
                    return `<span class="source-tag" ${titleAttr}>${displayName}</span>`;
                }).join('');
                
                sourcesDiv.innerHTML = '<strong>寮曠敤鏉ユ簮锛?/strong>' + sourcesHtml;
                contentDiv.appendChild(sourcesDiv);
            }
        }

        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
    }

    async listDocuments() {
        try {
            // 娣诲姞鏃堕棿鎴崇鐢ㄧ紦瀛?
            const response = await fetch('/rag/documents?' + Date.now());
            const data = await response.json();
            console.log('Received documents:', data);

            this.docsModalBody.innerHTML = '';

            if (!data.documents || data.documents.length === 0) {
                this.docsModalBody.innerHTML = '<p style="text-align:center;color:#999;">鏆傛棤鏂囨。</p>';
                this.docsModal.classList.add('show');
                return;
            }

            data.documents.forEach((doc, index) => {
                const docItem = document.createElement('div');
                docItem.className = 'doc-item';

                const titleDiv = document.createElement('div');
                titleDiv.className = 'doc-title';
                const originalName = doc.filename || doc.file || doc.question || '鏃犳爣棰?;
                console.log('Document:', index, 'filename:', doc.filename, 'originalName:', originalName);
                const displayName = this.truncateFilename(originalName, 25);
                titleDiv.textContent = `${index + 1}. ${displayName}`;
                titleDiv.title = originalName;

                const typeDiv = document.createElement('div');
                typeDiv.className = 'doc-type';
                if (doc.type === 'faq') {
                    typeDiv.textContent = '绫诲瀷: 闂瓟';
                } else {
                    const fileType = doc.file_type ? doc.file_type.toUpperCase() : 'DOC';
                    const fileSize = this.formatFileSize(doc.file_size);
                    typeDiv.textContent = `绫诲瀷: ${fileType} | 澶у皬: ${fileSize}`;
                }

                docItem.appendChild(titleDiv);
                docItem.appendChild(typeDiv);

                // 娣诲姞鍒犻櫎鎸夐挳锛團AQ 闆嗗悎涓嶅厑璁稿垹闄わ級
                if (doc.doc_id !== 'faq_collection') {
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'doc-delete-btn';
                    deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
                    deleteBtn.title = '鍒犻櫎姝ゆ枃妗?;
                    deleteBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const docName = doc.filename || doc.file || '姝ゆ枃妗?;
                        if (confirm(`纭畾瑕佸垹闄ゆ枃妗?${docName}" 鍚楋紵`)) {
                            this.deleteDocument(doc.doc_id);
                        }
                    });
                    docItem.appendChild(deleteBtn);
                }

                this.docsModalBody.appendChild(docItem);
            });

            this.docsModal.classList.add('show');
        } catch (error) {
            alert(`鑾峰彇鏂囨。鍒楄〃澶辫触: ${error.message}`);
        }
    }

    async deleteDocument(docId) {
        const confirmMsg = '纭畾瑕佸垹闄よ繖涓枃妗ｅ悧锛焅n娉ㄦ剰锛氬垹闄ゅ悗灏嗘棤娉曟仮澶嶏紝涓旂浉鍏冲悜閲忔暟鎹細浠庣煡璇嗗簱涓Щ闄ゃ€?;
        if (!confirm(confirmMsg)) {
            return;
        }

        const deleteBtn = event.target.closest('.doc-item')?.querySelector('.delete-btn');
        const originalText = deleteBtn ? deleteBtn.innerHTML : '';

        if (deleteBtn) {
            deleteBtn.disabled = true;
            deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 鍒犻櫎涓?..';
            deleteBtn.classList.add('doc-deleting');
        }

        try {
            const response = await fetch(`/rag/documents/${docId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.docsModal.classList.remove('show');
                setTimeout(() => {
                    this.listDocuments();
                }, 300);
            } else {
                alert(`鍒犻櫎澶辫触: ${data.message}`);
                if (deleteBtn) {
                    deleteBtn.disabled = false;
                    deleteBtn.innerHTML = originalText;
                    deleteBtn.classList.remove('doc-deleting');
                }
            }
        } catch (error) {
            alert(`鍒犻櫎鏂囨。澶辫触: ${error.message}`);
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = originalText;
                deleteBtn.classList.remove('doc-deleting');
            }
        }
    }

    async uploadFile() {
        if (!this.selectedFile) {
            alert('璇峰厛閫夋嫨鏂囦欢');
            return;
        }

        this.uploadArea.style.display = 'none';
        this.uploadFileBtn.style.display = 'none';
        this.uploadProgress.style.display = 'block';

        try {
            const formData = new FormData();
            formData.append('file', this.selectedFile);

            const response = await fetch('/rag/documents/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                alert(`涓婁紶鎴愬姛锛乗n鏂囦欢鍚? ${data.filename}\n鍒嗗潡鏁? ${data.chunks_count}`);
                this.uploadDocModal.classList.remove('show');
            } else {
                alert(`涓婁紶澶辫触: ${data.message}`);
            }
        } catch (error) {
            alert(`涓婁紶澶辫触: ${error.message}`);
        } finally {
            this.uploadProgress.style.display = 'none';
            this.uploadArea.style.display = 'flex';
            this.uploadArea.innerHTML = `
                <i class="fas fa-cloud-upload-alt"></i>
                <p>鐐瑰嚮鎴栨嫋鎷芥枃浠跺埌姝ゅ涓婁紶</p>
                <p class="upload-hint">鏀寔 PDF銆乀XT銆丏OCX銆丮D 绛夋牸寮?/p>
                <p class="upload-hint">鏈€澶ф枃浠跺ぇ灏忥細50MB</p>
            `;
            this.selectedFile = null;
        this.lastQuestion = null;
        this.authToken = localStorage.getItem('rag_token') || null;
        this.currentUsername = localStorage.getItem('rag_username') || null;
        this.initAuth();
        }
    }

    async addDocument() {
        const question = this.docQuestion.value.trim();
        const answer = this.docAnswer.value.trim();

        if (!question || !answer) {
            alert('璇峰～鍐欓棶棰樺拰绛旀');
            return;
        }

        try {
            const response = await fetch('/rag/documents', {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({ documents: [{ question, answer }] })
            });

            const data = await response.json();

            if (data.success) {
                alert('鏂囨。娣诲姞鎴愬姛锛?);
                this.addDocsModal.classList.remove('show');
                this.docQuestion.value = '';
                this.docAnswer.value = '';
            } else {
                alert(`娣诲姞澶辫触: ${data.message}`);
            }
        } catch (error) {
            alert(`娣诲姞鏂囨。澶辫触: ${error.message}`);
        }
    }

    async clearDocuments() {
        try {
            const response = await fetch('/rag/documents', {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                alert('鎵€鏈夋枃妗ｅ凡娓呯┖锛?);
            } else {
                alert(`娓呯┖澶辫触: ${data.message}`);
            }
        } catch (error) {
            alert(`娓呯┖鏂囨。澶辫触: ${error.message}`);
        }
    }

    async getDocumentCount() {
        try {
            const response = await fetch('/rag/documents/count');
            const data = await response.json();

            alert(`鍚戦噺搴撲腑鍏辨湁 ${data.count} 涓枃妗);
        } catch (error) {
            alert(`鑾峰彇鏂囨。鏁伴噺澶辫触: ${error.message}`);
        }
    }

    async deleteConversation(conversationId) {
        try {
            const response = await fetch(`/api/v1/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.currentConversationId = null;
                this.deleteConvBtn.style.display = 'none';
                this.welcomeScreen.style.display = 'flex';
                this.chatMessages.style.display = 'none';
                this.inputArea.style.display = 'none';
                await this.loadConversations();
                alert('浼氳瘽宸插垹闄わ紒');
            } else {
                alert(`鍒犻櫎澶辫触: ${data.message}`);
            }
        } catch (error) {
            alert(`鍒犻櫎浼氳瘽澶辫触: ${error.message}`);
        }
    }

    async updateConversationTitle() {
        const title = this.newTitle.value.trim();

        if (!title) {
            alert('璇疯緭鍏ユ柊鏍囬');
            return;
        }

        if (!this.currentConversationId) {
            alert('璇峰厛閫夋嫨涓€涓細璇?);
            return;
        }

        try {
            const response = await fetch(`/api/v1/conversations/${this.currentConversationId}/title?title=${encodeURIComponent(title)}`, {
                method: 'PUT'
            });

            const data = await response.json();

            if (data.success) {
                this.updateTitleModal.classList.remove('show');
                this.newTitle.value = '';
                this.chatHeader.querySelector('h2').textContent = title;
                await this.loadConversations();
                alert('鏍囬鏇存柊鎴愬姛锛?);
            } else {
                alert(`鏇存柊澶辫触: ${data.message}`);
            }
        } catch (error) {
            alert(`鏇存柊鏍囬澶辫触: ${error.message}`);
        }
    }

    async clearAllConversations() {
        try {
            for (const conv of this.conversations) {
                await fetch(`/api/v1/conversations/${conv.conversation_id}`, {
                    method: 'DELETE'
                });
            }

            this.conversations = [];
            this.currentConversationId = null;
            this.deleteConvBtn.style.display = 'none';
            this.conversationsList.innerHTML = '';
            this.welcomeScreen.style.display = 'flex';
            this.chatMessages.style.display = 'none';
            this.inputArea.style.display = 'none';

        } catch (error) {
            console.error('娓呯┖浼氳瘽澶辫触:', error);
        }
    }

    truncateFilename(filename, maxLength = 20) {
        if (!filename) return '';
        if (filename.length <= maxLength) return filename;
        const ext = filename.lastIndexOf('.') !== -1 ? filename.slice(filename.lastIndexOf('.')) : '';
        const nameWithoutExt = ext ? filename.slice(0, filename.lastIndexOf('.')) : filename;
        const truncatedName = nameWithoutExt.slice(0, maxLength - ext.length - 3);
        return truncatedName + '...' + ext;
    }

    formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    createStreamingBubble() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant streaming';
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = '<span class="streaming-cursor">|</span>';
        messageDiv.appendChild(contentDiv);
        this.chatMessages.appendChild(messageDiv);
        return { div: messageDiv, contentDiv: contentDiv };
    }

    handleSSEEvent(eventType, data, contentDiv, messageDiv) {
        if (eventType === 'thinking') {
            const text = data.text || '';
            if (contentDiv.querySelector('.stream-thinking')) {
                contentDiv.querySelector('.stream-thinking').textContent = text;
            } else {
                const thinkEl = document.createElement('div');
                thinkEl.className = 'stream-thinking';
                thinkEl.textContent = text;
                contentDiv.insertBefore(thinkEl, contentDiv.lastChild);
            }
        } else if (eventType === 'token') {
            const thinkEl = contentDiv.querySelector('.stream-thinking');
            if (thinkEl) thinkEl.parentNode.removeChild(thinkEl);
            const cursor = contentDiv.querySelector('.streaming-cursor');
            if (cursor) {
                cursor.insertAdjacentText('beforebegin', data.text);
            } else {
                contentDiv.appendChild(document.createTextNode(data.text));
            }
        }
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    finalizeStreamingBubble(messageDiv, contentDiv, sourcesData, rewrittenQuestion = null, finalPrompt = null) {
        const cursor = contentDiv.querySelector('.streaming-cursor');
        if (cursor) cursor.parentNode.removeChild(cursor);
        messageDiv.classList.remove('streaming');

        const rawText = contentDiv.textContent.trim();
        contentDiv.textContent = '';

        if (sourcesData && sourcesData.length > 0) {
            const citedHtml = this.renderCitations(rawText, sourcesData);
            contentDiv.innerHTML = citedHtml;
            contentDiv.querySelectorAll('.citation').forEach(badge => {
                badge.addEventListener('click', (e) => {
                    const idx = parseInt(badge.dataset.index);
                    const source = sourcesData[idx - 1];
                    if (source) {
                        alert('Source: ' + source.file + (source.page ? ', Page ' + source.page : ''));
                    }
                });
            });
        } else {
            contentDiv.textContent = rawText;
        }

        // 娣诲姞閲嶅啓鍚庣殑闂鍜孡LM Prompt涓婁笅鏂?
        if (rewrittenQuestion) {
            const rewriteDiv = document.createElement('div');
            rewriteDiv.className = 'message-rewrite';
            rewriteDiv.innerHTML = `<strong>馃攧 閲嶅啓鍚庣殑闂锛?/strong><br><pre style="margin: 5px 0 0 0; white-space: pre-wrap; word-break: break-all;">${this.escapeHtml(rewrittenQuestion)}</pre>`;
            contentDiv.appendChild(rewriteDiv);
        }

        if (finalPrompt) {
            const promptDiv = document.createElement('div');
            promptDiv.className = 'message-prompt';
            promptDiv.innerHTML = `<strong>馃摑 LLM Prompt 涓婁笅鏂囷細</strong><br><pre style="margin: 5px 0 0 0; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto;">${this.escapeHtml(finalPrompt)}</pre>`;
            contentDiv.appendChild(promptDiv);
        }

        this.addMessageActions(messageDiv, contentDiv);

        if (sourcesData && sourcesData.length > 0) {
            this.renderSourcesPanel(contentDiv, sourcesData);
        }

        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    renderCitations(text, sources) {
        return text.replace(/\[(\d+)\]/g, (match, num) => {
            const idx = parseInt(num) - 1;
            if (idx >= 0 && idx < sources.length) {
                const s = sources[idx];
                const title = s.file + (s.page ? ', Page ' + s.page : '');
                return '<span class="citation" data-index="' + num + '" title="' + this.escapeHtml(title) + '">[' + num + ']</span>';
            }
            return match;
        });
    }

    renderSourcesPanel(contentDiv, sourcesData) {
        const panel = document.createElement('div');
        panel.className = 'sources-panel';

        const header = document.createElement('div');
        header.className = 'sources-header';
        header.textContent = 'Sources (' + sourcesData.length + ')';
        header.addEventListener('click', () => {
            const body = panel.querySelector('.sources-body');
            if (body) body.style.display = body.style.display === 'none' ? 'block' : 'none';
            panel.classList.toggle('collapsed');
        });
        panel.appendChild(header);

        const body = document.createElement('div');
        body.className = 'sources-body';
        sourcesData.forEach((s, i) => {
            const item = document.createElement('div');
            item.className = 'source-item';
            item.innerHTML = '<span class="source-index">[' + s.index + ']</span> ' +
                '<span class="source-file">' + this.escapeHtml(s.file) + '</span>' +
                (s.page ? ' <span class="source-page">p.' + s.page + '</span>' : '');
            body.appendChild(item);
        });
        panel.appendChild(body);
        contentDiv.appendChild(panel);
    }

    addMessageActions(messageDiv, contentDiv) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'msg-action-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy';
        copyBtn.addEventListener('click', () => {
            const text = contentDiv.textContent;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => { copyBtn.innerHTML = '<i class="fas fa-copy"></i>'; }, 1500);
            });
        });
        actionsDiv.appendChild(copyBtn);

        // Check if this is the last assistant message
        const allMsgs = Array.from(messageDiv.parentNode.querySelectorAll('.message.assistant:not(.streaming)'));
        if (allMsgs.length > 0 && messageDiv === allMsgs[allMsgs.length - 1]) {
            const regenBtn = document.createElement('button');
            regenBtn.className = 'msg-action-btn';
            regenBtn.innerHTML = '<i class="fas fa-redo"></i>';
            regenBtn.title = 'Regenerate';
            regenBtn.addEventListener('click', () => this.regenerateAnswer(messageDiv));
            actionsDiv.appendChild(regenBtn);
        }

        const convId = this.currentConversationId;
        const msgId = messageDiv.dataset.messageId;
        if (convId && msgId) {
            const likeBtn = document.createElement('button');
            likeBtn.className = 'msg-action-btn feedback-btn';
            likeBtn.innerHTML = '<i class="far fa-thumbs-up"></i>';
            likeBtn.title = 'Like';
            likeBtn.addEventListener('click', () => this.sendFeedback(convId, msgId, 'like', likeBtn, actionsDiv));
            actionsDiv.appendChild(likeBtn);

            const dislikeBtn = document.createElement('button');
            dislikeBtn.className = 'msg-action-btn feedback-btn';
            dislikeBtn.innerHTML = '<i class="far fa-thumbs-down"></i>';
            dislikeBtn.title = 'Dislike';
            dislikeBtn.addEventListener('click', () => this.sendFeedback(convId, msgId, 'dislike', dislikeBtn, actionsDiv));
            actionsDiv.appendChild(dislikeBtn);
        }

        contentDiv.appendChild(actionsDiv);
    }

    async sendFeedback(conversationId, messageId, rating, clickedBtn, actionsDiv) {
        try {
            await fetch('/api/v1/messages/' + conversationId + '/feedback?message_id=' + messageId + '&rating=' + rating, {
                method: 'POST'
            });
            actionsDiv.querySelectorAll('.feedback-btn').forEach(b => {
                b.classList.remove('active');
                if (b === clickedBtn) {
                    b.classList.add('active');
                    b.style.color = rating === 'like' ? '#10b981' : '#ef4444';
                }
            });
        } catch (e) {
            console.error('Feedback failed:', e);
        }
    }

    regenerateAnswer(messageDiv) {
        if (!this.lastQuestion) return;
        if (messageDiv && messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
        this.messageInput.value = this.lastQuestion;
        setTimeout(() => this.sendMessage(), 50);
    }

    initAuth() {
        const loginOverlay = document.getElementById('loginOverlay');
        const loginSubmit = document.getElementById('loginSubmitBtn');
        const registerSubmit = document.getElementById('registerSubmitBtn');
        const skipLogin = document.getElementById('skipLoginBtn');
        const logoutBtn = document.getElementById('logoutBtn');
        if (!loginOverlay) return; const tabs = loginOverlay.querySelectorAll('.login-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const isLogin = tab.dataset.tab === 'login';
                document.getElementById('loginForm').style.display = isLogin ? 'block' : 'none';
                document.getElementById('registerForm').style.display = isLogin ? 'none' : 'block';
            });
        });
        loginSubmit.addEventListener('click', () => this.handleLogin());
        registerSubmit.addEventListener('click', () => this.handleRegister());
        skipLogin.addEventListener('click', () => this.skipLogin());
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.handleLogout());
        if (this.authToken) { this.onLoginSuccess(this.authToken, this.currentUsername || 'User'); }
    }

    async handleLogin() {
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value.trim();
        if (!username || !password) return;
        try {
            const r = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await r.json();
            if (r.ok) { this.onLoginSuccess(data.access_token, data.username); }
            else { document.getElementById('loginError').textContent = data.detail || 'Login failed'; }
        } catch (e) { document.getElementById('loginError').textContent = 'Network error: ' + e.message; }
    }

    async handleRegister() {
        const username = document.getElementById('registerUsername').value.trim();
        const password = document.getElementById('registerPassword').value.trim();
        if (!username || !password) return;
        try {
            const r = await fetch('/api/v1/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
            const data = await r.json();
            if (r.ok) { this.onLoginSuccess(data.access_token, data.username); }
            else { document.getElementById('registerError').textContent = data.detail || 'Registration failed'; }
        } catch (e) { document.getElementById('registerError').textContent = 'Network error: ' + e.message; }
    }

    skipLogin() { this.onLoginSuccess(null, 'anonymous'); }

    onLoginSuccess(token, username) {
        if (token) { this.authToken = token; localStorage.setItem('rag_token', token); }
        this.currentUsername = username;
        localStorage.setItem('rag_username', username);
        const overlay = document.getElementById('loginOverlay'); if (overlay) overlay.style.display = 'none';
        const userLabel = document.getElementById('currentUserLabel');
        if (userLabel) { userLabel.textContent = username; userLabel.style.display = 'inline'; }
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) logoutBtn.style.display = 'flex';
        this.loadConversations();
        if (this.welcomeScreen) this.welcomeScreen.style.display = 'flex';
    }

    handleLogout() {
        localStorage.removeItem('rag_token');
        localStorage.removeItem('rag_username');
        this.authToken = null;
        this.currentUsername = null;
        this.currentConversationId = null;
        document.getElementById('loginOverlay').style.display = 'flex';
        document.getElementById('currentUserLabel').style.display = 'none';
        document.getElementById('logoutBtn').style.display = 'none';
        this.welcomeScreen.style.display = 'flex';
        this.chatMessages.style.display = 'none';
        this.inputArea.style.display = 'none';
        this.chatMessages.innerHTML = '';
    }

    getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.authToken) {
            headers['Authorization'] = 'Bearer ' + this.authToken;
        }
        return headers;
    }

    getUserToken() { return this.authToken ? 'Bearer ' + this.authToken : null; }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChatApp();
});
