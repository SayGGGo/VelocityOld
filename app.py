from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import random
import string
import os
import re
import threading
import shutil
import pyotp
import requests
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth
from models import db, User, UserSession, UserEmail, UserPasskey, Payment, Transaction, Organization, PRO_ENTRY_PRICE, PRO_BONUS_TOKENS
                              
from dotenv import load_dotenv
load_dotenv()

def generate_styled_email(title, message_body, action_text=None, action_url=None, code=None):
    code_block = ""
    if code:
        code_block = f"""
        <div style="background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; text-align: center; margin: 30px 0;">
            <span style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #ffffff; font-family: monospace;">{code}</span>
        </div>
        """
    action_button = ""
    if action_text and action_url:
        action_button = f"""
        <div style="text-align: center; margin: 30px 0;">
            <a href="{action_url}" style="background-color: #ffffff; color: #000000; padding: 16px 32px; border-radius: 12px; font-weight: 800; font-size: 12px; text-decoration: none; display: inline-block; transition: 0.3s; letter-spacing: 1px; text-transform: uppercase;">{action_text}</a>
        </div>
        """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { 
                background-color: #050505;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 0;
            } 
        </style>
    </head>
    <body style="background-color: #050505; color: #ffffff; padding: 40px 20px; margin: 0;">
        <div style="background: #0a0a0a; padding: 40px; border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.05); width: 100%; max-width: 500px; margin: 0 auto; box-shadow: 0 20px 50px rgba(0,0,0,0.5); box-sizing: border-box;">
            <div style="text-align: center; margin-bottom: 40px;">
                <span style="font-size: 24px; font-weight: 900; letter-spacing: 2px; color: #ffffff;">VELOCITY</span>
            </div>
            <h1 style="font-size: 18px; font-weight: 800; margin-bottom: 20px; color: #ffffff; text-align: center; text-transform: uppercase; letter-spacing: 1px;">{title}</h1>
            <p style="font-size: 13px; color: #aaaaaa; line-height: 1.6; margin-bottom: 25px; text-align: center;">{message_body}</p>
            {code_block}
            {action_button}
            <div style="margin-top: 40px; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 20px; text-align: center; font-size: 11px; color: #555555; line-height: 1.4;">
                Это автоматическое письмо безопасности от VELOCITY.<br>
                Если вы не совершали данное действие, просто проигнорируйте его.<br><br>
                &copy; 2026 VELOCITY. Все права защищены.
            </div>
        </div>
    </body>
    </html>
    """

def create_user_session(user):
    session_key = os.urandom(24).hex()
    session['session_key'] = session_key
                      
    user_agent_str = request.user_agent.string or ""
    device = "Неизвестное устройство"
    if "Windows" in user_agent_str: device = "Windows (ПК)"
    elif "Macintosh" in user_agent_str: device = "macOS (ПК)"
    elif "iPhone" in user_agent_str: device = "iPhone"
    elif "iPad" in user_agent_str: device = "iPad"
    elif "Android" in user_agent_str: device = "Android"
    elif "Linux" in user_agent_str: device = "Linux (ПК)"
                
    ip = get_client_ip()
                                                 
    try:
        UserSession.query.filter_by(user_id=user.id).filter(UserSession.created_at < datetime.utcnow() - timedelta(days=30)).delete()
    except Exception:
        pass
    new_sess = UserSession(
        user_id=user.id,
        session_key=session_key,
        ip_address=ip,
        user_agent=user_agent_str[:250],
        device_type=device
    )
    db.session.add(new_sess)
    db.session.commit()

def build_obfuscated():
    print("Собираю защищенный фронтенд...")
    if not os.path.exists('static/css/styles.css') or not os.path.exists('templates/auth.html'):
        print("Исходники фронтенда не найдены, использую готовую сборку.")
        return
    os.makedirs('templates/build/partials', exist_ok=True)
    os.makedirs('static/build', exist_ok=True)
                                                                 
    IGNORE = {
        'init-black', 'smooth-scroll', 'side-nav-item', 'nav-label', 'nav-dot',
        'monotone-img', 'fade-in-up', 'active', 'badge',
        'header-blur-bg', 'word', 'statement-section', 'feature-card', 'glass-panel',
        'scroll-fade', 'ai-logos', 'ai-logo-img', 'price-card', 'faq-item',
        'faq-question', 'faq-answer', 'section-marker', 'smart-captcha', 'page-index',
        'oauth-btn', 'toggle-switch', 'toggle-slider',
        'dashboard-header', 'dh-left', 'dh-path', 'dh-right', 'dh-balance', 'dh-sub', 'dh-avatar', 'dashboard-content',
        'balance-add', 'profile-dropdown', 'profile-menu', 'show', 'logout-link', 'menu-divider',
        'profile-content', 'prof-card', 'prof-avatar-wrap', 'prof-avatar', 'prof-file-btn', 'btn-save', 'prof-msg', 'avatar-preview', 'avatar-input',
        'prof-container', 'prof-sidebar', 'prof-tab', 'prof-content-area', 'prof-panel', 'active', 'auth-logo',
        'settings-list', 'settings-item', 'settings-header', 'settings-title', 'settings-desc', 'settings-body', 'avatar-hover-container', 'avatar-overlay',
        'pay-method-card', 'course-cards-container', 'course-card-big', 'course-card-locked',
        'vel-balance-counter', 'vel-balance-static', 'vel-digit-slot', 'vel-digit-inner', 'vel-digit-col',
        'vel-digit-line', 'vel-digit-sep', 'vel-digit-suffix', 'models-category-grid', 'models-category-card',
        'models-category-icon', 'models-pinned-row', 'models-pinned-slot', 'models-pinned-empty',
        'models-view-back', 'model-card', 'model-card-auto', 'category-block', 'category-head', 'models-grid',
        'wallet-balance-big', 'model-price-tag', 'model-tokens-left', 'pinned-slot-name', 'pinned-slot-meta',
        'locked-plan', 'category-locked',
                                 
        'plans-grid', 'plan-card', 'plan-standart', 'plan-prime', 'plan-pro', 'current',
        'plan-badge', 'badge-free', 'badge-standart', 'badge-prime', 'badge-pro', 'badge-active',
        'plan-name', 'plan-price', 'plan-features', 'plan-btn', 'btn-standart', 'btn-prime', 'btn-pro', 'btn-active',
        'plan-days-left', 'feat-ok', 'feat-no', 'feat-star', 'feat-icon',
                                          
        'sub-banner', 'sub-banner-content', 'sub-banner-label', 'sub-banner-level',
        'sub-banner-features', 'sub-banner-overlay', 'sub-banner-icon', 'sub-days-chip',
                                    
        'org-grid', 'org-card', 'org-card-header', 'org-logo', 'org-logo-placeholder',
        'org-name', 'org-category', 'org-desc', 'org-footer', 'org-date', 'org-delete-btn',
        'org-add-card',
                             
        'modal-overlay', 'modal-box', 'modal-title', 'modal-close', 'open',
                        
        'input-group', 'btn-save', 'dh-balance', 'dh-sub',
    }
    classes = set()
    html_files = []
    for root, dirs, files in os.walk('templates'):
        if 'build' in root: continue
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
                                       
    import urllib.parse
    cache_dir = 'static/preloaded_cache-a'
    target_dir = 'static/build/preloaded'
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(target_dir, exist_ok=True)
    url_pattern = re.compile(r'https?://[^\s\"\'\>]+')
    external_urls = set()
               
    for filepath in html_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            for url in url_pattern.findall(content):
                url_lower = url.lower()
                if '${' in url or 'qrserver.com' in url_lower:
                    continue
                if any(ext in url_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']) or 'ui-avatars.com' in url_lower:
                    external_urls.add(url)
              
    if os.path.exists('static/css/styles.css'):
        with open('static/css/styles.css', 'r', encoding='utf-8') as f:
            css_content = f.read()
            for url in url_pattern.findall(css_content):
                url_lower = url.lower()
                if any(ext in url_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']):
                    external_urls.add(url)
    url_mapping = {}
    for url in sorted(external_urls):
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1]
        if not ext:
            if 'ui-avatars' in url:
                ext = '.png'
            else:
                ext = '.png'
        if ext.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico']:
            ext = '.png'
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        filename = f"{url_hash}{ext}"
        cache_path = os.path.join(cache_dir, filename)
        target_path = os.path.join(target_dir, filename)
        if not os.path.exists(cache_path):
            print(f"Загружаю внешний ресурс: {url}")
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    with open(cache_path, 'wb') as f:
                        f.write(r.content)
                    print(f"Успешно сохранено в кэш: {cache_path}")
                else:
                    print(f"Ошибка загрузки {url}: код {r.status_code}")
            except Exception as e:
                print(f"Не удалось скачать {url}: {e}")
        if os.path.exists(cache_path):
            import shutil
            shutil.copy(cache_path, target_path)
            url_mapping[url] = f"/static/build/preloaded/{filename}"
    class_pattern = re.compile(r'class=(["\'])(.*?)\1')
    valid_class = re.compile(r'^[a-zA-Z_-][a-zA-Z0-9_-]*$')
    jinja_split = re.compile(r'(\{%.*?%\}|\{\{.*?\}\}|\s+)')
    
    def get_classes_from_attr(attr_val):
        found = []
        for part in jinja_split.split(attr_val):
            if not part or part.isspace() or part.startswith('{%') or part.startswith('{{'):
                continue
            found.append(part)
        return found

    for filepath in html_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            for match in class_pattern.finditer(f.read()):
                for cls in get_classes_from_attr(match.group(2)):
                    if valid_class.match(cls) and cls not in IGNORE and not cls.startswith('ph'):
                        classes.add(cls)
    chars = string.ascii_lowercase + string.ascii_uppercase
    class_map = {}
    for i, cls in enumerate(sorted(classes)):
                                              
        short_name = "_" + "".join(chars[(i // (52**j)) % 52] for j in range((i // 52) + 1))
        class_map[cls] = short_name
    with open('static/css/styles.css', 'r', encoding='utf-8') as f:
        css = f.read()
    for orig, new in class_map.items():
        css = re.sub(r'\.' + re.escape(orig) + r'(?=[ \n\r\t\,\:\.\{\>])', '.' + new, css)
                                                             
    for ext_url, local_path in url_mapping.items():
        css = css.replace(ext_url, local_path)
                      
    css = re.sub(r'/\*.*?\*/', '', css)
    css = re.sub(r'\s+', ' ', css)
    with open('static/build/styles.css', 'w', encoding='utf-8') as f:
        f.write(css)
    os.makedirs('static/build/js', exist_ok=True)
    for js_file in ['bg.js', 'velocity-ui.js']:
        src_js = os.path.join('static/js', js_file)
        dest_js = os.path.join('static/build/js', js_file)
        if os.path.exists(src_js):
            with open(src_js, 'r', encoding='utf-8') as f:
                js_code = f.read()
            
            # We no longer embed CSS into JS
            import subprocess
            import time
            v = int(time.time())
            
            # Write js_code directly without obfuscation to avoid CloudFlare Auto Minify crash and speed up build
            with open(dest_js, 'w', encoding='utf-8') as f:
                f.write(js_code)
    for filepath in html_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        import time
        v = int(time.time())
        content = content.replace("filename='js/bg.js'", f"filename='build/js/bg.js', v={v}")
        content = content.replace('filename="js/bg.js"', f'filename="build/js/bg.js", v={v}')
        content = content.replace("filename='js/velocity-ui.js'", f"filename='build/js/velocity-ui.js', v={v}")
        content = content.replace('filename="js/velocity-ui.js"', f'filename="build/js/velocity-ui.js", v={v}')
        content = content.replace("filename='css/styles.css'", f"filename='build/styles.css', v={v}")
        content = content.replace('filename="css/styles.css"', f'filename="build/styles.css", v={v}')
                                                                                                
        script_blocks = []
        def script_stripper(match):
            script_blocks.append(match.group(0))
            return f"<!--SCRIPT_BLOCK_{len(script_blocks)-1}-->"
        temp_content = re.sub(r'<script\b[^>]*>.*?</script>', script_stripper, content, flags=re.DOTALL)
        def replacer(match):
            quote = match.group(1)
            val = match.group(2)
            parts = []
            for part in jinja_split.split(val):
                if not part:
                    continue
                if part.startswith('{%') or part.startswith('{{'):
                    parts.append(part)
                elif part.isspace():
                    parts.append(part)
                else:
                    parts.append(class_map.get(part, part))
            return f'class={quote}' + ''.join(parts) + f'{quote}'
        new_content = class_pattern.sub(replacer, temp_content)
                               
        for idx, block in enumerate(script_blocks):
            new_content = new_content.replace(f"<!--SCRIPT_BLOCK_{idx}-->", block)
                                                                  
        # We no longer strip styles.css since we removed anti-phishing logic
        for ext_url, local_path in url_mapping.items():
            new_content = new_content.replace(ext_url, local_path)
        
        # HTML Minifier and comment stripper
        new_content = re.sub(r'<!--(?!SCRIPT_BLOCK_)(.*?)-->', '', new_content, flags=re.DOTALL)
        def css_comment_stripper(m):
            s, b, e = m.groups()
            cleaned_b = re.sub(r'\/\*.*?\*\/', '', b, flags=re.DOTALL)
            return s + re.sub(r'\s+', ' ', cleaned_b) + e
        new_content = re.compile(r'(<style\b[^>]*>)(.*?)(</style>)', re.DOTALL).sub(css_comment_stripper, new_content)
        def js_comment_stripper(m):
            s, b, e = m.groups()
            if 'src=' not in s:
                cleaned_b = re.sub(r'(?<!:)\/\/[^\n]*', '', b)
                cleaned_b = re.sub(r'\/\*.*?\*\/', '', cleaned_b, flags=re.DOTALL)
                return s + re.sub(r'\s+', ' ', cleaned_b) + e
            return m.group(0)
        new_content = re.compile(r'(<script\b[^>]*>)(.*?)(</script>)', re.DOTALL).sub(js_comment_stripper, new_content)
        new_content = new_content.replace('\r', ' ').replace('\n', ' ')
        new_content = re.sub(r'\s+', ' ', new_content).strip()
        
        rel_path = os.path.relpath(filepath, 'templates')
        dest = os.path.join('templates/build', rel_path)
        with open(dest, 'w', encoding='utf-8') as f:
            f.write(new_content)
LAST_BUILD_TIME = 0
rebuild_lock = threading.Lock()

def get_latest_mtime():
    latest = 0
    if os.path.exists('static/css/styles.css'):
        latest = max(latest, os.path.getmtime('static/css/styles.css'))
    for root, _, files in os.walk('templates'):
        if 'build' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                latest = max(latest, os.path.getmtime(os.path.join(root, file)))
    return latest

# Инициализация сборки фронтенда при запуске приложения
try:
    build_obfuscated()
    LAST_BUILD_TIME = get_latest_mtime()
except Exception as e:
    print(f"Ошибка при автоматической сборке фронтенда при запуске: {e}")

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, template_folder='templates/build')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
              
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'velocity_super_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///velocity.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
             
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'mail.hosting.reg.ru')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False').lower() in ['true', '1', 't']
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'noreply@isvelocity.ru')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'nM6aT4jZ8xrJ1cH3')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@isvelocity.ru')
                 
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'
login_manager.login_message = "Пожалуйста, авторизуйтесь для доступа к этой странице."
login_manager.login_message_category = "error"
@login_manager.user_loader

def load_user(user_id):
    return db.session.get(User, int(user_id))
mail = Mail(app)
def get_client_ip():
    return request.headers.get('CF-Connecting-IP', request.headers.get('X-Forwarded-For', request.remote_addr)).split(',')[0].strip()

limiter = Limiter(
    get_client_ip,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
oauth = OAuth(app)
yandex = oauth.register(
    name='yandex',
    client_id=os.environ.get('YANDEX_CLIENT_ID'),
    client_secret=os.environ.get('YANDEX_CLIENT_SECRET'),
    authorize_url='https://oauth.yandex.ru/authorize',
    access_token_url='https://oauth.yandex.ru/token',
    api_base_url='https://login.yandex.ru/info',
    client_kwargs={'scope': 'login:info login:email'}
)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)
@app.before_request

def auto_rebuild():
    global LAST_BUILD_TIME
    current_latest = get_latest_mtime()
    if current_latest > LAST_BUILD_TIME:
        with rebuild_lock:
                                                                    
            if current_latest > LAST_BUILD_TIME:
                print("Файлы изменились. Пересобираю фронтенд...")
                build_obfuscated()
                LAST_BUILD_TIME = current_latest
                              
    if request.path.startswith('/static') or request.path == '/logout':
        return
    if current_user.is_authenticated:
        sk = session.get('session_key')
        if not sk:
            logout_user()
            return redirect(url_for('auth'))
        us = UserSession.query.filter_by(session_key=sk).first()
        if not us:
            logout_user()
            session.pop('session_key', None)
            flash("Сессия была завершена.", "error")
            return redirect(url_for('auth'))
        else:
            now = datetime.utcnow()
            if us.last_active is None or (now - us.last_active).total_seconds() > 60:
                us.last_active = now
                db.session.commit()
                                        
with app.app_context():
    db.create_all()
                                                  
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        if 'user' in inspector.get_table_names():
            user_cols = {c['name'] for c in inspector.get_columns('user')}
            migrations = []
            if 'bonus_balance' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN bonus_balance FLOAT DEFAULT 0.0")
            if 'defpay_authorized' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN defpay_authorized BOOLEAN DEFAULT 0")
            if 'pro_activated_at' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN pro_activated_at DATETIME")
            if 'api_access' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN api_access BOOLEAN DEFAULT 0")
            if 'selected_models' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN selected_models TEXT DEFAULT '{}'")
            if 'pinned_models' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN pinned_models TEXT DEFAULT '[null,null,null]'")
            if 'subscription_expires_at' not in user_cols:
                migrations.append("ALTER TABLE user ADD COLUMN subscription_expires_at DATETIME")
            for sql in migrations:
                db.session.execute(text(sql))
            if migrations:
                db.session.commit()
    except Exception as e:
        print(f"Миграция базы данных: {e}")
                                                                             
    current_latest = get_latest_mtime()
    if current_latest > LAST_BUILD_TIME:
        build_obfuscated()
        LAST_BUILD_TIME = current_latest
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        from ai_models import refresh_model_availability
        refresh_model_availability(sync=True)
        from payments import start_defpay_poller
        start_defpay_poller(app)
                                                                                
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
import gzip
import io

@app.after_request
def add_header(response):
    if 'static/' in request.path:
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
        response.cache_control.no_transform = True
        response.headers['Cache-Control'] += ', no-transform'
    return response
@app.context_processor

def inject_security():
    def get_anti_phishing_js():
        return ""
    return dict(
        anti_phishing=get_anti_phishing_js,
        YANDEX_CAPTCHA_CLIENT_KEY=os.environ.get('YANDEX_CAPTCHA_CLIENT_KEY', 'ysc1_iuWrKlKmg8h9p5oF2nxnboXBxT1ZqUoeZgXHIJgy83208734')
    )

def verify_smartcaptcha(token):
    secret = os.environ.get('YANDEX_CAPTCHA_SERVER_KEY', 'ysc2_iuWrKlKmg8h9p5oF2nxniRPIWDjrwr1Hx9WNqBc809cb7213')
    if not secret:
        return True
    if not token or not str(token).strip():
        return False
    try:
        resp = requests.post('https://smartcaptcha.yandexcloud.net/validate', data={
            'secret': secret,
            'token': token,
            'ip': get_client_ip()
        }, timeout=10)
        if resp.ok:
            return resp.json().get('status') == 'ok'
    except Exception as e:
        print(f'Ошибка проверки капчи: {e}')
    return False

@app.route('/api/login', methods=['POST'])
@limiter.limit('5 per minute')

def api_login():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    two_factor_code = data.get('two_factor_code')
    oauth_bypass = data.get('oauth_2fa_bypass', False)
    if not email or (not password and not oauth_bypass):
        return jsonify({'success': False, 'error': 'Missing credentials'})
    user = User.query.filter_by(email=email).first()
    if not user:
                                 
        additional = UserEmail.query.filter_by(email=email).first()
        if additional:
            user = User.query.get(additional.user_id)
    if user and (user.check_password(password) or oauth_bypass):
        if user.two_factor_enabled:
            if not two_factor_code:
                active_methods = [m.strip() for m in (user.two_factor_method or 'app').split(',') if m.strip()]
                code = str(random.randint(100000, 999999))
                session['pending_2fa_code'] = code
                session['pending_2fa_user_id'] = user.id
                session['pending_2fa_expiry'] = time.time() + 300
                if 'email' in active_methods:
                    html_content = generate_styled_email(
                        title="Вход в аккаунт",
                        message_body="Вы входите в свой личный кабинет. Пожалуйста, используйте следующий код для подтверждения входа:",
                        code=code
                    )
                    try:
                        msg = Message("Код подтверждения входа | VELOCITY", recipients=[user.email])
                        msg.html = html_content
                        mail.send(msg)
                        print(f"Код 2FA отправлен на почту {user.email}")
                    except Exception as e:
                        print(f"Не удалось отправить код 2FA на почту: {e}")
                if 'telegram' in active_methods and user.telegram_id:
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
                    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    try:
                        requests.post(tg_url, json={
                            'chat_id': user.telegram_id,
                            'text': f"🔐 Код подтверждения входа VELOCITY: {code}\nНикому не сообщайте этот код."
                        }, timeout=5)
                        print(f"Код 2FA отправлен в Телеграм {user.telegram_id}")
                    except Exception as e:
                        print(f"Не удалось отправить код 2FA в Телеграм: {e}")
                return jsonify({'success': False, 'require_2fa': True, 'method': user.two_factor_method})
                             
            active_methods = [m.strip() for m in (user.two_factor_method or 'app').split(',') if m.strip()]
            code_verified = False
            chosen_method = data.get('two_factor_method')
            if not chosen_method:
                chosen_method = active_methods[0] if active_methods else 'app'
            if chosen_method == 'app' and 'app' in active_methods and user.two_factor_secret:
                import pyotp
                totp = pyotp.TOTP(user.two_factor_secret)
                if totp.verify(two_factor_code, valid_window=1):
                    code_verified = True
            elif chosen_method in ['email', 'telegram'] and chosen_method in active_methods:
                pending_code = session.get('pending_2fa_code')
                pending_user = session.get('pending_2fa_user_id')
                pending_expiry = session.get('pending_2fa_expiry')
                if pending_code and pending_user == user.id and time.time() <= pending_expiry:
                    if pending_code == two_factor_code:
                        code_verified = True
                        session.pop('pending_2fa_code', None)
                        session.pop('pending_2fa_user_id', None)
                        session.pop('pending_2fa_expiry', None)
            if not code_verified:
                return jsonify({'success': False, 'error': 'Неверный код подтверждения'})
            login_user(user)
            create_user_session(user)
            return jsonify({'success': True})
        else:
            login_user(user)
            create_user_session(user)
            return jsonify({'success': True})
    if user:
        if user.auth_provider != 'local':
            return jsonify({'success': False, 'error': f'Этот аккаунт привязан к {user.auth_provider.capitalize()}. Пожалуйста, войдите через соцсеть.'})
        return jsonify({'success': False, 'error': 'Неверные учетные данные'})
    return jsonify({'success': False, 'error': 'Неверные учетные данные'})


@app.route('/api/login/send_2fa_code', methods=['POST'])
@limiter.limit('3 per minute')
def api_login_send_2fa_code():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    method = data.get('method')
    if not email or not password or not method:
        return jsonify({'success': False, 'error': 'Не заполнено имя пользователя, пароль или метод'})
    user = User.query.filter_by(email=email).first()
    if not user:
        additional = UserEmail.query.filter_by(email=email).first()
        if additional:
            user = User.query.get(additional.user_id)
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Неверные учетные данные'})
    if not user.two_factor_enabled:
        return jsonify({'success': False, 'error': '2FA не включена'})
    active_methods = [m.strip() for m in (user.two_factor_method or 'app').split(',') if m.strip()]
    if method not in active_methods:
        return jsonify({'success': False, 'error': 'Выбранный метод не активен'})
    if method not in ['email', 'telegram']:
        return jsonify({'success': False, 'error': 'Код для этого метода генерируется в приложении'})
    code = str(random.randint(100000, 999999))
    session['pending_2fa_code'] = code
    session['pending_2fa_user_id'] = user.id
    session['pending_2fa_expiry'] = time.time() + 300
    if method == 'email':
        html_content = generate_styled_email(
            title="Вход в аккаунт",
            message_body="Вы входите в свой личный кабинет. Пожалуйста, используйте следующий код для подтверждения входа:",
            code=code
        )
        try:
            msg = Message("Код подтверждения входа | VELOCITY", recipients=[user.email])
            msg.html = html_content
            mail.send(msg)
            return jsonify({'success': True, 'message': 'Код отправлен на почту'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Ошибка отправки: {e}'})
    elif method == 'telegram' and user.telegram_id:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
        tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            requests.post(tg_url, json={
                'chat_id': user.telegram_id,
                'text': f"🔐 Код подтверждения входа VELOCITY: {code}\nНикому не сообщайте этот код."
            }, timeout=5)
            return jsonify({'success': True, 'message': 'Код отправлен в Telegram'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Ошибка отправки: {e}'})
    return jsonify({'success': False, 'error': 'Не удалось отправить код'})


@app.route('/api/2fa/recovery/request', methods=['POST'])
@limiter.limit('3 per minute')
def api_2fa_recovery_request():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'success': False, 'error': 'Не заполнены email или пароль'})
    user = User.query.filter_by(email=email).first()
    if not user:
        additional = UserEmail.query.filter_by(email=email).first()
        if additional:
            user = User.query.get(additional.user_id)
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'})
    if not user.two_factor_enabled:
        return jsonify({'success': False, 'error': '2FA не включена'})
    
    code = str(random.randint(100000, 999999))
    session['pending_2fa_recovery_code'] = code
    session['pending_2fa_recovery_user_id'] = user.id
    session['pending_2fa_recovery_expiry'] = time.time() + 600
    
    html_content = generate_styled_email(
        title="Сброс двухфакторной аутентификации",
        message_body="Вы запросили сброс двухфакторной аутентификации (2FA) для вашего аккаунта VELOCITY. Используйте следующий код для отключения 2FA:",
        code=code
    )
    try:
        msg = Message("Восстановление доступа 2FA | VELOCITY", recipients=[user.email])
        msg.html = html_content
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Код сброса отправлен на вашу почту'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка отправки: {e}'})


@app.route('/api/2fa/recovery/verify', methods=['POST'])
def api_2fa_recovery_verify():
    data = request.json or {}
    code = data.get('code')
    pending_code = session.get('pending_2fa_recovery_code')
    pending_user_id = session.get('pending_2fa_recovery_user_id')
    pending_expiry = session.get('pending_2fa_recovery_expiry')
    if not pending_code or not pending_user_id or not pending_expiry or time.time() > pending_expiry:
        return jsonify({'success': False, 'error': 'Срок действия кода истек или запрос не найден'})
    if code == pending_code:
        user = db.session.get(User, pending_user_id)
        if user:
            user.two_factor_enabled = False
            user.two_factor_secret = None
            user.two_factor_method = 'app'
            db.session.commit()
            session.pop('pending_2fa_recovery_code', None)
            session.pop('pending_2fa_recovery_user_id', None)
            session.pop('pending_2fa_recovery_expiry', None)
            return jsonify({'success': True, 'message': '2FA успешно отключена. Теперь вы можете войти по паролю.'})
    return jsonify({'success': False, 'error': 'Неверный код сброса'})


reset_tokens = {}

@app.route('/reset_password', methods=['GET', 'POST'])
@limiter.limit('3 per minute')

def reset_password():
    if request.method == 'POST':
        captcha_token = request.form.get('smart-token')
        if not verify_smartcaptcha(captcha_token):
            flash("Пожалуйста, подтвердите капчу", "error")
            return redirect(url_for('reset_password'))
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            import uuid
            token = str(uuid.uuid4())
            reset_tokens[token] = user.id
            reset_link = url_for('reset_password_token', token=token, _external=True)
            try:
                import socket
                socket.setdefaulttimeout(15.0)
                html_content = generate_styled_email(
                    title="Сброс пароля",
                    message_body="Здравствуйте! Для сброса пароля от вашего аккаунта перейдите по ссылке ниже. Ссылка активна в течение одного часа.",
                    action_text="СБРОСИТЬ ПАРОЛЬ",
                    action_url=reset_link
                )
                msg = Message(
                    "Сброс пароля | VELOCITY",
                    recipients=[email]
                )
                msg.html = html_content
                mail.send(msg)
                print(f"Письмо отправлено на {email}")
                flash("Инструкции по сбросу пароля отправлены на ваш email", "success")
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")
                flash(f"Ошибка отправки письма: {e}", "error")
        else:
                                                                                         
            flash("Инструкции по сбросу пароля отправлены на ваш email", "success")
        return redirect(url_for('reset_password'))
    return render_template('reset_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])

def reset_password_token(token):
    if token not in reset_tokens:
        flash("Ссылка для сброса недействительна или устарела", "error")
        return redirect(url_for('reset_password'))
    if request.method == 'POST':
        password = request.form.get('password')
        if len(password) < 8:
            flash("Пароль должен содержать минимум 8 символов", "error")
            return render_template('reset_password_token.html', token=token)
        user = db.session.get(User, reset_tokens[token])
        if user:
            user.set_password(password)
            db.session.commit()
            del reset_tokens[token]
            flash("Пароль успешно изменен! Теперь вы можете войти.", "success")
            return redirect(url_for('auth'))
    return render_template('reset_password_token.html', token=token)
registration_codes = {}

@app.route('/api/register/send_code', methods=['POST'])
@limiter.limit('3 per minute')

def api_register_send_code():
    email = request.json.get('email')
    captcha_token = request.json.get('captcha_token')
    if not email:
        return jsonify({'success': False, 'error': 'Укажите email'})
    if not verify_smartcaptcha(captcha_token):
        return jsonify({'success': False, 'error': 'Подтвердите капчу'})
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        if existing_user.auth_provider != 'local':
            return jsonify({'success': False, 'error': f'Этот email привязан к {existing_user.auth_provider.capitalize()}.'})
        return jsonify({'success': False, 'error': 'Почта уже зарегистрирована'})
    code = str(random.randint(100000, 999999))
    registration_codes[email] = code
    try:
        import socket
        socket.setdefaulttimeout(15.0)
        html_content = generate_styled_email(
            title="Регистрация аккаунта",
            message_body="Спасибо за регистрацию в VELOCITY! Используйте следующий код подтверждения для завершения регистрации. Никому не сообщайте этот код.",
            code=code
        )
        msg = Message("Код подтверждения VELOCITY", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.html = html_content
        mail.send(msg)
        print(f"Код подтверждения отправлен. Код: {code}")
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")
        return jsonify({'success': False, 'error': f'Ошибка отправки письма: {e}'})
    return jsonify({'success': True})

@app.route('/api/register', methods=['POST'])
@limiter.limit('5 per minute')

def api_register():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    code = data.get('code')
    token = data.get('captcha_token')
    if not email or not password or not code:
        return jsonify({'success': False, 'error': 'Не все данные заполнены'})
    if registration_codes.get(email) != code:
        return jsonify({'success': False, 'error': 'Неверный или устаревший код подтверждения'})
    if token and not verify_smartcaptcha(token):
        return jsonify({'success': False, 'error': 'Invalid captcha'})
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        if existing_user.auth_provider != 'local':
            return jsonify({'success': False, 'error': f'Этот email привязан к {existing_user.auth_provider.capitalize()}. Пожалуйста, войдите через соцсеть.'})
        return jsonify({'success': False, 'error': 'Почта уже зарегистрирована'})
    if len(password) < 8:
        return jsonify({'success': False, 'error': 'Пароль должен содержать минимум 8 символов'})
    if username and User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'error': 'Username already taken'})
    new_user = User(username=username, email=email, first_name=first_name, last_name=last_name)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    create_user_session(new_user)
    return jsonify({'success': True})

@app.route('/lk')

@app.route('/lk/')
@login_required

def lk_redirect():
    return redirect(url_for('dashboard'))

@app.route('/lk/dashboard')
@login_required

def dashboard():
    return render_template('dashboard.html')

@app.route('/lk/profile')
@login_required

def profile():
    return render_template('profile.html')

@app.route('/api/profile/update', methods=['POST'])
@login_required

def update_profile():
    import base64
    username = request.form.get('username') or None
    first_name = request.form.get('first_name') or None
    last_name = request.form.get('last_name') or None
    email = request.form.get('email')
    reset_avatar = request.form.get('reset_avatar')
    if reset_avatar == 'true':
        current_user.avatar = current_user.original_avatar
        db.session.commit()
        return jsonify({'success': True})
    if username and username != current_user.username:
        existing = User.query.filter_by(username=username).first()
        if existing:
            return jsonify({'success': False, 'error': 'Юзернейм занят'})
        current_user.username = username
    elif not username and current_user.username:
        current_user.username = None
    current_user.first_name = first_name
    current_user.last_name = last_name
    if email and email != current_user.email and current_user.auth_provider == 'local':
        existing = User.query.filter_by(email=email).first()
        if existing:
            return jsonify({'success': False, 'error': 'Email уже занят'})
        current_user.email = email
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file.filename != '':
            image_b64 = base64.b64encode(file.read()).decode('utf-8')
            imgbb_key = '7f6e7f3eefae0359d4c6237ec614ef00'
            resp = requests.post(
                f"https://api.imgbb.com/1/upload?key={imgbb_key}",
                data={'image': image_b64}
            )
            if resp.ok:
                res_data = resp.json()
                if res_data.get('success'):
                    current_user.avatar = res_data['data']['url']
            else:
                return jsonify({'success': False, 'error': 'Ошибка загрузки аватара'})
    db.session.commit()
    return jsonify({'success': True, 'avatar_url': current_user.avatar})

@app.route('/api/2fa/generate', methods=['POST'])
@login_required

def generate_2fa():
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    db.session.commit()
    totp = pyotp.TOTP(secret)
    url = totp.provisioning_uri(name=current_user.email, issuer_name="VELOCITY")
    return jsonify({'success': True, 'secret': secret, 'url': url})

@app.route('/api/2fa/enable', methods=['POST'])
@login_required

def enable_2fa():
    code = request.json.get('code')
    if not current_user.two_factor_secret:
        return jsonify({'success': False, 'error': 'Секрет не сгенерирован'})
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if totp.verify(code):
        active_methods = [m.strip() for m in (current_user.two_factor_method or '').split(',') if m.strip()]
        if 'app' not in active_methods:
            active_methods.append('app')
        current_user.two_factor_method = ','.join(active_methods)
        current_user.two_factor_enabled = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Неверный код'})

@app.route('/api/2fa/disable', methods=['POST'])
@login_required

def disable_2fa():
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.two_factor_method = ''
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/2fa/disable_method', methods=['POST'])
@login_required

def disable_2fa_method():
    method = request.json.get('method')
    if not method or method not in ['app', 'email', 'telegram']:
        return jsonify({'success': False, 'error': 'Некорректный метод'})
    active_methods = [m.strip() for m in (current_user.two_factor_method or '').split(',') if m.strip()]
    if method in active_methods:
        active_methods.remove(method)
    if not active_methods:
        current_user.two_factor_enabled = False
        current_user.two_factor_method = ''
    else:
        current_user.two_factor_method = ','.join(active_methods)
    if method == 'app':
        current_user.two_factor_secret = None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/2fa/enable_email', methods=['POST'])
@login_required

def enable_email_2fa():
    code = str(random.randint(100000, 999999))
    session['email_2fa_setup_code'] = code
    session['email_2fa_setup_expiry'] = time.time() + 300
    html_content = generate_styled_email(
        title="Настройка 2FA по почте",
        message_body="Вы настраиваете двухфакторную аутентификацию по электронной почте. Пожалуйста, используйте следующий проверочный код:",
        code=code
    )
    try:
        msg = Message("Код настройки 2FA | VELOCITY", recipients=[current_user.email])
        msg.html = html_content
        mail.send(msg)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка отправки: {e}'})

@app.route('/api/2fa/verify_email', methods=['POST'])
@login_required

def verify_email_2fa():
    code = request.json.get('code')
    setup_code = session.get('email_2fa_setup_code')
    setup_expiry = session.get('email_2fa_setup_expiry')
    if not setup_code or not setup_expiry or time.time() > setup_expiry:
        return jsonify({'success': False, 'error': 'Срок действия кода истек'})
    if code == setup_code:
        active_methods = [m.strip() for m in (current_user.two_factor_method or '').split(',') if m.strip()]
        if 'email' not in active_methods:
            active_methods.append('email')
        current_user.two_factor_method = ','.join(active_methods)
        current_user.two_factor_enabled = True
        db.session.commit()
        session.pop('email_2fa_setup_code', None)
        session.pop('email_2fa_setup_expiry', None)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Неверный код'})

@app.route('/api/2fa/enable_telegram', methods=['POST'])
@login_required

def enable_telegram_2fa():
    if not current_user.telegram_id:
        return jsonify({'success': False, 'error': 'Сначала привяжите Telegram в разделе социальных сетей'})
    code = str(random.randint(100000, 999999))
    session['telegram_2fa_setup_code'] = code
    session['telegram_2fa_setup_expiry'] = time.time() + 300
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(tg_url, json={
            'chat_id': current_user.telegram_id,
            'text': f"🔐 Код для включения Telegram 2FA: {code}\nНикому не передавайте этот код."
        }, timeout=5)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка отправки: {e}'})

@app.route('/api/2fa/verify_telegram', methods=['POST'])
@login_required

def verify_telegram_2fa():
    code = request.json.get('code')
    setup_code = session.get('telegram_2fa_setup_code')
    setup_expiry = session.get('telegram_2fa_setup_expiry')
    if not setup_code or not setup_expiry or time.time() > setup_expiry:
        return jsonify({'success': False, 'error': 'Срок действия кода истек'})
    if code == setup_code:
        active_methods = [m.strip() for m in (current_user.two_factor_method or '').split(',') if m.strip()]
        if 'telegram' not in active_methods:
            active_methods.append('telegram')
        current_user.two_factor_method = ','.join(active_methods)
        current_user.two_factor_enabled = True
        db.session.commit()
        session.pop('telegram_2fa_setup_code', None)
        session.pop('telegram_2fa_setup_expiry', None)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Неверный код'})

@app.route('/api/2fa/method', methods=['POST'])
@login_required

def change_2fa_method():
    method = request.json.get('method')
    if method not in ['app', 'email', 'telegram']:
        return jsonify({'success': False, 'error': 'Неверный метод 2FA'})
    if method == 'telegram' and not current_user.telegram_id:
        return jsonify({'success': False, 'error': 'Сначала привяжите Telegram в разделе социальных сетей'})
    current_user.two_factor_method = method
    db.session.commit()
    return jsonify({'success': True})

@app.route('/auth/telegram')

def auth_telegram():
    callback_url = url_for('telegram_callback', _external=True)
    import urllib.parse
    encoded_callback = urllib.parse.quote(callback_url)
    return redirect(f'https://api.isvelocity.ru/v1/oauth/tg/index.php?return_to={encoded_callback}')

@app.route('/oauth/telegram/callback')

def telegram_callback():
    data = request.args.to_dict()
    if 'hash' not in data:
        return "No hash provided", 400
    check_hash = data.pop('hash')
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hash_calc = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if hash_calc != check_hash:
        return "Invalid signature", 403
    if time.time() - int(data.get('auth_date', 0)) > 86400:
        return "Data outdated", 403
    tg_id = str(data.get('id'))
    username = data.get('username') or None
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = f"{tg_id}@telegram.local"
    photo_url = data.get('photo_url')
    if current_user.is_authenticated:
        existing = User.query.filter_by(telegram_id=tg_id).first()
        if existing and existing.id != current_user.id:
            flash("Этот Telegram аккаунт уже привязан к другому пользователю.", "error")
            return redirect(url_for('profile') + '?tab=security')
        current_user.telegram_id = tg_id
        db.session.commit()
        flash("Telegram аккаунт успешно привязан.", "success")
        return redirect(url_for('profile') + '?tab=security')
    user = User.query.filter_by(telegram_id=tg_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.telegram_id = tg_id
        else:
            user = User(username=username, first_name=first_name, last_name=last_name, email=email, auth_provider='telegram', telegram_id=tg_id)
            user.set_password(os.urandom(24).hex())
            user.avatar = photo_url
            user.original_avatar = photo_url
            db.session.add(user)
    else:
        if photo_url and not user.original_avatar:
            user.original_avatar = photo_url
        if photo_url and not user.avatar:
            user.avatar = photo_url
    db.session.commit()
    if user.two_factor_enabled:
        session['pending_2fa_user'] = user.id
        method = user.two_factor_method or 'app'
        if method in ['email', 'telegram']:
            code = str(random.randint(100000, 999999))
            session['pending_2fa_code'] = code
            session['pending_2fa_user_id'] = user.id
            session['pending_2fa_expiry'] = time.time() + 300
            if method == 'email':
                html_content = generate_styled_email(
                    title="Вход в аккаунт",
                    message_body="Вы входите в свой личный кабинет через Telegram. Пожалуйста, используйте следующий код для подтверждения входа:",
                    code=code
                )
                try:
                    msg = Message("Код подтверждения входа | VELOCITY", recipients=[user.email])
                    msg.html = html_content
                    mail.send(msg)
                except Exception as e:
                    print("Не удалось отправить код 2FA на почту:", e)
            elif method == 'telegram' and user.telegram_id:
                bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
                tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                try:
                    requests.post(tg_url, json={
                        'chat_id': user.telegram_id,
                        'text': f"🔐 Код подтверждения входа VELOCITY (OAuth): {code}\nНикому не сообщайте этот код."
                    }, timeout=5)
                except Exception as e:
                    print("Не удалось отправить код 2FA в Телеграм:", e)
        return render_template('auth.html', require_oauth_2fa=True, oauth_email=user.email, oauth_2fa_method=method)
    login_user(user)
    create_user_session(user)
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required

def logout():
    sk = session.get('session_key')
    if sk:
        UserSession.query.filter_by(session_key=sk).delete()
        db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@app.route('/')

def index():
    return render_template('index.html')

@app.route('/auth')

def auth():
    return render_template('auth.html')

@app.route('/offer')

def offer():
    return render_template('offer.html')

@app.route('/privacy')

def privacy():
    return render_template('privacy.html')

@app.route('/agreement')

def agreement():
    return render_template('agreement.html')

@app.route('/terms')

def terms():
    return render_template('offer.html')

@app.route('/docs')

def docs():
    return render_template('docs.html')


@app.route('/docs/api')
def api_docs():
    return render_template('api_docs.html')

@app.route('/oauth/yandex')

def yandex_login():
    redirect_uri = url_for('yandex_authorize', _external=True)
    return yandex.authorize_redirect(redirect_uri)

@app.route('/oauth/yandex/authorize')

def yandex_authorize():
    try:
        token = yandex.authorize_access_token()
        resp = yandex.get('info')
        user_info = resp.json()
        email = user_info.get('default_email') or user_info.get('emails', [''])[0]
        username = user_info.get('login') or None
        first_name = user_info.get('first_name')
        last_name = user_info.get('last_name')
        avatar_id = user_info.get('default_avatar_id')
        photo_url = f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200" if avatar_id else None
        yandex_id = str(user_info.get('id'))
        if current_user.is_authenticated:
            existing = User.query.filter_by(yandex_id=yandex_id).first()
            if existing and existing.id != current_user.id:
                flash("Этот Yandex аккаунт уже привязан к другому пользователю.", "error")
                return redirect(url_for('profile') + '?tab=security')
            current_user.yandex_id = yandex_id
            db.session.commit()
            flash("Yandex аккаунт успешно привязан.", "success")
            return redirect(url_for('profile') + '?tab=security')
        user = User.query.filter_by(yandex_id=yandex_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.yandex_id = yandex_id
            else:
                user = User(username=username, first_name=first_name, last_name=last_name, email=email, auth_provider='yandex', yandex_id=yandex_id)
                user.set_password(os.urandom(24).hex())
                user.avatar = photo_url
                user.original_avatar = photo_url
                db.session.add(user)
        else:
            if photo_url and not user.original_avatar:
                user.original_avatar = photo_url
            if photo_url and not user.avatar:
                user.avatar = photo_url
        db.session.commit()
        if user.two_factor_enabled:
            session['pending_2fa_user'] = user.id
            method = user.two_factor_method or 'app'
            if method in ['email', 'telegram']:
                code = str(random.randint(100000, 999999))
                session['pending_2fa_code'] = code
                session['pending_2fa_user_id'] = user.id
                session['pending_2fa_expiry'] = time.time() + 300
                if method == 'email':
                    html_content = generate_styled_email(
                        title="Вход в аккаунт",
                        message_body="Вы входите в свой личный кабинет через Yandex. Пожалуйста, используйте следующий код для подтверждения входа:",
                        code=code
                    )
                    try:
                        msg = Message("Код подтверждения входа | VELOCITY", recipients=[user.email])
                        msg.html = html_content
                        mail.send(msg)
                    except Exception as e:
                        print("Не удалось отправить код 2FA на почту:", e)
                elif method == 'telegram' and user.telegram_id:
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
                    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    try:
                        requests.post(tg_url, json={
                            'chat_id': user.telegram_id,
                            'text': f"🔐 Код подтверждения входа VELOCITY (OAuth): {code}\nНикому не сообщайте этот код."
                        }, timeout=5)
                    except Exception as e:
                        print("Не удалось отправить код 2FA в Телеграм:", e)
            return render_template('auth.html', require_oauth_2fa=True, oauth_email=user.email, oauth_2fa_method=method)
        login_user(user)
        create_user_session(user)
        return redirect(url_for('dashboard'))
    except Exception as e:
        print("Ошибка авторизации через Яндекс:", e)
        return redirect(url_for('auth'))

@app.route('/oauth/google')

def google_login():
    redirect_uri = url_for('google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/oauth/google/authorize')

def google_authorize():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
            user_info = resp.json()
        email = user_info.get('email')
        first_name = user_info.get('given_name')
        last_name = user_info.get('family_name')
        username = None
        photo_url = user_info.get('picture')
        google_id = str(user_info.get('sub') or user_info.get('id'))
        if current_user.is_authenticated:
            existing = User.query.filter_by(google_id=google_id).first()
            if existing and existing.id != current_user.id:
                flash("Этот Google аккаунт уже привязан к другому пользователю.", "error")
                return redirect(url_for('profile') + '?tab=security')
            current_user.google_id = google_id
            db.session.commit()
            flash("Google аккаунт успешно привязан.", "success")
            return redirect(url_for('profile') + '?tab=security')
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()
            if user:
                user.google_id = google_id
            else:
                user = User(username=username, first_name=first_name, last_name=last_name, email=email, auth_provider='google', google_id=google_id)
                user.set_password(os.urandom(24).hex())
                user.avatar = photo_url
                user.original_avatar = photo_url
                db.session.add(user)
        else:
            if photo_url and not user.original_avatar:
                user.original_avatar = photo_url
            if photo_url and not user.avatar:
                user.avatar = photo_url
        db.session.commit()
        if user.two_factor_enabled:
            session['pending_2fa_user'] = user.id
            method = user.two_factor_method or 'app'
            if method in ['email', 'telegram']:
                code = str(random.randint(100000, 999999))
                session['pending_2fa_code'] = code
                session['pending_2fa_user_id'] = user.id
                session['pending_2fa_expiry'] = time.time() + 300
                if method == 'email':
                    html_content = generate_styled_email(
                        title="Вход в аккаунт",
                        message_body="Вы входите в свой личный кабинет через Google. Пожалуйста, используйте следующий код для подтверждения входа:",
                        code=code
                    )
                    try:
                        msg = Message("Код подтверждения входа | VELOCITY", recipients=[user.email])
                        msg.html = html_content
                        mail.send(msg)
                    except Exception as e:
                        print("Не удалось отправить код 2FA на почту:", e)
                elif method == 'telegram' and user.telegram_id:
                    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8775472698:AAFwacDm-zZzKLECstRBu091NUCC7uxZZBs')
                    tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    try:
                        requests.post(tg_url, json={
                            'chat_id': user.telegram_id,
                            'text': f"🔐 Код подтверждения входа VELOCITY (OAuth): {code}\nНикому не сообщайте этот код."
                        }, timeout=5)
                    except Exception as e:
                        print("Не удалось отправить код 2FA в Телеграм:", e)
            return render_template('auth.html', require_oauth_2fa=True, oauth_email=user.email, oauth_2fa_method=method)
        login_user(user)
        create_user_session(user)
        return redirect(url_for('dashboard'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Ошибка авторизации через Google:", e)
        return redirect(url_for('auth'))

@app.route('/api/sessions', methods=['GET'])
@login_required

def get_sessions():
    sessions_list = UserSession.query.filter_by(user_id=current_user.id).order_by(UserSession.last_active.desc()).all()
    current_key = session.get('session_key')
    res = []
    for s in sessions_list:
        res.append({
            'id': s.id,
            'device_type': s.device_type,
            'ip_address': s.ip_address,
            'last_active': s.last_active.strftime('%d.%m.%Y %H:%M') if s.last_active else 'Неизвестно',
            'is_current': s.session_key == current_key
        })
    return jsonify({'success': True, 'sessions': res})

@app.route('/api/sessions/terminate', methods=['POST'])
@login_required

def terminate_session():
    sess_id = request.json.get('session_id')
    sess = UserSession.query.filter_by(user_id=current_user.id, id=sess_id).first()
    if not sess:
        return jsonify({'success': False, 'error': 'Сессия не найдена'})
    current_key = session.get('session_key')
    is_current = sess.session_key == current_key
    db.session.delete(sess)
    db.session.commit()
    if is_current:
        logout_user()
        session.pop('session_key', None)
        return jsonify({'success': True, 'logged_out': True})
    return jsonify({'success': True, 'logged_out': False})

@app.route('/api/oauth/unlink/<provider>', methods=['POST'])
@login_required

def unlink_oauth(provider):
    if provider not in ['google', 'yandex', 'telegram']:
        return jsonify({'success': False, 'error': 'Неизвестный провайдер'})
    has_password = current_user.password_hash is not None
    passkeys = UserPasskey.query.filter_by(user_id=current_user.id).all()
    linked_count = 0
    if current_user.google_id: linked_count += 1
    if current_user.yandex_id: linked_count += 1
    if current_user.telegram_id: linked_count += 1
    if not has_password and len(passkeys) == 0 and linked_count <= 1:
        return jsonify({'success': False, 'error': 'Нельзя отключить единственный способ входа. Установите пароль или добавьте Passkey.'})
    if provider == 'google':
        current_user.google_id = None
    elif provider == 'yandex':
        current_user.yandex_id = None
    elif provider == 'telegram':
        current_user.telegram_id = None
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/profile/delete', methods=['POST'])
@login_required

def delete_account():
    user_id = current_user.id
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Пользователь не найден'})
    UserSession.query.filter_by(user_id=user_id).delete()
    UserEmail.query.filter_by(user_id=user_id).delete()
    UserPasskey.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    logout_user()
    session.clear()
    return jsonify({'success': True})

@app.route('/api/profile/emails', methods=['GET'])
@login_required

def get_emails():
    emails = UserEmail.query.filter_by(user_id=current_user.id).all()
    res = [{'id': e.id, 'email': e.email, 'is_verified': e.is_verified} for e in emails]
    return jsonify({'success': True, 'emails': res})

@app.route('/api/profile/emails/add', methods=['POST'])
@login_required

def add_email():
    email = request.json.get('email', '').strip().lower()
    if not email:
        return jsonify({'success': False, 'error': 'Почта не может быть пустой'})
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({'success': False, 'error': 'Некорректный формат почты'})
    existing_count = UserEmail.query.filter_by(user_id=current_user.id).count()
    if existing_count >= 3:
        return jsonify({'success': False, 'error': 'Вы можете добавить максимум 3 дополнительные почты'})
    if email == current_user.email:
        return jsonify({'success': False, 'error': 'Эта почта уже привязана как основная'})
    exists_primary = User.query.filter_by(email=email).first()
    exists_secondary = UserEmail.query.filter_by(email=email).first()
    if exists_primary or exists_secondary:
        return jsonify({'success': False, 'error': 'Почта уже используется'})
    new_email = UserEmail(user_id=current_user.id, email=email, is_verified=True)
    db.session.add(new_email)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/profile/emails/delete', methods=['POST'])
@login_required

def delete_email():
    email_id = request.json.get('email_id')
    email_record = UserEmail.query.filter_by(user_id=current_user.id, id=email_id).first()
    if not email_record:
        return jsonify({'success': False, 'error': 'Почта не найдена'})
    db.session.delete(email_record)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/webauthn/register/options', methods=['POST'])
@login_required

def webauthn_register_options():
    challenge = os.urandom(32).hex()
    session['webauthn_register_challenge'] = challenge
    return jsonify({
        'success': True,
        'challenge': challenge,
        'user': {
            'id': current_user.id,
            'name': current_user.email,
            'displayName': current_user.display_name
        }
    })

@app.route('/api/webauthn/register/verify', methods=['POST'])
@login_required

def webauthn_register_verify():
    data = request.json or {}
    credential_id = data.get('credential_id')
    public_key = data.get('public_key', 'mock_public_key')
    if not credential_id:
        return jsonify({'success': False, 'error': 'Отсутствует ID ключа'})
    existing = UserPasskey.query.filter_by(credential_id=credential_id).first()
    if existing:
        return jsonify({'success': False, 'error': 'Этот ключ уже зарегистрирован'})
    pk = UserPasskey(
        user_id=current_user.id,
        credential_id=credential_id,
        public_key=public_key
    )
    db.session.add(pk)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/webauthn/login/options', methods=['POST'])

def webauthn_login_options():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        additional = UserEmail.query.filter_by(email=email).first()
        if additional:
            user = User.query.get(additional.user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Пользователь не найден'})
    challenge = os.urandom(32).hex()
    session['webauthn_login_challenge'] = challenge
    session['webauthn_login_user_id'] = user.id
    keys = UserPasskey.query.filter_by(user_id=user.id).all()
    allowed_credentials = [k.credential_id for k in keys]
    return jsonify({
        'success': True,
        'challenge': challenge,
        'allowed_credentials': allowed_credentials
    })

@app.route('/api/webauthn/login/verify', methods=['POST'])

def webauthn_login_verify():
    data = request.json or {}
    credential_id = data.get('credential_id')
    user_id = session.get('webauthn_login_user_id')
    if not credential_id or not user_id:
        return jsonify({'success': False, 'error': 'Ошибка сессии авторизации'})
    pk = UserPasskey.query.filter_by(user_id=user_id, credential_id=credential_id).first()
    if not pk:
        return jsonify({'success': False, 'error': 'Неверный электронный ключ'})
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'Пользователь не найден'})
    login_user(user)
    create_user_session(user)
    session.pop('webauthn_login_challenge', None)
    session.pop('webauthn_login_user_id', None)
    return jsonify({'success': True})


                  

@app.route('/api/payments/create', methods=['POST'])
@login_required
def create_payment():
    from payments import (
        create_yookassa_payment, create_cryptobot_invoice, create_stars_invoice,
        get_payment_amount, get_plan_topup_amount, DEFPAY_BOT_LINK, PLAN_PRICES,
        get_plan_price
    )
    data = request.json or {}
    method = data.get('method', 'yookassa')
    payment_type = data.get('payment_type', 'topup')
    duration_days = int(data.get('duration_days', 30))
    if duration_days not in (30, 90, 180, 365):
        duration_days = 30

    if payment_type == 'start':
        return jsonify({'success': False, 'error': 'Стартовый тариф бесплатный'})

    if payment_type in PLAN_PRICES:
        plan_price = get_plan_price(payment_type, duration_days)
        topup_needed = get_plan_topup_amount(current_user, payment_type, duration_days)
        if payment_type == 'pro' and (current_user.subscription_level or '').lower() == 'pro':
            return jsonify({'success': False, 'error': 'Тариф PRO уже активен'})
        if payment_type == 'api' and current_user.api_access:
            return jsonify({'success': False, 'error': 'Доступ к API уже куплен'})
        if topup_needed <= 0:
            return jsonify({
                'success': False,
                'error': 'balance_covers_plan',
                'plan_price': plan_price,
                'balance': current_user.balance or 0,
            })
        amount = float(data.get('amount', 0))
        if abs(amount - topup_needed) > 0.51:
            return jsonify({
                'success': False,
                'error': f'Пополните баланс на {topup_needed:.0f} ₽ (стоимость тарифа {plan_price:.0f} ₽ минус ваш баланс)'
            })
    elif payment_type == 'topup':
        amount = float(data.get('amount', 0))
        if amount < 15 or amount > 100000:
            return jsonify({'success': False, 'error': 'Сумма должна быть от 15 до 100 000 ₽'})
    else:
        return jsonify({'success': False, 'error': 'Неизвестный тип оплаты'})

    return_url = url_for('payment_return', _external=True)

    try:
        if method == 'yookassa':
            payment = create_yookassa_payment(current_user, amount, return_url, payment_type, duration_days=duration_days)
        elif method == 'crypto':
            payment = create_cryptobot_invoice(current_user, amount, return_url, payment_type, duration_days=duration_days)
        elif method == 'stars':
            if not current_user.telegram_id:
                return jsonify({
                    'success': False,
                    'error': 'telegram_required',
                    'message': 'Привяжите Telegram в разделе «Безопасность»'
                })
            if not current_user.defpay_authorized:
                return jsonify({
                    'success': False,
                    'error': 'defpay_not_authorized',
                    'auth_url': DEFPAY_BOT_LINK,
                    'qr_url': f'https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={DEFPAY_BOT_LINK}'
                })
            payment = create_stars_invoice(current_user, amount, payment_type, duration_days=duration_days)
        else:
            return jsonify({'success': False, 'error': 'Недоступный способ оплаты'})
    except RuntimeError as e:
        err = str(e)
        if err == 'defpay_not_authorized':
            return jsonify({
                'success': False,
                'error': 'defpay_not_authorized',
                'auth_url': DEFPAY_BOT_LINK,
                'qr_url': f'https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={DEFPAY_BOT_LINK}'
            })
        return jsonify({'success': False, 'error': err})
    except Exception as e:
        print(f"Ошибка создания платежа: {e}")
        return jsonify({'success': False, 'error': 'Ошибка создания платежа. Попробуйте позже.'})

    qr_url = None
    if payment.payment_url:
        import urllib.parse
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(payment.payment_url, safe='')}"

    return jsonify({
        'success': True,
        'payment_id': payment.id,
        'payment_url': payment.payment_url,
        'qr_url': qr_url,
        'amount': payment.amount,
        'method': payment.method,
        'payment_type': payment.payment_type
    })


@app.route('/api/payments/status/<int:payment_id>')
@login_required
def payment_status(payment_id):
    from payments import check_yookassa_status, check_cryptobot_status
    payment = Payment.query.filter_by(id=payment_id, user_id=current_user.id).first()
    if not payment:
        return jsonify({'success': False, 'error': 'Платёж не найден'})
    if payment.status == 'pending':
        if payment.method == 'yookassa':
            check_yookassa_status(payment)
        elif payment.method == 'crypto':
            check_cryptobot_status(payment)
    db.session.refresh(current_user)
    return jsonify({
        'success': True,
        'status': payment.status,
        'balance': current_user.balance,
        'bonus_balance': current_user.bonus_balance,
        'subscription_level': current_user.subscription_level,
        'api_access': current_user.api_access
    })


@app.route('/api/payments/defpay/auth-status')
@login_required
def defpay_auth_status():
    from payments import DEFPAY_BOT_LINK
    return jsonify({
        'success': True,
        'telegram_linked': bool(current_user.telegram_id),
        'defpay_authorized': bool(current_user.defpay_authorized),
        'auth_url': DEFPAY_BOT_LINK
    })


@app.route('/api/payments/history')
@login_required
def payment_history():
    txs = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.created_at.desc()).limit(50).all()
    items = [{
        'id': t.id,
        'type': t.tx_type,
        'amount': t.amount,
        'balance_type': t.balance_type,
        'description': t.description,
        'created_at': t.created_at.strftime('%d.%m.%Y %H:%M') if t.created_at else ''
    } for t in txs]
    return jsonify({'success': True, 'transactions': items})


@app.route('/api/payments/yookassa/webhook', methods=['POST'])
def yookassa_webhook():
    from payments import handle_yookassa_webhook
    event = request.json or {}
    try:
        handle_yookassa_webhook(event)
    except Exception as e:
        print(f"Ошибка вебхука ЮКассы: {e}")
    return jsonify({'success': True})


@app.route('/api/payments/crypto/webhook', methods=['POST'])
def cryptobot_webhook():
    from payments import handle_cryptobot_webhook
    update = request.json or {}
    try:
        handle_cryptobot_webhook(update)
    except Exception as e:
        print(f"Ошибка вебхука КриптоБота: {e}")
    return jsonify({'success': True})


@app.route('/api/payments/defpay/webhook', methods=['POST'])
def defpay_webhook():
    from payments import handle_defpay_update
    update = request.json or {}
    try:
        handle_defpay_update(update)
    except Exception as e:
        print(f"Ошибка вебхука DefPay: {e}")
    return '', 200


@app.route('/api/subscription/purchase-balance', methods=['POST'])
@login_required
def purchase_plan_balance():
    from payments import purchase_plan_from_balance
    from models import PLAN_PRICES
    data = request.json or {}
    plan = data.get('plan', '').lower()
    duration = int(data.get('duration', 30))
    if duration not in (30, 90, 180, 365):
        duration = 30
    if plan not in PLAN_PRICES:
        return jsonify({'success': False, 'error': 'Неизвестный тариф'})
    ok, err = purchase_plan_from_balance(current_user, plan, duration_days=duration)
    if not ok:
        return jsonify({'success': False, 'error': err})
    return jsonify({
        'success': True,
        'subscription_level': current_user.subscription_level,
        'api_access': current_user.api_access,
        'balance': current_user.balance,
        'bonus_balance': current_user.bonus_balance,
    })


@app.route('/api/subscription/plan-topup')
@login_required
def subscription_plan_topup():
    from payments import get_plan_topup_amount, get_plan_price
    from models import PLAN_PRICES
    plan = request.args.get('plan', '').lower()
    duration = int(request.args.get('duration', 30))
    if duration not in (30, 90, 180, 365):
        duration = 30
    if plan not in PLAN_PRICES and plan not in ('start', 'free'):
        return jsonify({'success': False, 'error': 'Неизвестный тариф'})
    plan_price = get_plan_price(plan, duration) if plan in PLAN_PRICES else 0.0
    topup = get_plan_topup_amount(current_user, plan, duration) if plan in PLAN_PRICES else 0.0

                                                           
    PLAN_RANKS = {'free': 0, 'start': 0, 'standart': 1, 'prime': 2, 'pro': 3}
    current_level = (current_user.subscription_level or 'Start').lower()
    current_rank = PLAN_RANKS.get(current_level, 0)
    target_rank = PLAN_RANKS.get(plan, 0)

    refund_amount = 0.0
    days_left = 0
    if target_rank < current_rank:
        expires = current_user.subscription_expires_at
        if expires:
            now = datetime.utcnow()
            if expires > now:
                days_left = (expires - now).days + 1
                if days_left > 0:
                    daily_rate = 290.0 / 30.0 if current_level == 'standart' else 590.0 / 30.0
                    unused_value = daily_rate * days_left
                    refund_amount = round(unused_value * 0.8, 2)

    return jsonify({
        'success': True,
        'plan': plan,
        'plan_price': plan_price,
        'balance': current_user.balance or 0,
        'topup_needed': topup,
        'covers_from_balance': topup <= 0,
        'refund_amount': refund_amount,
        'days_refunded': days_left
    })


@app.route('/api/subscription/set-plan', methods=['POST'])
@login_required
def set_subscription_plan():
    plan = (request.json or {}).get('plan', '').lower()
    if plan == 'start':
        from payments import refund_remaining_subscription
        refund_amount, days = refund_remaining_subscription(current_user)
        current_user.subscription_level = 'Start'
        db.session.commit()
        return jsonify({
            'success': True,
            'subscription_level': current_user.subscription_level,
            'refund_amount': refund_amount,
            'days_refunded': days
        })
    return jsonify({'success': False, 'error': 'Этот тариф требует оплаты'})


@app.route('/api/subscription/activate-pro', methods=['POST'])
@login_required
def activate_pro_info():
    return jsonify({
        'success': True,
        'price': PRO_ENTRY_PRICE,
        'bonus_tokens': PRO_BONUS_TOKENS,
        'already_pro': (current_user.subscription_level or '').lower() == 'pro'
    })


@app.route('/lk/payment/return')
@login_required
def payment_return():
    payment_id = request.args.get('payment_id')
    if payment_id:
        from payments import check_yookassa_status
        payment = Payment.query.filter_by(id=payment_id, user_id=current_user.id).first()
        if payment and payment.status == 'pending':
            check_yookassa_status(payment)
    return redirect(url_for('profile') + '?tab=wallet&balance_anim=1')


PROMO_CODES = {
    'VELOCITY500': 500,
    'WELCOME100': 100,
}


@app.route('/api/promo/redeem', methods=['POST'])
@login_required
def redeem_promo():
    from payments import apply_promo_bonus
    code = (request.json or {}).get('code', '').strip().upper()
    if not code:
        return jsonify({'success': False, 'error': 'Введите промокод'})
    amount = PROMO_CODES.get(code)
    if not amount:
        return jsonify({'success': False, 'error': 'Промокод недействителен'})
    used_key = f'promo_used_{code}'
    if session.get(used_key):
        return jsonify({'success': False, 'error': 'Промокод уже использован в этой сессии'})
    existing = Transaction.query.filter_by(
        user_id=current_user.id, tx_type='promo_bonus'
    ).filter(Transaction.description.contains(code)).first()
    if existing:
        return jsonify({'success': False, 'error': 'Вы уже активировали этот промокод'})
    apply_promo_bonus(current_user, amount, code)
    session[used_key] = True
    return jsonify({'success': True, 'bonus_added': amount, 'bonus_balance': current_user.bonus_balance})


@app.route('/api/models/catalog')
@login_required
def models_catalog():
    from ai_models import (
        serialize_catalog_for_user, serialize_pinned_for_user,
        AVAILABLE_MODEL_IDS, fetch_remote_model_ids, normalize_plan,
        is_pro_plan, PLAN_LABELS,
    )
    if not AVAILABLE_MODEL_IDS:
        fetch_remote_model_ids(force=True)
    plan = normalize_plan(current_user.subscription_level)
    return jsonify({
        'success': True,
        'categories': serialize_catalog_for_user(current_user, AVAILABLE_MODEL_IDS),
        'pinned': serialize_pinned_for_user(current_user, AVAILABLE_MODEL_IDS),
        'balance': current_user.balance,
        'bonus_balance': current_user.bonus_balance,
        'total_balance': current_user.total_spendable,
        'subscription': plan,
        'subscription_label': PLAN_LABELS.get(plan, plan),
        'is_pro': is_pro_plan(current_user.subscription_level),
    })


@app.route('/api/models/select', methods=['POST'])
@login_required
def models_select():
    import json
    from ai_models import MODEL_BY_ID, AVAILABLE_MODEL_IDS, find_fallback, is_plan_allowed
    data = request.json or {}
    category = data.get('category')
    model_id = data.get('model_id')
    if not category or not model_id:
        return jsonify({'success': False, 'error': 'Некорректные данные'})
    try:
        selected = json.loads(current_user.selected_models or '{}')
    except (TypeError, json.JSONDecodeError):
        selected = {}
    if model_id.startswith('auto-') or model_id == 'auto':
        selected[category] = f'auto-{category}'
    else:
        if model_id not in AVAILABLE_MODEL_IDS:
            fallback = find_fallback(model_id, AVAILABLE_MODEL_IDS, current_user.subscription_level)
            if not fallback:
                return jsonify({'success': False, 'error': 'Модель недоступна'})
            model_id = fallback
        if not is_plan_allowed(current_user.subscription_level, model_id):
            return jsonify({'success': False, 'error': 'Модель недоступна на вашем тарифе'})
        selected[category] = model_id
    current_user.selected_models = json.dumps(selected, ensure_ascii=False)
    db.session.commit()
    return jsonify({'success': True, 'selected': selected})


@app.route('/api/models/pin', methods=['POST'])
@login_required
def models_pin():
    import json
    from ai_models import MODEL_BY_ID, AVAILABLE_MODEL_IDS, load_pinned_models, PINNED_SLOTS, is_plan_allowed
    data = request.json or {}
    slot = data.get('slot')
    model_id = data.get('model_id')
    category = data.get('category')
    if slot is None or not isinstance(slot, int) or slot < 0 or slot >= PINNED_SLOTS:
        return jsonify({'success': False, 'error': 'Некорректный слот'})
    slots = load_pinned_models(current_user)
    if not model_id:
        slots[slot] = None
    else:
        if model_id not in MODEL_BY_ID:
            return jsonify({'success': False, 'error': 'Модель не найдена'})
        model = MODEL_BY_ID[model_id]
        if model_id not in AVAILABLE_MODEL_IDS:
            return jsonify({'success': False, 'error': 'Модель пока недоступна'})
        if not is_plan_allowed(current_user.subscription_level, model_id):
            return jsonify({'success': False, 'error': 'Модель недоступна на вашем тарифе'})
        slots[slot] = {'model_id': model_id, 'category': category or model['category']}
    current_user.pinned_models = json.dumps(slots, ensure_ascii=False)
    db.session.commit()
    from ai_models import serialize_pinned_for_user
    return jsonify({'success': True, 'pinned': serialize_pinned_for_user(current_user, AVAILABLE_MODEL_IDS)})


@app.route('/api/plans/prices')
@login_required
def plan_prices():
    from models import PLAN_PRICES, PRO_BONUS_TOKENS, API_ACCESS_PRICE
    return jsonify({
        'success': True,
        'plans': {
            'start': {'price': 0, 'name': 'Стартовый'},
            'standart': {'price': PLAN_PRICES['standart'], 'name': 'Стандарт'},
            'prime': {'price': PLAN_PRICES['prime'], 'name': 'Прайм'},
            'pro': {'price': PLAN_PRICES['pro'], 'bonus': PRO_BONUS_TOKENS, 'name': 'PRO'},
            'api': {'price': API_ACCESS_PRICE, 'name': 'API доступ'},
        },
        'current': {
            'subscription': current_user.subscription_level,
            'api_access': current_user.api_access,
        }
    })




                       

@app.route('/api/organizations', methods=['GET'])
@login_required
def get_organizations():
    from models import Organization
    orgs = Organization.query.filter_by(owner_id=current_user.id).all()
    result = []
    for o in orgs:
        result.append({
            'id': o.id,
            'name': o.name,
            'description': o.description,
            'logo': o.logo,
            'category': o.category,
            'created_at': o.created_at.strftime('%d.%m.%Y') if o.created_at else ''
        })
    return jsonify({'success': True, 'organizations': result, 'can_create': current_user.can_create_org})


@app.route('/api/organizations/create', methods=['POST'])
@login_required
def create_organization():
    import base64
    from models import Organization
    if not current_user.can_create_org:
        return jsonify({'success': False, 'error': 'Создание организаций доступно только на тарифе СТАНДАРТ и выше'})
    orgs_count = Organization.query.filter_by(owner_id=current_user.id).count()
    if orgs_count >= 3:
        return jsonify({'success': False, 'error': 'Максимум 3 организации на аккаунт'})
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Укажите название организации'})
    logo_url = None
    if 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename:
            image_b64 = base64.b64encode(file.read()).decode('utf-8')
            imgbb_key = '7f6e7f3eefae0359d4c6237ec614ef00'
            try:
                resp = requests.post(
                    f"https://api.imgbb.com/1/upload?key={imgbb_key}",
                    data={'image': image_b64}
                )
                if resp.ok and resp.json().get('success'):
                    logo_url = resp.json()['data']['url']
            except Exception as e:
                print(f"Ошибка загрузки логотипа: {e}")
    org = Organization(
        owner_id=current_user.id,
        name=name,
        description=description,
        category=category,
        logo=logo_url
    )
    db.session.add(org)
    db.session.commit()
    return jsonify({
        'success': True,
        'organization': {
            'id': org.id,
            'name': org.name,
            'description': org.description,
            'logo': org.logo,
            'category': org.category,
            'created_at': org.created_at.strftime('%d.%m.%Y') if org.created_at else ''
        }
    })


@app.route('/api/organizations/<int:org_id>', methods=['DELETE'])
@login_required
def delete_organization(org_id):
    from models import Organization
    org = Organization.query.filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        return jsonify({'success': False, 'error': 'Организация не найдена'})
    db.session.delete(org)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/organizations/<int:org_id>/update', methods=['POST'])
@login_required
def update_organization(org_id):
    import base64
    from models import Organization
    org = Organization.query.filter_by(id=org_id, owner_id=current_user.id).first()
    if not org:
        return jsonify({'success': False, 'error': 'Организация не найдена'})
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Укажите название организации'})
    if 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename:
            image_b64 = base64.b64encode(file.read()).decode('utf-8')
            imgbb_key = '7f6e7f3eefae0359d4c6237ec614ef00'
            try:
                resp = requests.post(
                    f"https://api.imgbb.com/1/upload?key={imgbb_key}",
                    data={'image': image_b64}
                )
                if resp.ok and resp.json().get('success'):
                    org.logo = resp.json()['data']['url']
            except Exception as e:
                print(f"Ошибка загрузки логотипа: {e}")
    org.name = name
    org.description = description
    org.category = category
    db.session.commit()
    return jsonify({
        'success': True,
        'organization': {
            'id': org.id,
            'name': org.name,
            'description': org.description,
            'logo': org.logo,
            'category': org.category
        }
    })


@app.route('/api/profile/generate-api-key', methods=['POST'])
@login_required
def generate_api_key():
    import secrets
    if not current_user.api_access:
        return jsonify({'success': False, 'error': 'Требуется купить доступ к API'})
    new_key = f"sk-vel_{secrets.token_hex(16)}"
    current_user.api_key = new_key
    db.session.commit()
    return jsonify({'success': True, 'api_key': new_key})


@app.route('/api/subscription/info')
@login_required
def subscription_info():
                                                             
    level = (current_user.subscription_level or 'Start').lower()
    days_left = current_user.subscription_days_left
    expires_at = current_user.subscription_expires_at.strftime('%d.%m.%Y') if current_user.subscription_expires_at else None
    return jsonify({
        'success': True,
        'level': level,
        'level_display': current_user.subscription_level or 'Start',
        'days_left': days_left,
        'expires_at': expires_at,
        'can_create_org': current_user.can_create_org,
    })



@app.errorhandler(400)

def bad_request(e):
    return render_template('404.html'), 400
@app.errorhandler(404)

def page_not_found(e):
    return render_template('404.html'), 404
@app.errorhandler(500)

def internal_server_error(e):
    return render_template('500.html'), 500
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7777))
    app.run(host='0.0.0.0', debug=False, port=port)