/**
 * Premium Floating Button - Robust Draggable Logic
 * Uses 'Top/Left' positioning for absolute stability.
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('floatingChatBtn');
    if (!container) return;

    // Configuration
    const STORAGE_KEY = 'floatingBtnConfig';
    const DRAG_THRESHOLD = 5; // pixels needed to consider it a drag
    
    // State
    let isDragging = false;
    let startX, startY;     // Mouse/Touch start position
    let initialLeft, initialTop; // Element start position
    let hasMoved = false;   // Flag to differentiate click vs drag

    // Initialize Position
    initPosition();

    function initPosition() {
        const savedConfig = localStorage.getItem(STORAGE_KEY);
        if (savedConfig) {
            try {
                const config = JSON.parse(savedConfig);
                applyPosition(config.left, config.top);
                validateBounds(); // Ensure it's visible
            } catch (e) {
                console.error("Error parsing saved position", e);
                resetPosition();
            }
        } else {
            // First run: let CSS handle bottom-left default, 
            // but we calculate exact pixels to switch to absolute positioning
            // after first interaction or on next load.
        }
    }

    /**
     * Applies exact Left/Top style.
     * Uses 'px' to be explicit.
     */
    function applyPosition(left, top) {
        // Switch to fixed positioning with explicit coordinates
        container.style.position = 'fixed';
        container.style.left = left + 'px';
        container.style.top = top + 'px';
        
        // Remove 'bottom/right' defaults to avoid conflict
        container.style.bottom = 'auto';
        container.style.right = 'auto';
    }

    /**
     * Resets to default bottom-left
     */
    function resetPosition() {
        container.style.left = '30px';
        container.style.bottom = '30px';
        container.style.top = 'auto';
        localStorage.removeItem(STORAGE_KEY);
    }

    /**
     * Ensures button is strictly inside viewport
     */
    function validateBounds() {
        const rect = container.getBoundingClientRect();
        const winW = window.innerWidth;
        const winH = window.innerHeight;

        let newLeft = rect.left;
        let newTop = rect.top;
        let needsFix = false;

        // X Bounds
        if (newLeft < 0) { newLeft = 0; needsFix = true; }
        if (newLeft + rect.width > winW) { newLeft = winW - rect.width; needsFix = true; }

        // Y Bounds
        if (newTop < 0) { newTop = 0; needsFix = true; }
        if (newTop + rect.height > winH) { newTop = winH - rect.height; needsFix = true; }

        if (needsFix) {
            applyPosition(newLeft, newTop);
            savePosition(newLeft, newTop);
        }
    }

    function savePosition(left, top) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ left, top }));
    }

    // --- Interaction Handlers ---

    function onDragStart(e) {
        // Only allow drag from the button itself, not from menu/chat content
        if (!e.target.closest('.floating-chat-btn')) return;
        
        // 1. Normalize Event
        const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;

        // 2. Setup State
        isDragging = true;
        hasMoved = false;
        startX = clientX;
        startY = clientY;

        // 3. Get Current Element Position
        // We read computed style to handle implementation where 'left' might be 'auto'
        const rect = container.getBoundingClientRect();
        initialLeft = rect.left;
        initialTop = rect.top;

        // 4. Disable transition for instant response
        container.style.transition = 'none';
        
        // Prevent default text selection
        if (e.type === 'mousedown') e.preventDefault();
    }

    function onDragMove(e) {
        if (!isDragging) return;

        const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;

        // Calculate Delta
        const deltaX = clientX - startX;
        const deltaY = clientY - startY;

        // Threshold Check (for Click vs Drag)
        if (!hasMoved) {
            const dist = Math.sqrt(deltaX*deltaX + deltaY*deltaY);
            if (dist > DRAG_THRESHOLD) {
                hasMoved = true; // Confirmed it's a drag
            } else {
                return; // Ignore small movements
            }
        }

        // Apply Movement
        // strict logic: newPos = initial + delta
        let newLeft = initialLeft + deltaX;
        let newTop = initialTop + deltaY;

        // Strict Clamping
        const winW = window.innerWidth;
        const winH = window.innerHeight;
        const rect = container.getBoundingClientRect();

        if (newLeft < 0) newLeft = 0;
        if (newLeft > winW - rect.width) newLeft = winW - rect.width;
        if (newTop < 0) newTop = 0;
        if (newTop > winH - rect.height) newTop = winH - rect.height;

        applyPosition(newLeft, newTop);
        if (hasMoved) e.preventDefault(); // Only stop scrolling when actually dragging
    }

    function onDragEnd(e) {
        if (!isDragging) return;

        isDragging = false;
        container.style.transition = ''; // Restore smooth effects

        if (hasMoved) {
            // It was a drag, save the final position
            const rect = container.getBoundingClientRect();
            savePosition(rect.left, rect.top);
            
            // Prevent Click! (The 'click' event fires after mouseup)
            // We use a capture listener on the window phase to block it?
            // Or easier: set a flag on the element
            container.setAttribute('data-was-dragged', 'true');
            // Increase timeout to ensure we catch slightly delayed clicks
            setTimeout(() => container.removeAttribute('data-was-dragged'), 350);
        } else {
            // It was a static click (moved < threshold)
            container.removeAttribute('data-was-dragged');
        }
    }

    // --- Click Handling ---

    const toggleBtn = container.querySelector('.floating-chat-btn');
    
    // Robust Click Interceptor
    // We attach to the BUTTON itself in the capture phase to stop Bootstrap (which listens on the button/document)
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function(e) {
            // Check if we dragged
            if (container.getAttribute('data-was-dragged') === 'true') {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation(); // CRITICAL: Stops other listeners on the same element
                return;
            }
        }, true); // Capture phase
    }

    // Also keep container listener just in case
    container.addEventListener('click', function(e) {
        if (container.getAttribute('data-was-dragged') === 'true') {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        }
    }, true);

    // --- Attach Events ---
    
    // Mouse
    container.addEventListener('mousedown', onDragStart);
    document.addEventListener('mousemove', onDragMove);
    document.addEventListener('mouseup', onDragEnd);

    // Touch
    container.addEventListener('touchstart', onDragStart, { passive: false });
    document.addEventListener('touchmove', onDragMove, { passive: false });
    document.addEventListener('touchend', onDragEnd);

    // Window Resize Safety
    window.addEventListener('resize',  () => {
        validateBounds(); // Push it back on screen if resize hides it
    });

    // --- Tab Styling Logic ---
    const tabEls = document.querySelectorAll('#chatWidgetTabs button[data-bs-toggle="tab"]');
    tabEls.forEach(tabEl => {
        tabEl.addEventListener('show.bs.tab', event => {
            // Reset all
            tabEls.forEach(btn => {
                btn.classList.remove('border-bottom', 'border-primary', 'border-2', 'text-primary');
                btn.classList.add('text-secondary');
            });
            // highlight new
            const active = event.target;
            active.classList.remove('text-secondary');
            active.classList.add('border-bottom', 'border-primary', 'border-2', 'text-primary');
        });
    });
});

// Mini Chat Manager
const ChatManager = {
    activeChats: {}, // userId -> windowElement
    knownUnread: {}, // userId -> count
    
    init: function() {
        // Start WebSocket Connection (Real-Time)
        this.connectWebSocket();

        // Intercept clicks on user items in the floating list
        document.addEventListener('click', function(e) {
            // Find if clicking inside a user link
            const userLink = e.target.closest('a[href*="/accounts/messages/compose/?to="]');
            
            // Ensure we are clicking inside the floating menu OR the online users list
            // (We check for .floating-chat-menu context just to be safe, or just intercept all specific compose links)
            if (userLink) {
                e.preventDefault(); // STOP NAVIGATION
                e.stopPropagation();
                
                const urlParams = new URLSearchParams(userLink.href.split('?')[1]);
                const userId = urlParams.get('to');
                
                // Get User Name from the link content (try to find the bold text)
                const nameElement = userLink.querySelector('.fw-bold');
                const userName = nameElement ? nameElement.textContent.trim() : 'مستخدم';
                
                ChatManager.openChat(userId, userName);
                
                // Optional: Hide the main dropdown if desired
                // const dropdownEl = document.getElementById('floatingChatBtn');
                // const dropdown = bootstrap.Dropdown.getInstance(dropdownEl.querySelector('.floating-chat-btn'));
                // if(dropdown) dropdown.hide();
            }
        });
    },

    _wsRetryDelay: 3000,
    _wsMaxRetryDelay: 60000,
    _wsAuthFailed: false,

    connectWebSocket: function() {
        // لا تحاول الاتصال إذا فشلت المصادقة سابقاً
        if (this._wsAuthFailed) return;

        // تحقق من وجود عنصر الشات (يعني المستخدم مسجل دخول)
        if (!document.querySelector('.floating-chat-container')) return;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const socketUrl = `${protocol}//${window.location.host}/ws/chat/`;
        
        this.socket = new WebSocket(socketUrl);
        
        this.socket.onopen = () => {
            console.log('Chat WebSocket Connected');
            this._wsRetryDelay = 3000; // إعادة تعيين مدة الانتظار عند النجاح
        };
        
        this.socket.onmessage = (e) => {
            const data = JSON.parse(e.data);

            if (data.type === 'chat_message') {
                this.handleIncomingMessage(data.message);
            } else if (data.type === 'user_typing') {
                this.handleTyping(data);
            } else if (data.type === 'read_receipt') {
                this.handleReadReceipt(data);
            }
        };
        
        this.socket.onclose = (e) => {
            // كود 4001 = رفض المصادقة - لا تحاول مرة أخرى
            if (e.code === 4001) {
                console.warn('Chat WebSocket: Authentication failed. Will not reconnect.');
                this._wsAuthFailed = true;
                return;
            }
            // Exponential backoff لإعادة المحاولة
            console.warn(`Chat WebSocket Closed. Reconnecting in ${this._wsRetryDelay/1000}s...`);
            setTimeout(() => this.connectWebSocket(), this._wsRetryDelay);
            this._wsRetryDelay = Math.min(this._wsRetryDelay * 2, this._wsMaxRetryDelay);
        };
    },
    
    sendReadReceipt: function(senderId, messageId) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'read_receipt',
                sender_id: senderId, // Original Sender
                message_id: messageId
            }));
        }
    },
    
    handleReadReceipt: function(data) {
        // Mark specific message as read
        if (data.message_id) {
            const elementId = `status-${data.message_id}`;
            const statusEl = document.getElementById(elementId);
            
            if (statusEl) {
                statusEl.innerHTML = '<i class="fas fa-check-double"></i>'; // Two checks
                statusEl.classList.remove('sent');
                statusEl.classList.add('delivered'); // Reuse delivered class for now (Green)
            }
        }
    },
    
    handleTyping: function(data) {
        console.log("DEBUG: Handling Typing UI", data);
        const userId = String(data.sender_id);
        const win = this.activeChats[userId];
        if (!win) return;
        
        const container = win.querySelector('.chat-messages-area');
        let indicator = container.querySelector('.typing-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'typing-indicator';
            indicator.innerHTML = `
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            `;
            container.appendChild(indicator);
        }
        
        if (data.is_typing) {
            indicator.style.display = 'flex';
            this.scrollToBottom(container);
            
            // Auto-hide after 3 seconds of no updates (safety fallback)
            clearTimeout(indicator.hideTimeout);
            indicator.hideTimeout = setTimeout(() => {
                indicator.style.display = 'none';
            }, 3000);
        } else {
            indicator.style.display = 'none';
        }
    },
    
    sendTyping: function(recipientId, isTyping) {
        console.log("DEBUG: Sending Typing", isTyping);
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'typing',
                recipient_id: recipientId,
                is_typing: isTyping
            }));
        }
    },
    
    handleIncomingMessage: function(msg) {
        const userId = String(msg.sender_id);
        
        let win = this.activeChats[userId];
        
        if (!win) {
            // Open NEW window -> Minimized
            this.openChat(userId, msg.sender_name, true);
            win = this.activeChats[userId];
            // Initialize count
            win.dataset.unreadCount = 0;
        }
        
        // Remove typing indicator if exists (message arrived, so stop typing)
        const container = win.querySelector('.chat-messages-area');
        const indicator = container.querySelector('.typing-indicator');
        if (indicator) indicator.style.display = 'none';

        // Append Message
        this.appendMessage(container, msg);
        this.scrollToBottom(container);
        
        // Update Badge logic
        // If window is minimized OR not focused (simplification: just allow manual clear for now) via interaction
        // actually, if we just received a message, we increment badge
        let currentCount = parseInt(win.dataset.unreadCount || 0) + 1;
        win.dataset.unreadCount = currentCount;
        
        this.updateBadge(userId, currentCount);
        
        // Play notification sound if desired
        if (!msg.is_me && win.dataset.muted !== 'true') {
             this.playNotificationSound();
        }
    },
    
    playNotificationSound: function() {
        // التأكد من دعم المتصفح
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return;

        const ctx = new AudioContext();
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        // إعداد النغمة لتكون ناعمة (Sine Wave)
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(880, ctx.currentTime); // تردد 880 هرتز (نغمة A5 مريحة)

        // إعداد مستوى الصوت ليخفت تدريجياً (تأثير الجرس)
        gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 1); // يتلاشى خلال ثانية

        // توصيل العقد ببعضها
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        // تشغيل الصوت
        oscillator.start();
        oscillator.stop(ctx.currentTime + 1);
    },
    
    updateBadge: function(userId, count) {
        if (!this.activeChats[userId]) return;
        const win = this.activeChats[userId];
        const badge = win.querySelector('.unread-badge');
        
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline-block';
                // Beep or Pulse
            } else {
                badge.style.display = 'none';
            }
        }
    },

    openChat: function(userId, userName, startMinimized = false) {
        if (this.activeChats[userId]) {
            const win = this.activeChats[userId];
            if (startMinimized) {
                // Do nothing if already open
            } else {
                // If opening explicitly (user click), maximize and clear badge
                this.maximizeChat(userId);
            }
            return;
        }
        
        // Clone Template
        const template = document.getElementById('mini-chat-template');
        if (!template) return;
        
        const chatWin = template.firstElementChild.cloneNode(true);
        chatWin.id = `chat-window-${userId}`;
        chatWin.setAttribute('data-user-id', userId);
        const openCount = Object.keys(this.activeChats).length;
        
        // Mobile: full width — Desktop: stacked right
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            chatWin.style.width = '100%';
            chatWin.style.right = '0';
            chatWin.style.left = '0';
            chatWin.style.maxHeight = '75vh';
            const msgArea = chatWin.querySelector('.chat-messages-area');
            if (msgArea) msgArea.style.height = '50vh';
        } else {
            chatWin.style.right = `${100 + (openCount * 320)}px`;
        }
        chatWin.style.display = 'block';
        
        // Set Content
        chatWin.querySelector('.chat-username').textContent = userName;
        
        // Inject Badge into Header if not in template
        const headerInfo = chatWin.querySelector('.card-header > div:first-child');
        if (headerInfo && !headerInfo.querySelector('.unread-badge')) {
            const badgeSpan = document.createElement('span');
            badgeSpan.className = 'badge bg-danger rounded-pill ms-2 unread-badge';
            badgeSpan.style.display = 'none';
            badgeSpan.textContent = '0';
            headerInfo.appendChild(badgeSpan);
        }
        
        // Create Mute Button
        const controlsDiv = chatWin.querySelector('.card-header > div:last-child');
        const muteBtn = document.createElement('button');
        muteBtn.className = 'btn btn-link btn-sm text-white p-0 me-2 mute-chat';
        
        // Load initial mute state from LocalStorage
        const isMuted = localStorage.getItem(`chat_muted_${userId}`) === 'true';
        if (isMuted) {
            chatWin.dataset.muted = 'true';
            muteBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
            muteBtn.title = "تشغيل الصوت";
        } else {
            chatWin.dataset.muted = 'false';
            muteBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
            muteBtn.title = "كتم الصوت";
        }

        // Insert before minimize button
        const minBtn = chatWin.querySelector('.minimize-chat');
        controlsDiv.insertBefore(muteBtn, minBtn);

        // Bind Events
        muteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const icon = muteBtn.querySelector('i');
            if (chatWin.dataset.muted === 'true') {
                // Unmute
                chatWin.dataset.muted = 'false';
                localStorage.setItem(`chat_muted_${userId}`, 'false');
                icon.className = 'fas fa-volume-up';
                muteBtn.title = "كتم الصوت";
            } else {
                // Mute
                chatWin.dataset.muted = 'true';
                localStorage.setItem(`chat_muted_${userId}`, 'true');
                icon.className = 'fas fa-volume-mute';
                muteBtn.title = "تشغيل الصوت";
            }
        });

        chatWin.querySelector('.close-chat').addEventListener('click', (e) => {
            e.stopPropagation();
            this.closeChat(userId);
        });
        chatWin.querySelector('.minimize-chat').addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleMinimize(userId);
        });
        
        // Header Click -> Toggle Minimize / Maximize
        chatWin.querySelector('.card-header').addEventListener('click', () => {
            this.toggleMinimize(userId);
        });

        // Mark as read when clicking input
        const inputField = chatWin.querySelector('.chat-input');
        inputField.addEventListener('focus', () => {
            this.markAsRead(userId);
        });
        
        // Typing Indicator Logic
        let typingTimeout;
        inputField.addEventListener('input', () => {
            this.sendTyping(userId, true);
            
            clearTimeout(typingTimeout);
            typingTimeout = setTimeout(() => {
                this.sendTyping(userId, false);
            }, 2000); // Stop typing after 2s of silence
        });
        
        // Mark as read when clicking chat body (optional but good UX)
        chatWin.querySelector('.card-body').addEventListener('click', () => {
            this.markAsRead(userId);
        });

        chatWin.querySelector('.chat-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage(userId, chatWin);
        });
        
        // Append
        document.body.appendChild(chatWin);
        this.activeChats[userId] = chatWin;
        
        // Initial State
        if (startMinimized) {
            chatWin.querySelector('.card-body').style.display = 'none';
            chatWin.querySelector('.card-footer').style.display = 'none';
        } else {
            // Load History only if visible (this triggers Mark as Read on backend)
            this.loadHistory(userId, chatWin);
        }
    },
    
    closeChat: function(userId) {
        const win = this.activeChats[userId];
        if (win) {
            win.remove();
            delete this.activeChats[userId];
            this.repositionWindows();
        }
    },
    
    toggleMinimize: function(userId) {
        const win = this.activeChats[userId];
        const body = win.querySelector('.card-body');
        const footer = win.querySelector('.card-footer');
        
        if (body.style.display === 'none') {
            // Maximize
            this.maximizeChat(userId);
        } else {
            // Minimize
            body.style.display = 'none';
            footer.style.display = 'none';
        }
    },

    maximizeChat: function(userId) {
        const win = this.activeChats[userId];
        if (!win) return;
        
        const body = win.querySelector('.card-body');
        const footer = win.querySelector('.card-footer');
        
        body.style.display = 'block';
        footer.style.display = 'block';
        
        // Mark as read immediately when maximizing
        this.markAsRead(userId);
        
        // Focus input
        setTimeout(() => {
            const input = win.querySelector('.chat-input');
            if (input) input.focus();
            this.scrollToBottom(win.querySelector('.chat-messages-area'));
        }, 100);
    },
    
    markAsRead: function(userId) {
        const win = this.activeChats[userId];
        if (!win) return;
        
        // Check if there are unread messages to mark as read
        const unreadCount = parseInt(win.dataset.unreadCount || 0);
        
        if (unreadCount > 0) {
            // 1. Decrement Global Badge
            this.decrementGlobalBadge(unreadCount);
            
            // 2. Mark as read on Backend (by reloading history)
            // Note: We use loadHistory to sync backend. 
            // If the user is typing, we might not want to reload the whole chat list if it causes flicker.
            // But for now, it's the safest way to ensure "Read" status is synced.
            this.loadHistory(userId, win);
        }
        
        // Clear Local Badge
        win.dataset.unreadCount = 0;
        this.updateBadge(userId, 0);
    },
    
    decrementGlobalBadge: function(amount) {
        const btn = document.getElementById('floatingChatBtn');
        if (!btn) return;
        
        const badge = btn.querySelector('.badge-counter');
        if (!badge) return; // If no badge exists, count is 0
        
        let current = parseInt(badge.textContent || 0);
        let newVal = Math.max(0, current - amount);
        
        if (newVal > 0) {
            badge.textContent = newVal;
        } else {
            badge.style.display = 'none'; // Or remove
        }
    },
    
    repositionWindows: function() {
        const windows = Object.values(this.activeChats);
        windows.forEach((win, index) => {
            win.style.right = `${100 + (index * 320)}px`;
        });
    },
    
    loadHistory: function(userId, win) {
        fetch(`/accounts/api/messages/history/${userId}/`)
            .then(res => res.json())
            .then(data => {
                const container = win.querySelector('.chat-messages-area');
                container.innerHTML = ''; // Clear loading
                container.dataset.lastMessageDate = ''; // Reset Date Separator Logic
                
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        this.appendMessage(container, msg);
                    });
                    this.scrollToBottom(container);
                } else {
                    container.innerHTML = '<div class="text-center text-muted small mt-5">لا توجد رسائل سابقة. ابدأ المحادثة!</div>';
                }
            })
            .catch(err => console.error("Error loading chat:", err));
    },
    
    sendMessage: function(userId, win) {
        const input = win.querySelector('.chat-input');
        const text = input.value.trim();
        if (!text) return;
        
        fetch(`/accounts/api/messages/send/${userId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ body: text })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                input.value = '';
                const container = win.querySelector('.chat-messages-area');
                // Remove empty message placeholder if exists (Look for the centered message div)
                const placeholder = container.querySelector('.text-center.mt-5');
                if (placeholder) placeholder.remove();
                
                this.appendMessage(container, data.message);
                this.scrollToBottom(container);
            }
        })
        .catch(err => {
            console.error("Error sending message:", err);
            // Show error in chat
            const container = win.querySelector('.chat-messages-area');
            const d = document.createElement('div');
            d.className = `chat-message-row me`;
            d.innerHTML = `
                <div class="chat-bubble bg-danger text-white">
                    <div class="small">
                        <i class="fas fa-exclamation-circle me-1"></i>
                        لم يتم الإرسال. حاول مرة أخرى.
                    </div>
                </div>
            `;
            container.appendChild(d);
            this.scrollToBottom(container);
        });
    },
    
    pollMessages: function(userId, win) {
        // For MVP, simplistic polling: 
        // We could verify last ID, but reusing loadHistory clears view which is annoying.
        // Let's implement a 'check new' version later. 
        // For now, let's just let the user manually refresh or implement a distinct poller?
        // Actually, let's skip auto-refresh for this immediate step to ensure STABILITY first, 
        // unless requested. The user asked for "Mini Chat", real-time implies it but 
        // basic send/receive is the core.
        // Let's implement a gentle poll that checks without clearing if possible, 
        // or just rely on user interaction for now to avoid the "flicker" of full reload.
        
        // Implement better polling later.
    },
    
    appendMessage: function(container, msg) {
        // --- Date Separator Logic ---
        const msgDateObj = new Date(msg.created_at || Date.now());
        const msgDateStr = msgDateObj.toLocaleDateString('ar-EG', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        
        // Check local state for last date
        const lastDate = container.dataset.lastMessageDate;
        
        if (lastDate !== msgDateStr) {
            const separator = document.createElement('div');
            separator.className = 'text-center my-3 position-relative';
            separator.innerHTML = `
                <span class="bg-light px-3 py-1 rounded-pill text-muted small border shadow-sm" style="font-size: 0.7rem;">
                    ${msgDateStr}
                </span>
            `;
            // Insert before typing indicator if exists
            const typingIndicator = container.querySelector('.typing-indicator');
            if (typingIndicator) {
                container.insertBefore(separator, typingIndicator);
            } else {
                container.appendChild(separator);
            }
            container.dataset.lastMessageDate = msgDateStr;
        }

        const d = document.createElement('div');
        const isMe = msg.is_me;
        d.className = `chat-message-row ${isMe ? 'me' : 'other'}`;
        
        let avatarHtml = '';
        if (!isMe) {
            const avatarUrl = msg.sender_avatar || null; // Fallback handled by CSS or conditional
            if (avatarUrl) {
                avatarHtml = `<img src="${avatarUrl}" class="chat-avatar" alt="User">`;
            } else {
                avatarHtml = `<div class="chat-avatar bg-secondary d-flex align-items-center justify-content-center text-white" style="font-size: 0.8rem;"><i class="fas fa-user"></i></div>`;
            }
        }
        
        let statusHtml = '';
        if (isMe) {
            const isRead = msg.is_read === true;
            const statusClass = isRead ? 'delivered' : 'sent';
            const statusIcon = isRead ? '<i class="fas fa-check-double"></i>' : '<i class="fas fa-check"></i>';
            statusHtml = `<span class="msg-status ${statusClass}" id="status-${msg.id}">${statusIcon}</span>`;
        }
        
        // Time Formatting
        const timeStr = msgDateObj.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });

        d.innerHTML = `
            ${!isMe ? avatarHtml : ''}
            <div class="chat-bubble">
                <div class="small" style="word-wrap: break-word;">${msg.body}</div>
                <div class="d-flex align-items-center justify-content-end mt-1">
                    ${statusHtml}
                    <div class="text-${isMe ? 'white-50' : 'muted'}" style="font-size: 0.6rem;">${timeStr}</div>
                </div>
            </div>
        `;
        
        // Insert before typing indicator if it exists
        const typingIndicator = container.querySelector('.typing-indicator');
        if (typingIndicator) {
            container.insertBefore(d, typingIndicator);
        } else {
            container.appendChild(d);
        }
    },
    
    scrollToBottom: function(container) {
        container.scrollTop = container.scrollHeight;
    }
};

// Helper: Get Cookie for CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Expose as global for external calls (like Inbox)
window.FloatingChat = ChatManager;

// Init Chat Manager
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ChatManager.init());
} else {
    ChatManager.init();
}
