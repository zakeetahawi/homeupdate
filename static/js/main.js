// Theme Management
document.addEventListener('DOMContentLoaded', function() {
    // Get theme selector element
    const themeSelector = document.getElementById('themeSelector');
    if (!themeSelector) return;

    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('selectedTheme') || 'default';
    themeSelector.value = savedTheme;
    applyTheme(savedTheme);

    // Listen for theme changes
    themeSelector.addEventListener('change', function(e) {
        const selectedTheme = e.target.value;
        applyTheme(selectedTheme);
        localStorage.setItem('selectedTheme', selectedTheme);
    });
});

function applyTheme(theme) {
    document.body.setAttribute('data-theme', theme);
}
