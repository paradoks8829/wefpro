document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form[data-prevent-double-submit]").forEach(function (form) {
        form.addEventListener("submit", function () {
            var buttons = form.querySelectorAll('[type="submit"]');
            buttons.forEach(function (btn) {
                if (btn.disabled) {
                    return;
                }
                btn.disabled = true;
                if (btn.tagName === "BUTTON") {
                    btn.dataset.originalText = btn.textContent;
                    btn.textContent = "Сохранение...";
                }
            });
        });
    });
});
