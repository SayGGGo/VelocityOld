(function () {
    'use strict';

    window.VelocityUI = window.VelocityUI || {};

    VelocityUI.formatNumber = function (value, decimals) {
        const num = Number(value) || 0;
        const opts = decimals != null
            ? { minimumFractionDigits: decimals, maximumFractionDigits: decimals }
            : { maximumFractionDigits: 0 };
        return num.toLocaleString('ru-RU', opts).replace(/\u00A0/g, ' ').replace(/,/g, ' ');
    };

    VelocityUI.formatRub = function (value, withSymbol) {
        const formatted = VelocityUI.formatNumber(Math.round(Number(value) || 0));
        return withSymbol === false ? formatted : formatted + ' ₽';
    };

    VelocityUI.parseAmountInput = function (raw) {
        return parseInt(String(raw || '').replace(/\s/g, ''), 10) || 0;
    };

    class DigitRoller {
        constructor(container, duration) {
            this.container = container;
            this.duration = duration || 1200;
            this.frame = null;
        }

        renderStatic(formatted) {
            this.container.innerHTML = '';
            formatted.split('').forEach(ch => {
                const slot = document.createElement('span');
                slot.className = 'vel-digit-slot';
                if (/\d/.test(ch)) {
                    const inner = document.createElement('span');
                    inner.className = 'vel-digit-inner';
                    inner.textContent = ch;
                    slot.appendChild(inner);
                } else {
                    slot.className = 'vel-digit-sep';
                    slot.textContent = ch;
                }
                this.container.appendChild(slot);
            });
        }

        animate(fromValue, toValue, suffix) {
            if (this.frame) cancelAnimationFrame(this.frame);
            const fromStr = VelocityUI.formatNumber(Math.round(fromValue));
            const toStr = VelocityUI.formatNumber(Math.round(toValue));
            const maxLen = Math.max(fromStr.length, toStr.length);
            const paddedFrom = fromStr.padStart(maxLen, ' ');
            const paddedTo = toStr.padStart(maxLen, ' ');

            this.container.innerHTML = '';
            const slots = [];
            for (let i = 0; i < maxLen; i++) {
                const chFrom = paddedFrom[i];
                const chTo = paddedTo[i];
                const slot = document.createElement('span');
                if (!/\d/.test(chTo) && !/\d/.test(chFrom)) {
                    slot.className = 'vel-digit-sep';
                    slot.textContent = chTo.trim() ? chTo : '\u00A0';
                    this.container.appendChild(slot);
                    continue;
                }
                slot.className = 'vel-digit-slot';
                const inner = document.createElement('span');
                inner.className = 'vel-digit-inner';
                const col = document.createElement('span');
                col.className = 'vel-digit-col';
                const startDigit = /\d/.test(chFrom) ? parseInt(chFrom, 10) : 0;
                const endDigit = /\d/.test(chTo) ? parseInt(chTo, 10) : 0;
                if (startDigit === endDigit && chFrom === chTo) {
                    inner.textContent = chTo;
                    slot.appendChild(inner);
                    this.container.appendChild(slot);
                    slots.push(null);
                    continue;
                }
                const steps = [];
                let cur = startDigit;
                steps.push(cur);
                while (cur !== endDigit) {
                    cur = (cur + 1) % 10;
                    steps.push(cur);
                }
                steps.forEach(d => {
                    const line = document.createElement('span');
                    line.className = 'vel-digit-line';
                    line.textContent = d;
                    col.appendChild(line);
                });
                inner.appendChild(col);
                slot.appendChild(inner);
                this.container.appendChild(slot);
                slots.push({ col, steps: steps.length - 1, endDigit });
            }

            if (suffix) {
                const suf = document.createElement('span');
                suf.className = 'vel-digit-suffix';
                suf.textContent = suffix;
                this.container.appendChild(suf);
            }

            const start = performance.now();
            const tick = now => {
                const t = Math.min(1, (now - start) / this.duration);
                const eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                slots.forEach(s => {
                    if (!s) return;
                    const step = eased * s.steps;
                    s.col.style.transform = `translateY(-${step * 1.1}em)`;
                });
                if (t < 1) {
                    this.frame = requestAnimationFrame(tick);
                } else {
                    this.renderStatic(toStr + (suffix || ''));
                }
            };
            this.frame = requestAnimationFrame(tick);
        }
    }

    VelocityUI.initBalanceCounters = function () {
        const nodes = Array.from(document.querySelectorAll('[data-balance-counter]'));
        const shouldAnim = sessionStorage.getItem('vel_balance_anim') === '1';
        const prevByKey = {};
        const targetByKey = {};
        nodes.forEach(el => {
            const key = el.dataset.balanceKey;
            if (!(key in prevByKey)) {
                const target = parseFloat(el.dataset.balanceCounter) || 0;
                prevByKey[key] = parseFloat(sessionStorage.getItem('vel_balance_' + key) || String(target));
                targetByKey[key] = target;
            }
        });
        nodes.forEach(el => {
            const key = el.dataset.balanceKey;
            const target = parseFloat(el.dataset.balanceCounter) || 0;
            const prev = prevByKey[key] ?? target;
            const suffix = el.dataset.balanceSuffix || ' ₽';
            const isStatic = el.dataset.balanceStatic === '1' || el.classList.contains('vel-balance-static');
            if (isStatic) {
                el.textContent = VelocityUI.formatNumber(Math.round(target)) + suffix;
                return;
            }
            const roller = new DigitRoller(el, 1200);
            if (Math.abs(prev - target) > 0.5 && shouldAnim) {
                roller.animate(prev, target, suffix.trim() ? suffix : '');
            } else {
                roller.renderStatic(VelocityUI.formatNumber(Math.round(target)) + suffix);
            }
        });
        Object.entries(targetByKey).forEach(([key, val]) => {
            sessionStorage.setItem('vel_balance_' + key, String(val));
        });
        sessionStorage.removeItem('vel_balance_anim');
    };

    VelocityUI.markBalanceAnimation = function () {
        sessionStorage.setItem('vel_balance_anim', '1');
    };

    VelocityUI.openModal = function (id) {
        const m = document.getElementById(id);
        if (m) {
            m.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    };

    VelocityUI.closeModal = function (id) {
        const m = document.getElementById(id);
        if (m) {
            m.style.display = 'none';
            document.body.style.overflow = '';
        }
    };

    VelocityUI.alert = function (msg) {
        return new Promise((resolve) => {
            const modal = document.getElementById('vel-alert-modal');
            const msgEl = document.getElementById('vel-alert-message');
            if (modal && msgEl) {
                msgEl.innerText = msg;
                const closeBtn = modal.querySelector('.vel-modal-close');
                const okBtn = modal.querySelector('.auth-btn');
                const handler = () => {
                    VelocityUI.closeModal('vel-alert-modal');
                    resolve();
                };
                if (closeBtn) closeBtn.onclick = handler;
                if (okBtn) okBtn.onclick = handler;
                VelocityUI.openModal('vel-alert-modal');
            } else {
                window.alert(msg);
                resolve();
            }
        });
    };

    window.alert = VelocityUI.alert;

    VelocityUI.confirm = function (msg) {
        return new Promise((resolve) => {
            const modal = document.getElementById('vel-confirm-modal');
            const msgEl = document.getElementById('vel-confirm-message');
            if (modal && msgEl) {
                msgEl.innerText = msg;
                const cancelBtn = document.getElementById('vel-confirm-cancel');
                const okBtn = document.getElementById('vel-confirm-ok');
                const closeBtn = modal.querySelector('.vel-modal-close');
                const onCancel = () => {
                    VelocityUI.closeModal('vel-confirm-modal');
                    resolve(false);
                };
                const onOk = () => {
                    VelocityUI.closeModal('vel-confirm-modal');
                    resolve(true);
                };
                if (cancelBtn) cancelBtn.onclick = onCancel;
                if (closeBtn) closeBtn.onclick = onCancel;
                if (okBtn) okBtn.onclick = onOk;
                VelocityUI.openModal('vel-confirm-modal');
            } else {
                resolve(window.confirm(msg));
            }
        });
    };

    VelocityUI.showToast = function (title, msg, type = 'success') {
        const toast = document.createElement('div');
        toast.style.position = 'fixed';
        toast.style.bottom = '30px';
        toast.style.right = '30px';
        toast.style.background = '#111';
        toast.style.border = '1px solid rgba(255,255,255,0.1)';
        toast.style.padding = '14px 20px';
        toast.style.borderRadius = '12px';
        toast.style.color = '#fff';
        toast.style.fontSize = '12px';
        toast.style.zIndex = '100000';
        toast.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
        toast.style.display = 'flex';
        toast.style.alignItems = 'center';
        toast.style.gap = '12px';
        toast.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
        toast.style.transform = 'translateY(100px)';
        toast.style.opacity = '0';

        const iconClass = type === 'success' ? 'ph ph-check-circle' : 'ph ph-info';
        const iconColor = type === 'success' ? '#4ade80' : '#3b82f6';
        toast.innerHTML = `
            <i class="${iconClass}" style="color:${iconColor}; font-size:18px;"></i>
            <div>
                <strong style="display:block; font-size:10px; text-transform:uppercase; color:#666; letter-spacing:0.5px;">${title}</strong>
                <span>${msg}</span>
            </div>
        `;
        document.body.appendChild(toast);
        
        
        toast.offsetHeight;
        
        toast.style.transform = 'translateY(0)';
        toast.style.opacity = '1';

        setTimeout(() => {
            toast.style.transform = 'translateY(20px)';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    document.addEventListener('DOMContentLoaded', () => {
        const params = new URLSearchParams(window.location.search);
        if (params.get('balance_anim') === '1') {
            VelocityUI.markBalanceAnimation();
            params.delete('balance_anim');
            const qs = params.toString();
            const clean = window.location.pathname + (qs ? '?' + qs : '');
            window.history.replaceState({}, '', clean);
        }
        VelocityUI.initBalanceCounters();
    });
})();
