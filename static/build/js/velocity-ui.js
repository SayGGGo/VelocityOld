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

(function(){const s=document.createElement('style');s.innerHTML=`:root { --bg-color: #050505; --text-primary: #ffffff; --text-muted: #777777; --border: rgba(255, 255, 255, 0.08); --panel-bg: rgba(12, 12, 12, 0.75); } * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Unbounded', sans-serif !important; } body { background-color: var(--bg-color); color: var(--text-primary); -webkit-font-smoothing: antialiased; overflow-x: hidden; } .word { opacity: 0.1; } .scroll-fade { opacity: 0; transform: translateY(30px); } .ai-logo-img { opacity: 0; transform: translateY(20px); } .glass-panel { opacity: 0; transform: translateY(50px) rotateX(5deg); } #topo-canvas { position: absolute; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -3; pointer-events: none; } ._kb { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -2; pointer-events: none; opacity: 0.03; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E"); } .monotone-img { background-color: #000; } .monotone-img:hover { filter: grayscale(100%) contrast(1.15) brightness(0.85) !important; } ._Ab { position: fixed; right: 40px; top: 50%; transform: translateY(-50%); display: flex; flex-direction: column; gap: 15px; z-index: 1000; } .side-nav-item { display: flex; align-items: center; justify-content: flex-end; gap: 15px; cursor: pointer; } .nav-label { font-size: 10px; font-weight: 900; letter-spacing: 3px; color: var(--text-primary); opacity: 0; transform: translateX(20px); transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1); pointer-events: none; text-transform: uppercase; } .nav-dot { width: 4px; height: 40px; background: rgba(255, 255, 255, 0.15); border-radius: 4px; transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1); } .side-nav-item:hover .nav-label { opacity: 0.8; transform: translateX(0); } .side-nav-item:hover .nav-dot { background: rgba(255, 255, 255, 0.5); } .side-nav-item.active .nav-label { opacity: 1; transform: translateX(0); } .side-nav-item.active .nav-dot { background: var(--text-primary); height: 80px; } .header-blur-bg { position: fixed; top: 0; left: 0; width: 100%; height: 90px; background: linear-gradient(to bottom, rgba(5,5,5,0.95) 20%, rgba(5,5,5,0.5) 70%, transparent 100%); backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px); z-index: 999; opacity: 0; transition: opacity 0.4s ease; pointer-events: none; } ._Bb { position: fixed; top: 0; width: 100%; z-index: 1000; background: transparent; } ._jb { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 60px; padding: 0 20px; border-bottom: 1px solid var(--border); } ._eb { height: 20px; filter: invert(1); } ._cb { display: flex; gap: 40px; } ._cb a { color: var(--text-muted); text-decoration: none; font-size: 10px; font-weight: 600; letter-spacing: 1px; transition: color 0.3s ease; } ._cb a:hover { color: var(--text-primary); } ._l { display: flex; align-items: center; justify-content: center; gap: 10px; background: transparent; color: var(--text-primary); text-decoration: none; padding: 12px 24px; border: 1px solid var(--border); border-radius: 40px; font-size: 10px; font-weight: 800; letter-spacing: 1px; transition: all 0.3s ease; cursor: pointer; } ._l:hover { background: var(--text-primary); color: var(--bg-color); } ._n { transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); border-radius: 50px; } ._n:hover { transform: scale(1.05); } ._n:active { transform: scale(0.95); } ._l:hover .btn-arrow { filter: invert(1); } .btn-arrow { width: 10px; transition: filter 0.3s ease; } ._l._nb { width: 100%; } ._l._S { width: 100%; background: var(--text-primary); color: var(--bg-color); } ._U { min-height: 100vh; padding-top: 60px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; } .badge { display: inline-block; padding: 8px 16px; border: 1px solid var(--border); border-radius: 30px; font-size: 9px; font-weight: 700; letter-spacing: 2px; color: var(--text-muted); margin-bottom: 40px; } ._fb { font-size: 11vw; font-weight: 900; line-height: 0.85; letter-spacing: -0.04em; margin-bottom: 40px; text-transform: uppercase; text-align: center; } ._hb { font-size: 12px; color: var(--text-muted); font-weight: 400; max-width: 380px; margin: 0 auto 60px; line-height: 1.8; letter-spacing: 0.5px; text-align: center; } ._hb._p { max-width: 500px; } ._gb { font-size: 6vw; font-weight: 900; line-height: 0.9; letter-spacing: -0.03em; margin-bottom: 30px; text-transform: uppercase; text-align: center; } .hero-3d-wrapper { width: 100%; max-width: 900px; padding: 0 20px; } .hero-image-container { width: 100%; border-radius: 12px; overflow: hidden; will-change: transform; border: 1px solid var(--border); background: #000; } .hero-image { width: 100%; height: auto; display: block; } ._zb { position: absolute; bottom: 5vh; left: 50%; transform: translateX(-50%); opacity: 0.2; } ._ib { width: 22px; height: 34px; border: 1px solid var(--text-primary); border-radius: 12px; display: flex; justify-content: center; padding-top: 6px; } ._Hb { width: 2px; height: 6px; background: var(--text-primary); border-radius: 2px; animation: scrollWheel 2s infinite ease-in-out; } @keyframes scrollWheel { 0% { transform: translateY(0); opacity: 1; } 50% { transform: translateY(10px); opacity: 0; } 100% { transform: translateY(0); opacity: 0; } } .statement-section { height: 100vh; display: flex; justify-content: center; align-items: center; } .statement-text { font-size: 3vw; font-weight: 800; line-height: 1.2; text-align: center; max-width: 1200px; text-transform: uppercase; color: var(--text-muted); } .massive-word { font-size: 8vw; color: var(--text-primary); display: block; margin: 10px 0; } ._J { position: relative; width: 100%; } .feature-card { position: sticky; top: 0; height: 100vh; width: 100vw; display: flex; align-items: center; justify-content: center; overflow: hidden; background: #000; } .feature-card:nth-child(1) { z-index: 1; } .feature-card:nth-child(2) { z-index: 2; box-shadow: 0 -20px 50px rgba(0,0,0,0.9); } .feature-card:nth-child(3) { z-index: 3; box-shadow: 0 -20px 50px rgba(0,0,0,0.9); } ._E { position: absolute; top: 0; left: 0; width: 100%; height: 100%; } ._T { width: 100%; height: 100%; object-fit: cover; display: block; opacity: 1 !important; filter: grayscale(100%) brightness(0.35) !important; } .faq-item { border-bottom: 1px solid rgba(255,255,255,0.1); } .faq-question { width: 100%; background: transparent; border: none; color: var(--text-primary); padding: 25px 0; font-size: 14px; font-weight: 600; text-align: left; display: flex; justify-content: space-between; align-items: center; cursor: pointer; letter-spacing: 1px; outline: none; } ._D { font-size: 20px; font-weight: 300; transition: transform 0.3s ease; } .faq-item.active ._D { transform: rotate(45deg); color: rgba(255,255,255,0.5); } .faq-answer { max-height: 0; overflow: hidden; transition: max-height 0.4s ease; } .faq-answer p { font-size: 12px; color: var(--text-muted); padding-bottom: 25px; line-height: 1.6; } .glass-panel { position: absolute; top: 50%; left: 10%; transform: translateY(-50%); background: var(--panel-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); padding: 60px 50px; border-radius: 8px; max-width: 420px; border: 1px solid var(--border); } .glass-panel._yb { left: auto; right: 10%; } .panel-icon { height: 24px; margin-bottom: 30px; filter: invert(1); } ._pb { font-size: 24px; margin-bottom: 20px; font-weight: 900; text-transform: uppercase; letter-spacing: -0.02em; } ._ob { font-size: 11px; line-height: 1.7; color: var(--text-muted); margin-bottom: 30px; } ._F { list-style: none; display: flex; flex-direction: column; gap: 15px; } ._F li { font-size: 11px; color: #ccc; display: flex; align-items: flex-start; gap: 10px; line-height: 1.4; } ._F li span { color: #fff; font-weight: 900; } ._b { padding: 150px 20px 100px; display: flex; flex-direction: column; align-items: center; } ._a { max-width: 1000px; text-align: center; margin-bottom: 100px; } .ai-logos { display: flex; justify-content: center; flex-wrap: wrap; gap: 50px; align-items: center; margin-top: 60px; } .ai-logo-img { height: 30px; width: auto; object-fit: contain; filter: grayscale(100%) brightness(2.5) contrast(0.5); transition: opacity 0.3s ease, filter 0.3s ease; } .ai-logo-img:hover { opacity: 1 !important; filter: grayscale(100%) brightness(3) contrast(1); } ._wb { padding: 100px 20px 150px; max-width: 1200px; margin: 0 auto; } ._vb { text-align: center; margin-bottom: 80px; } ._ub { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; } .price-card { border: 1px solid var(--border); border-radius: 12px; padding: 40px 30px; background: rgba(10, 10, 10, 0.4); position: relative; display: flex; flex-direction: column; } .price-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(600px circle at var(--mouse-x, 0px) var(--mouse-y, 0px), rgba(255,255,255,0.08), transparent 40%); opacity: 0; transition: opacity 0.3s ease; z-index: 0; pointer-events: none; border-radius: inherit; } .price-card:hover::before { opacity: 1; } .price-card > * { position: relative; z-index: 1; } .price-card._G { border-color: rgba(255, 255, 255, 0.2); background: rgba(15, 15, 15, 0.8); } .price-card._I { border-color: rgba(255, 255, 255, 0.6); background: rgba(25, 25, 25, 0.9); box-shadow: 0 0 50px rgba(255,255,255,0.08); transform: translateY(-10px); } ._H { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: var(--text-primary); color: var(--bg-color); padding: 4px 12px; border-radius: 20px; font-size: 9px; font-weight: 800; letter-spacing: 1px; white-space: nowrap; } .plan-name { font-size: 13px; font-weight: 900; margin-bottom: 15px; color: var(--text-muted); letter-spacing: 1px; } ._z { display: flex; width: 100%; height: 400px; gap: 15px; } ._u { flex: 1; border-radius: 30px; background: rgba(15, 15, 15, 0.4); border: 1px solid rgba(255,255,255,0.05); position: relative; overflow: hidden; transition: flex 0.5s cubic-bezier(0.16, 1, 0.3, 1), background 0.3s ease; cursor: pointer; display: flex; flex-direction: column; justify-content: center; align-items: center; backdrop-filter: blur(10px); } ._u:hover { flex: 3; background: rgba(25, 25, 25, 0.8); border-color: rgba(255,255,255,0.2); } ._x { width: 60px; height: 60px; object-fit: contain; filter: grayscale(100%) brightness(0.6) contrast(1.2); transition: all 0.5s ease; } ._u:hover ._x { filter: grayscale(100%) brightness(1.2) contrast(1.2); transform: translateY(-30px) scale(1.2); } ._v { position: absolute; bottom: 30px; left: 0; width: 100%; text-align: center; opacity: 0; transform: translateY(15px); transition: opacity 0.3s ease, transform 0.3s ease; padding: 0 15px; pointer-events: none; } ._u:hover ._v { opacity: 1; transform: translateY(0); transition: opacity 0.8s ease 0.2s, transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.15s; } ._y { font-size: 12px; font-weight: 800; color: var(--text-primary); letter-spacing: 2px; margin-bottom: 8px; } ._w { font-size: 10px; color: var(--text-muted); line-height: 1.4; } @media (max-width: 900px) { ._z { flex-direction: column; height: auto; } ._u { height: 80px; flex-direction: row; justify-content: flex-start; padding: 0 20px; } ._u:hover { height: 180px; } ._x { width: 40px; height: 40px; } ._u:hover ._x { transform: translateY(-10px) scale(1.1); } ._v { position: static; opacity: 1; transform: none; text-align: left; margin-left: 20px; padding: 0; } ._u:hover ._v { transform: none; } } .price-card._G .plan-name, .price-card._I .plan-name { color: var(--text-primary); } ._H._xb { background: #ffffff; color: #000000; } ._sb { font-size: 32px; font-weight: 900; margin-bottom: 30px; letter-spacing: -0.03em; } ._sb span { font-size: 11px; color: var(--text-muted); font-weight: 400; } ._tb { list-style: none; margin-bottom: 40px; display: flex; flex-direction: column; gap: 12px; flex-grow: 1; } ._tb li { font-size: 10px; display: flex; align-items: center; gap: 10px; color: #ccc; line-height: 1.4; } ._tb li._s { color: #555; } ._tb li._X { color: #fff; font-weight: 700; } ._R { background: #000000; border-top: 1px solid var(--border); padding: 100px 20px 40px; } ._O { max-width: 1200px; margin: 0 auto 80px; display: grid; grid-template-columns: 1fr 2fr; gap: 80px; } ._M ._Q { height: 18px; margin-bottom: 25px; filter: invert(1); } ._N { font-size: 10px; color: var(--text-muted); line-height: 1.8; } ._P { display: grid; grid-template-columns: repeat(3, 1fr); gap: 40px; } ._bb h4 { font-size: 9px; font-weight: 800; letter-spacing: 2px; margin-bottom: 25px; color: #fff; } ._bb a { display: block; color: var(--text-muted); text-decoration: none; font-size: 11px; margin-bottom: 15px; transition: color 0.3s; } ._bb a:hover { color: #fff; } ._L { max-width: 1200px; margin: 0 auto; display: flex; justify-content: center; border-top: 1px solid var(--border); padding-top: 40px; } ._d { font-family: 'Unbounded', sans-serif; background: #000; color: #fff; overflow: hidden; display: flex; height: 100vh; } ._g { width: 40%; min-width: 450px; padding: 60px; display: flex; flex-direction: column; justify-content: center; position: relative; z-index: 10; background: rgba(5,5,5,0.9); border-right: 1px solid rgba(255,255,255,0.05); box-shadow: 20px 0 50px rgba(0,0,0,0.5); } ._h { width: 60%; position: relative; background: radial-gradient(circle at center, #0a0f14 0%, #000 100%); display: flex; align-items: center; justify-content: center; overflow: hidden; cursor: grab; } ._h:active { cursor: grabbing; } .auth-logo { width: 180px; margin-bottom: 60px; filter: invert(1); } ._k { font-size: 32px; font-weight: 900; margin-bottom: 10px; letter-spacing: -1px; } ._i { font-size: 12px; color: #666; margin-bottom: 40px; line-height: 1.5; } ._f { display: flex; flex-direction: column; gap: 20px; } .input-group { display: flex; flex-direction: column; gap: 8px; position: relative; } .input-group label { font-size: 10px; font-weight: 700; color: #555; letter-spacing: 2px; text-transform: uppercase; } .input-group input { background: #0a0a0a; border: 1px solid #222; padding: 18px 20px; border-radius: 12px; color: #fff; font-family: 'Unbounded', sans-serif; font-size: 14px; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); transform-origin: left center; } .input-group input:focus { outline: none; border-color: #fff; background: #0c1218; box-shadow: 0 10px 30px rgba(255, 255, 255, 0.15); transform: scale(1.02); } ._rb { position: absolute; right: 15px; bottom: 16px; cursor: pointer; opacity: 0.3; transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; z-index: 2; } ._rb:hover { opacity: 1; } ._rb svg { width: 18px; height: 18px; fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; position: absolute; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); } ._rb ._B { opacity: 0; transform: scale(0.5) rotate(-45deg); } ._rb ._A { opacity: 1; transform: scale(1) rotate(0); } ._rb._W ._B { opacity: 1; transform: scale(1) rotate(0); } ._rb._W ._A { opacity: 0; transform: scale(0.5) rotate(45deg); } ._e { background: #fff; color: #000; border: none; padding: 20px; border-radius: 12px; font-weight: 800; font-family: 'Unbounded', sans-serif; font-size: 12px; letter-spacing: 1px; cursor: pointer; transition: 0.3s; margin-top: 10px; } ._e:hover { background: #fff; color: #000; transform: translateY(-2px); } ._j { margin-top: 30px; font-size: 12px; color: #666; text-align: center; } ._j a { color: #fff; text-decoration: none; font-weight: 600; transition: 0.3s; cursor: pointer; } ._j a:hover { color: #fff; } ._o { position: absolute; top: 0; left: 0; width: 100%; height: 100%; } ._t { position: absolute; bottom: 40px; left: 50%; transform: translateX(-50%); font-size: 10px; letter-spacing: 4px; color: rgba(255,255,255,0.2); pointer-events: none; font-weight: 700; z-index: 20; } @media (max-width: 900px) { ._d { flex-direction: column-reverse; overflow-y: auto; height: auto; } ._g { width: 100%; min-height: 60vh; border-right: none; padding: 40px 20px; } ._h { width: 100%; height: 40vh; min-height: 300px; border-bottom: 1px solid rgba(255,255,255,0.05); } .auth-logo { margin-bottom: 40px; } } ._r { font-size: 9px; color: var(--text-muted); letter-spacing: 1px; } @media (max-width: 1200px) { ._Ab { display: none; } } @media (max-width: 1024px) { ._ub { grid-template-columns: 1fr 1fr; gap: 40px; } ._fb { font-size: 15vw; } .statement-text { font-size: 5vw; } .massive-word { font-size: 10vw; } } @media (max-width: 900px) { ._cb { display: none; } ._gb { font-size: 8vw; } ._O { grid-template-columns: 1fr; gap: 50px; } ._P { grid-template-columns: 1fr 1fr; } } @media (max-width: 600px) { .glass-panel, .glass-panel._yb { left: 5%; right: 5%; max-width: none; bottom: 5%; top: auto; transform: none; padding: 40px 30px; } ._U { padding-top: 140px; } ._P { grid-template-columns: 1fr; } .ai-logos { gap: 30px; } ._ub { grid-template-columns: 1fr; } ._n { padding: 18px 40px !important; font-size: 10px !important; } } ::-webkit-scrollbar { display: none !important; width: 0 !important; } * { scrollbar-width: none !important; } body { -ms-overflow-style: none; scrollbar-width: none; overflow-x: hidden; } ._K { position: fixed; top: 20px !important; left: 50% !important; transform: translateX(-50%) !important; width: 95%; max-width: 1200px; background: rgba(5,5,5,0.6) !important; backdrop-filter: blur(20px) !important; -webkit-backdrop-filter: blur(20px) !important; border: 1px solid rgba(255,255,255,0.05) !important; border-radius: 50px !important; padding: 10px 20px; z-index: 1000; } ._K ._jb { border-bottom: none !important; height: 50px; } .vel-digit-slot { display: inline-block; height: 1.1em; overflow: hidden; vertical-align: bottom; line-height: 1.1em; font-family: 'Unbounded', sans-serif !important; } .vel-digit-inner { display: block; font-family: inherit; } .vel-digit-col { display: flex; flex-direction: column; } .vel-digit-line { height: 1.1em; line-height: 1.1em; display: block; font-family: inherit; } .vel-digit-sep { display: inline-block; opacity: 0.55; padding: 0 1px; font-family: inherit; } .vel-digit-suffix { margin-left: 4px; font-size: 0.72em; opacity: 0.75; font-family: inherit; } .vel-balance-counter { font-variant-numeric: tabular-nums; letter-spacing: 0.02em; font-family: 'Unbounded', sans-serif !important; } .vel-balance-static { font-family: 'Unbounded', sans-serif !important; font-weight: 900; font-variant-numeric: tabular-nums; } .wallet-balance-big { font-family: 'Unbounded', sans-serif !important; font-weight: 900; font-variant-numeric: tabular-nums; } ._Gb { display: none; position: fixed; inset: 0; background: rgba(5,5,5,0.88); backdrop-filter: blur(20px); z-index: 100000; align-items: center; justify-content: center; padding: 20px; box-sizing: border-box; } ._Eb { background: rgba(15,15,15,0.96); border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; max-width: 440px; width: 100%; padding: 28px; color: #fff; box-shadow: 0 30px 80px rgba(0,0,0,0.8); position: relative; animation: velModalIn 0.35s ease; } @keyframes velModalIn { from { opacity: 0; transform: translateY(16px) scale(0.98); } to { opacity: 1; transform: none; } } ._Fb { position: absolute; top: 16px; right: 16px; background: none; border: none; color: #fff; font-size: 22px; cursor: pointer; opacity: 0.5; } ._Fb:hover { opacity: 1; } .vel-toast-wrap { display: none !important; } .vel-toast { display: none !important; } .model-card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; padding: 14px; cursor: pointer; transition: 0.25s; } .model-card:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.15); } .model-card.selected { border-color: #fff; background: rgba(255,255,255,0.08); } .model-card.unavailable:not(.locked-plan) { opacity: 0.35; pointer-events: none; } .model-card.locked-plan { opacity: 0.55; border-style: dashed; border-color: rgba(255,154,158,0.35); cursor: pointer; } .model-card.locked-plan:hover { border-color: rgba(255,154,158,0.6); background: rgba(255,154,158,0.05); } .models-category-card.category-locked { opacity: 0.55; border-style: dashed; } .models-category-card.category-locked:hover { border-color: rgba(255,154,158,0.4); } .model-card-auto { border-style: dashed; } .category-block { margin-bottom: 28px; } .models-category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 28px; } .models-category-card { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 20px 16px; cursor: pointer; transition: 0.25s; text-align: center; } .models-category-card:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.18); transform: translateY(-2px); } .models-category-icon { width: 44px; height: 44px; margin: 0 auto 12px; border-radius: 12px; background: rgba(255,255,255,0.04); display: flex; align-items: center; justify-content: center; padding: 8px; overflow: hidden; } .models-category-icon img.monotone-img { width: 28px; height: 28px; object-fit: contain; filter: grayscale(100%); opacity: 0.7; mix-blend-mode: screen; transition: 0.25s; } .models-category-card:hover .models-category-icon img.monotone-img { opacity: 1; filter: grayscale(100%) brightness(1.15); } .category-head .models-category-icon { margin: 0; flex-shrink: 0; } .models-pinned-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 28px; } .models-pinned-slot { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px; min-height: 110px; cursor: pointer; transition: 0.25s; display: flex; flex-direction: column; justify-content: center; } .models-pinned-slot:hover { border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.04); } .models-pinned-empty { border-style: dashed; align-items: center; text-align: center; color: #555; } .models-pinned-empty i { font-size: 28px; margin-bottom: 8px; } .models-view-back { display: inline-flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 700; color: #888; cursor: pointer; margin-bottom: 20px; border: none; background: none; padding: 0; letter-spacing: 0.5px; } .models-view-back:hover { color: #fff; } .pinned-slot-name { font-size: 12px; font-weight: 800; margin-bottom: 4px; } .pinned-slot-meta { font-size: 10px; color: #666; } ._c input { font-variant-numeric: tabular-nums; } .btn-pay-ready { opacity: 1 !important; box-shadow: 0 0 24px rgba(255,255,255,0.35) !important; cursor: pointer !important; } ._m { opacity: 0.35 !important; cursor: not-allowed !important; box-shadow: none !important; } `;document.head.appendChild(s);})();
