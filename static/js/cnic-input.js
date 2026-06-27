(function () {
    function formatCnic(value) {
        var digits = value.replace(/\D/g, '').slice(0, 13);
        if (digits.length <= 5) {
            return digits;
        }
        if (digits.length <= 12) {
            return digits.slice(0, 5) + '-' + digits.slice(5);
        }
        return digits.slice(0, 5) + '-' + digits.slice(5, 12) + '-' + digits.slice(12);
    }

    function attach(input) {
        if (input.dataset.cnicBound) {
            return;
        }
        input.dataset.cnicBound = '1';
        input.setAttribute('inputmode', 'numeric');
        input.setAttribute('maxlength', '15');
        input.setAttribute('placeholder', input.getAttribute('placeholder') || '12345-1234567-1');

        input.addEventListener('input', function () {
            var formatted = formatCnic(input.value);
            if (formatted !== input.value) {
                input.value = formatted;
            }
        });

        input.addEventListener('paste', function (event) {
            event.preventDefault();
            var pasted = (event.clipboardData || window.clipboardData).getData('text');
            input.value = formatCnic(pasted);
        });
    }

    function init() {
        document.querySelectorAll('[data-cnic-input]').forEach(attach);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
