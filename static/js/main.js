// static/js/main.js — Traffic FMIS JavaScript Utilities

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function () {

    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(function () { alert.remove(); }, 500);
        }, 5000);
    });

    // Auto-uppercase registration number inputs
    const regInputs = document.querySelectorAll('input[name="reg_number"]');
    regInputs.forEach(function (input) {
        input.addEventListener('input', function () {
            this.value = this.value.toUpperCase();
        });
    });

    // Confirm before dangerous actions
    const dangerBtns = document.querySelectorAll('[data-confirm]');
    dangerBtns.forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            if (!confirm(this.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });

});
