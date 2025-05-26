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
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // Remove any existing theme
    document.body.removeAttribute('data-theme');
    
    // Apply new theme if it's not the default
    if (theme !== 'default') {
        document.body.setAttribute('data-theme', theme);
    }

    // Store the theme preference
    localStorage.setItem('selectedTheme', theme);

    // Remove transition after it's complete
    setTimeout(() => {
        document.body.style.transition = '';
    }, 300);
}

// Generic alert dismissal
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const dismissBtn = new bootstrap.Alert(alert);
            dismissBtn.close();
        });
    }, 5000);
});

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Responsive table handling
document.addEventListener('DOMContentLoaded', function() {
    const tables = document.querySelectorAll('.table-responsive table');
    tables.forEach(table => {
        if (table.offsetWidth > table.parentElement.offsetWidth) {
            table.parentElement.classList.add('table-scroll');
        }
    });
});

// Dynamic form fields
function addFormField(containerId, template) {
    const container = document.getElementById(containerId);
    const newRow = template.cloneNode(true);
    container.appendChild(newRow);
}

// Format currency in Egyptian Pounds
function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-EG', { 
        style: 'currency', 
        currency: 'EGP' 
    }).format(amount);
}

// Function to toggle password visibility
function togglePasswordVisibility(inputId, iconId) {
    var passwordInput = document.getElementById(inputId);
    var icon = document.getElementById(iconId);
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}
