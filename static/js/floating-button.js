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
        e.preventDefault(); // Stop scrolling on touch
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
            setTimeout(() => container.removeAttribute('data-was-dragged'), 50);
        } else {
            // It was a static click (moved < threshold)
            container.removeAttribute('data-was-dragged');
        }
    }

    // --- Click Handling ---

    const toggleBtn = container.querySelector('.floating-chat-btn');
    
    // Intercept Click
    container.addEventListener('click', function(e) {
        // If we just finished a drag, STOP EVERYTHING.
        if (container.getAttribute('data-was-dragged') === 'true') {
            e.preventDefault();
            e.stopPropagation();
            return;
        }

        // Otherwise, allow normal bootstrap toggle
        // Safely Initialize/Get Dropdown
        const dropdown = bootstrap.Dropdown.getOrCreateInstance(toggleBtn || container);
        dropdown.toggle();
    }, true); // Capture phase to intervene early? No, bubbling is fine if we check the attribute.

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
});
