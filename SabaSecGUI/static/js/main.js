// main.js – SilentSnare UI Helpers v2
// Toast Notifications · Tooltips · Flash Conversion · API Helpers

// ─── Toast System ─────────────────────────────────────────────────────

const TOAST_ICONS = {
    success: '<i class="fa-solid fa-circle-check"></i>',
    error:   '<i class="fa-solid fa-circle-xmark"></i>',
    warning: '<i class="fa-solid fa-triangle-exclamation"></i>',
    info:    '<i class="fa-solid fa-circle-info"></i>'
};

const TOAST_DURATION = 5000;

function showNotification(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');

    const icon = document.createElement('span');
    icon.className = 'toast-icon';
    icon.innerHTML = TOAST_ICONS[type] || TOAST_ICONS.info;

    const body = document.createElement('div');
    body.className = 'toast-body';

    const title = document.createElement('div');
    title.className = 'toast-title';
    title.textContent = { success: 'Success', error: 'Error', warning: 'Warning', info: 'Info' }[type] || 'Info';

    const msg = document.createElement('div');
    msg.className = 'toast-message';
    msg.textContent = message;

    body.appendChild(title);
    body.appendChild(msg);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.setAttribute('aria-label', 'Dismiss');

    const progress = document.createElement('div');
    progress.className = 'toast-progress';

    toast.appendChild(icon);
    toast.appendChild(body);
    toast.appendChild(closeBtn);
    toast.appendChild(progress);
    container.appendChild(toast);

    // Animate progress bar
    progress.style.transition = `width ${TOAST_DURATION}ms linear`;
    requestAnimationFrame(() => {
        requestAnimationFrame(() => { progress.style.width = '0%'; });
    });

    const dismiss = () => {
        toast.classList.add('hiding');
        setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 350);
    };

    closeBtn.addEventListener('click', (e) => { e.stopPropagation(); dismiss(); });
    toast.addEventListener('click', dismiss);
    const timer = setTimeout(dismiss, TOAST_DURATION);

    // Pause on hover
    toast.addEventListener('mouseenter', () => {
        clearTimeout(timer);
        progress.style.transitionDuration = '0ms';
    });

    return toast;
}

// ─── Convenience Aliases ──────────────────────────────────────────────
function showSuccess(msg) { return showNotification(msg, 'success'); }
function showError(msg)   { return showNotification(msg, 'error');   }
function showWarning(msg) { return showNotification(msg, 'warning'); }
function showInfo(msg)    { return showNotification(msg, 'info');    }

// ─── API Fetch Wrapper with Toasts ────────────────────────────────────
function apiFetch(url, options = {}, successMsg = null, errorMsg = null) {
    options.headers = options.headers || { 'Content-Type': 'application/json' };
    return fetch(url, options)
        .then(async res => {
            const data = await res.json().catch(() => ({}));
            if (res.ok) {
                if (successMsg) showSuccess(successMsg);
            } else {
                const msg = data.error || data.message || errorMsg || 'An unexpected error occurred.';
                showError(msg);
            }
            return { ok: res.ok, data, status: res.status };
        })
        .catch(err => {
            showError(errorMsg || `Network error — ${err.message || 'check connection'}`);
            throw err;
        });
}

// ─── Flash → Toast Converter ──────────────────────────────────────────
function flashToToast() {
    document.querySelectorAll('.flash-message[data-category]').forEach(el => {
        const cat = el.dataset.category;
        const msg = el.textContent.trim();
        const type = cat === 'danger' ? 'error' : cat;
        if (msg) showNotification(msg, type);
        el.remove();
    });
}

// ─── Tooltip System ───────────────────────────────────────────────────
let _activeTooltip = null;

function initTooltips() {
    const elements = document.querySelectorAll('[data-tooltip]');
    elements.forEach(el => {
        el.classList.add('has-tooltip');

        const show = (e) => {
            if (_activeTooltip) _activeTooltip.remove();

            const tip = document.createElement('div');
            tip.className = 'tooltip-popup';
            tip.innerHTML = el.getAttribute('data-tooltip');
            document.body.appendChild(tip);
            _activeTooltip = tip;

            const rect = el.getBoundingClientRect();
            const tipRect = tip.getBoundingClientRect();
            let top = rect.top + window.scrollY - tipRect.height - 10;
            let left = rect.left + window.scrollX + (rect.width / 2) - (tipRect.width / 2);

            // Keep within viewport
            if (top < window.scrollY + 8) top = rect.bottom + window.scrollY + 10;
            if (left < 8) left = 8;
            if (left + tipRect.width > window.innerWidth - 8)
                left = window.innerWidth - tipRect.width - 8;

            tip.style.top  = top + 'px';
            tip.style.left = left + 'px';
            requestAnimationFrame(() => tip.classList.add('visible'));
        };

        const hide = () => {
            if (_activeTooltip) {
                _activeTooltip.classList.remove('visible');
                const t = _activeTooltip;
                setTimeout(() => { if (t.parentNode) t.parentNode.removeChild(t); }, 200);
                _activeTooltip = null;
            }
        };

        el.addEventListener('mouseenter', show);
        el.addEventListener('focusin',    show);
        el.addEventListener('mouseleave', hide);
        el.addEventListener('focusout',   hide);
        el.addEventListener('click',      hide);
    });
}

// ─── Active Nav Highlight ─────────────────────────────────────────────
function highlightActiveNav() {
    const currentPath = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.navbar a').forEach(link => {
        const href = (link.getAttribute('href') || '').replace(/\/$/, '') || '/';
        if (href === currentPath) {
            link.classList.add('nav-active');
        }
    });
}

// ─── Copy to Clipboard Helper ─────────────────────────────────────────
function copyToClipboard(text, label = 'Content') {
    navigator.clipboard.writeText(text)
        .then(() => showSuccess(`${label} copied to clipboard`))
        .catch(() => showError('Copy failed — browser permission denied'));
}

// ─── Confirm Dialog (async) ───────────────────────────────────────────
function confirmAction(message) {
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.className = 'confirm-overlay';
        overlay.innerHTML = `
            <div class="confirm-dialog">
                <div class="confirm-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <div class="confirm-message">${message}</div>
                <div class="confirm-buttons">
                    <button class="btn btn-secondary confirm-cancel">Cancel</button>
                    <button class="btn btn-danger confirm-ok">Confirm</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        requestAnimationFrame(() => overlay.classList.add('visible'));

        const cleanup = (result) => {
            overlay.classList.remove('visible');
            setTimeout(() => overlay.remove(), 250);
            resolve(result);
        };

        overlay.querySelector('.confirm-ok').addEventListener('click', () => cleanup(true));
        overlay.querySelector('.confirm-cancel').addEventListener('click', () => cleanup(false));
        overlay.addEventListener('click', e => { if (e.target === overlay) cleanup(false); });
    });
}

// ─── Page Init ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    flashToToast();
    initTooltips();
    highlightActiveNav();
});
