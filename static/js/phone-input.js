(function () {
    function attachLocal(input) {
        if (input.dataset.phoneLocalBound) {
            return;
        }
        input.dataset.phoneLocalBound = '1';

        input.addEventListener('input', function () {
            var digits = input.value.replace(/\D/g, '');
            if (digits !== input.value) {
                input.value = digits;
            }
        });

        input.addEventListener('paste', function (event) {
            event.preventDefault();
            var pasted = (event.clipboardData || window.clipboardData).getData('text');
            input.value = pasted.replace(/\D/g, '');
        });
    }

    function updatePlaceholder(select, input) {
        if (select.value === '+92') {
            input.placeholder = '3001234567';
        } else {
            input.placeholder = 'Phone number';
        }
    }

    function attachGroup(group) {
        var select = group.querySelector('[data-phone-country]');
        var input = group.querySelector('[data-phone-local]');
        if (!select || !input) {
            return;
        }
        attachLocal(input);
        updatePlaceholder(select, input);
        select.addEventListener('change', function () {
            updatePlaceholder(select, input);
        });
    }

    function init() {
        document.querySelectorAll('.phone-input-group').forEach(attachGroup);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
