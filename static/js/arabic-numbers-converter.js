/**
 * Arabic Numbers to English Converter
 * محول الأرقام العربية إلى الإنجليزية
 * 
 * Automatically converts Arabic numerals (٠-٩) to English (0-9)
 * in all text and number input fields
 */

(function() {
    'use strict';

    /**
     * Convert Arabic numerals to English
     * @param {string} str - Input string
     * @returns {string} - String with English numerals
     */
    function convertArabicToEnglish(str) {
        if (!str) return str;
        
        const arabicNumbers = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
        const englishNumbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
        
        let result = str;
        for (let i = 0; i < 10; i++) {
            result = result.replace(new RegExp(arabicNumbers[i], 'g'), englishNumbers[i]);
        }
        
        return result;
    }

    /**
     * Apply converter to an input element
     * @param {HTMLInputElement} input - Input element
     */
    function applyConverter(input) {
        input.addEventListener('input', function(e) {
            const start = this.selectionStart;
            const end = this.selectionEnd;
            const originalValue = this.value;
            const convertedValue = convertArabicToEnglish(originalValue);
            
            if (originalValue !== convertedValue) {
                this.value = convertedValue;
                // Restore cursor position
                this.setSelectionRange(start, end);
            }
        });
        
        // Also convert on paste
        input.addEventListener('paste', function(e) {
            setTimeout(() => {
                this.value = convertArabicToEnglish(this.value);
            }, 0);
        });
    }

    /**
     * Initialize converter on all relevant inputs
     */
    function initConverter() {
        // Apply to all text and number inputs
        const inputs = document.querySelectorAll(
            'input[type="text"], input[type="number"], input[type="tel"], textarea'
        );
        
        inputs.forEach(input => {
            applyConverter(input);
        });
        
        console.log(`✅ Arabic Numbers Converter initialized on ${inputs.length} inputs`);
    }

    /**
     * Watch for dynamically added inputs (AJAX, etc.)
     */
    function watchDynamicInputs() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        // Check if the node itself is an input
                        if (node.matches && node.matches('input[type="text"], input[type="number"], input[type="tel"], textarea')) {
                            applyConverter(node);
                        }
                        // Check for inputs within the added node
                        const inputs = node.querySelectorAll 
                            ? node.querySelectorAll('input[type="text"], input[type="number"], input[type="tel"], textarea')
                            : [];
                        inputs.forEach(input => applyConverter(input));
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initConverter();
            watchDynamicInputs();
        });
    } else {
        initConverter();
        watchDynamicInputs();
    }

    // Make converter available globally if needed
    window.convertArabicToEnglish = convertArabicToEnglish;

})();
