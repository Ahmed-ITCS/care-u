(function () {
    var DEBOUNCE_MS = 350;

    function submitForm(form) {
        if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    function initForm(form) {
        if (form.dataset.filterAutoBound) {
            return;
        }
        form.dataset.filterAutoBound = '1';

        var debounceTimer = null;

        function scheduleSubmit() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                submitForm(form);
            }, DEBOUNCE_MS);
        }

        form.querySelectorAll('input, select, textarea').forEach(function (el) {
            var type = (el.type || '').toLowerCase();
            if (type === 'submit' || type === 'button' || type === 'hidden') {
                return;
            }

            if (el.tagName === 'SELECT' || type === 'checkbox' || type === 'radio' || type === 'date') {
                el.addEventListener('change', function () {
                    clearTimeout(debounceTimer);
                    submitForm(form);
                });
                return;
            }

            el.addEventListener('input', scheduleSubmit);
        });
    }

    function init() {
        document.querySelectorAll('[data-filter-auto]').forEach(initForm);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
