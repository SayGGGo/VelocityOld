import json
import os
import threading
import time

import requests

CHAT_API_URL = os.environ.get(
    'CHAT_API_URL',
    'https://chat.gpt-chatbot.ru/api/openai/v1/chat/completions'
)
CHAT_MODELS_URL = os.environ.get(
    'CHAT_MODELS_URL',
    'https://chat.gpt-chatbot.ru/api/openai/v1/models'
)
CHAT_HEADERS = {
    'accept': 'application/json',
    'accept-language': 'ru-RU,ru;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://chat.gpt-chatbot.ru',
    'referer': 'https://chat.gpt-chatbot.ru/',
    'user-agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    ),
}
USD_RUB = float(os.environ.get('USD_RUB_RATE', '92'))

AVAILABLE_MODEL_IDS = set()
REMOTE_MODEL_IDS = set()
MODELS_LOCK = threading.Lock()
REMOTE_CACHE_AT = 0.0
REMOTE_CACHE_TTL = 300

                                                                                   
CATEGORIES = {
    'claude': {
        'name': 'Claude',
        'logo': 'https://images.seeklogo.com/logo-png/55/2/claude-logo-png_seeklogo-554534.png',
        'price_source': 'anthropic.com/pricing',
    },
    'gemini': {
        'name': 'Gemini',
        'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Google_Gemini_icon_2025.svg/500px-Google_Gemini_icon_2025.svg.png',
        'price_source': 'ai.google.dev/pricing',
    },
    'chatgpt': {
        'name': 'ChatGPT',
        'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/ChatGPT-Logo.svg/960px-ChatGPT-Logo.svg.png',
        'price_source': 'gpt-chatbot.ru',
    },
    'deepseek': {
        'name': 'DeepSeek',
        'logo': 'https://1000logos.net/wp-content/uploads/2025/01/DeepSeek-Emblem.png',
        'price_source': 'api.deepseek.com/pricing',
    },
    'perplexity': {
        'name': 'Perplexity',
        'logo': 'https://images.seeklogo.com/logo-png/61/2/perplexity-ai-icon-black-logo-png_seeklogo-611679.png',
        'price_source': 'docs.perplexity.ai/guides/pricing',
    },
    'qwen': {
        'name': 'Qwen',
        'logo': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/Qwen_logo.svg/3840px-Qwen_logo.svg.png',
        'price_source': 'help.aliyun.com/model-studio/pricing',
    },
    'free': {
        'name': 'Бесплатные',
        'logo': '/static/assets/logo-mini.svg',
        'price_source': 'gpt-chatbot.ru',
    },
}

MODEL_CATALOG = [
    {'id': 'claude-haiku-45', 'category': 'claude', 'name': 'Haiku 4.5', 'tier': 'economy',
     'api_model': 'mistral-tiny-latest', 'input': 0.80, 'output': 4.0},
    {'id': 'claude-sonnet-5', 'category': 'claude', 'name': 'Sonnet 5', 'tier': 'balanced',
     'api_model': 'anthropic/claude-sonnet-4', 'input': 3.0, 'output': 15.0},
    {'id': 'claude-opus-48', 'category': 'claude', 'name': 'Opus 4.8', 'tier': 'flagship',
     'api_model': 'Claude-3.7', 'input': 15.0, 'output': 75.0},

    {'id': 'gemini-31-pro', 'category': 'gemini', 'name': 'Gemini 3.1 Pro', 'tier': 'flagship',
     'api_model': 'google/gemini-2.5-pro-preview-05-06', 'input': 1.25, 'output': 10.0},
    {'id': 'gemini-25-pro', 'category': 'gemini', 'name': 'Gemini 2.5 Pro', 'tier': 'balanced',
     'api_model': 'google/gemini-2.5-pro-preview-05-06', 'input': 1.25, 'output': 10.0},
    {'id': 'gemini-25-flash', 'category': 'gemini', 'name': 'Gemini 2.5 Flash', 'tier': 'economy',
     'api_model': 'stepfun-ai/step-3.7-flash', 'input': 0.15, 'output': 0.60},

    {'id': 'gpt-55', 'category': 'chatgpt', 'name': 'GPT-5.5', 'tier': 'flagship',
     'api_model': 'gpt-5.2', 'input': 0.0, 'output': 0.0, 'free': True},
    {'id': 'gpt-54', 'category': 'chatgpt', 'name': 'GPT-5.4', 'tier': 'balanced',
     'api_model': 'gpt-5.4-mini', 'input': 0.0, 'output': 0.0, 'free': True},
    {'id': 'gpt-4o-mini', 'category': 'chatgpt', 'name': 'GPT-4o mini', 'tier': 'economy',
     'api_model': 'chatgpt-4o-latest', 'input': 0.0, 'output': 0.0, 'free': True},

    {'id': 'deepseek-v4-pro', 'category': 'deepseek', 'name': 'DeepSeek V4 Pro', 'tier': 'flagship',
     'api_model': 'deepseek-ai/deepseek-v4-pro', 'input': 0.27, 'output': 1.10},
    {'id': 'deepseek-r1', 'category': 'deepseek', 'name': 'DeepSeek R1', 'tier': 'balanced',
     'api_model': 'deepseek-ai/deepseek-r1', 'input': 0.55, 'output': 2.19},
    {'id': 'deepseek-v4-flash', 'category': 'deepseek', 'name': 'DeepSeek V4 Flash', 'tier': 'economy',
     'api_model': 'deepseek-ai/deepseek-v4-flash', 'input': 0.14, 'output': 0.28},

    {'id': 'sonar-pro', 'category': 'perplexity', 'name': 'Sonar Pro', 'tier': 'flagship',
     'api_model': 'perplexity/sonar-pro', 'input': 3.0, 'output': 15.0},
    {'id': 'sonar-reasoning-pro', 'category': 'perplexity', 'name': 'Sonar Reasoning Pro', 'tier': 'balanced',
     'api_model': 'perplexity/sonar-reasoning-pro', 'input': 2.0, 'output': 8.0},
    {'id': 'sonar', 'category': 'perplexity', 'name': 'Sonar', 'tier': 'economy',
     'api_model': 'perplexity/sonar', 'input': 1.0, 'output': 1.0},

    {'id': 'qwen-37-max', 'category': 'qwen', 'name': 'Qwen 3.7 Max', 'tier': 'flagship',
     'api_model': 'qwen3.7-max', 'input': 1.20, 'output': 6.0},
    {'id': 'qwen-36-plus', 'category': 'qwen', 'name': 'Qwen 3.6 Plus', 'tier': 'balanced',
     'api_model': 'qwen/qwen3-next-80b-a3b-instruct', 'input': 0.33, 'output': 1.95},
    {'id': 'qwen-max', 'category': 'qwen', 'name': 'Qwen-Max', 'tier': 'balanced',
     'api_model': 'qwen/qwen-max', 'aliases': ['qwen3.7-max'], 'input': 1.60, 'output': 6.40},
    {'id': 'qwen-25-72b', 'category': 'qwen', 'name': 'Qwen 2.5 / 3.0 (72B)', 'tier': 'balanced',
     'api_model': 'qwen/qwen-2.5-72b-instruct', 'aliases': ['qwen/qwen3-235b-a22b'], 'input': 0.23, 'output': 0.23},
    {'id': 'qwen-36-flash', 'category': 'qwen', 'name': 'Qwen 3.6 Flash', 'tier': 'economy',
     'api_model': 'qwen/qwen-turbo', 'aliases': ['qwen/qwen2.5-7b-instruct'], 'input': 0.05, 'output': 0.20},
    {'id': 'qwen-turbo', 'category': 'qwen', 'name': 'Qwen-Turbo', 'tier': 'economy',
     'api_model': 'qwen/qwen2.5-7b-instruct', 'input': 0.05, 'output': 0.20},

    {'id': 'free-gpt-oss-120b', 'category': 'free', 'name': 'GPT-OSS 120B', 'tier': 'balanced',
     'api_model': 'openai/gpt-oss-120b', 'input': 0.0, 'output': 0.0, 'free': True},
    {'id': 'free-gemma-27b', 'category': 'free', 'name': 'Gemma 3 27B', 'tier': 'economy',
     'api_model': 'google/gemma-3-27b-it', 'input': 0.0, 'output': 0.0, 'free': True},
    {'id': 'free-llama-70b', 'category': 'free', 'name': 'Llama 3.3 70B', 'tier': 'balanced',
     'api_model': 'meta/llama-3.3-70b-instruct', 'input': 0.0, 'output': 0.0, 'free': True},
]

MODEL_BY_ID = {m['id']: m for m in MODEL_CATALOG}
TIER_ORDER = {'economy': 0, 'balanced': 1, 'flagship': 2}
PINNED_SLOTS = 3

PLAN_RANK = {'start': 0, 'standart': 1, 'prime': 2, 'pro': 3}
PLAN_LABELS = {
    'start': 'Стартовый',
    'standart': 'Стандарт',
    'prime': 'Прайм',
    'pro': 'PRO',
}
CATEGORY_MIN_PLAN = {
    'free': 'start',
    'chatgpt': 'start',
    'deepseek': 'standart',
    'claude': 'prime',
    'gemini': 'prime',
    'perplexity': 'prime',
    'qwen': 'prime',
}

                                                                                  
MODEL_MIN_PLAN = {
    'free-gpt-oss-120b': 'start',
    'free-gemma-27b': 'start',
    'free-llama-70b': 'start',
    'gpt-4o-mini': 'start',
    'gpt-54': 'start',
    'gpt-55': 'start',
    'deepseek-v4-flash': 'standart',
    'deepseek-r1': 'standart',
    'claude-haiku-45': 'prime',
    'claude-sonnet-5': 'prime',
    'gemini-25-flash': 'prime',
    'gemini-25-pro': 'prime',
    'sonar': 'prime',
    'sonar-reasoning-pro': 'prime',
    'qwen-36-flash': 'prime',
    'qwen-turbo': 'prime',
    'qwen-36-plus': 'prime',
    'qwen-25-72b': 'prime',
    'deepseek-v4-pro': 'prime',
    'claude-opus-48': 'pro',
    'gemini-31-pro': 'pro',
    'sonar-pro': 'pro',
    'qwen-37-max': 'pro',
    'qwen-max': 'pro',
}


def normalize_plan(subscription_level):
    s = (subscription_level or 'start').strip().lower()
    if s in ('free', ''):
        return 'start'
    if s == 'standard':
        return 'standart'
    return s if s in PLAN_RANK else 'start'


def is_pro_plan(subscription_level):
    return normalize_plan(subscription_level) == 'pro'


def get_model_min_plan(model):
    if model['id'] in MODEL_MIN_PLAN:
        return MODEL_MIN_PLAN[model['id']]
    if model.get('free'):
        return 'start'
    tier = model.get('tier', 'balanced')
    if tier == 'economy':
        return 'standart'
    if tier == 'balanced':
        return 'prime'
    return 'pro'


def is_plan_allowed(subscription_level, model_id):
    model = MODEL_BY_ID.get(model_id)
    if not model:
        return False
    user_rank = PLAN_RANK[normalize_plan(subscription_level)]
    need_rank = PLAN_RANK[get_model_min_plan(model)]
    return user_rank >= need_rank


def filter_ids_by_plan(model_ids, subscription_level):
    return {mid for mid in model_ids if is_plan_allowed(subscription_level, mid)}


def get_category_min_plan(cat_id):
    models = [m for m in MODEL_CATALOG if m['category'] == cat_id]
    if not models:
        return CATEGORY_MIN_PLAN.get(cat_id, 'pro')
    return min((get_model_min_plan(m) for m in models), key=lambda p: PLAN_RANK[p])


def is_category_accessible(subscription_level, cat_id):
    return PLAN_RANK[normalize_plan(subscription_level)] >= PLAN_RANK[get_category_min_plan(cat_id)]


def _candidate_api_ids(model):
    raw = [model['api_model'], *model.get('aliases', [])]
    expanded = []
    for mid in raw:
        if not mid:
            continue
        expanded.append(mid)
        if mid.endswith(':free'):
            expanded.append(mid[:-5])
    return list(dict.fromkeys(expanded))


def _is_listed_in_remote(model, remote_ids):
    if not remote_ids:
        return True
    return any(mid in remote_ids for mid in _candidate_api_ids(model))


def fetch_remote_model_ids(force=False):
    global REMOTE_CACHE_AT
    now = time.time()
    if not force and REMOTE_MODEL_IDS and (now - REMOTE_CACHE_AT) < REMOTE_CACHE_TTL:
        return set(REMOTE_MODEL_IDS)
    try:
        resp = requests.get(CHAT_MODELS_URL, headers=CHAT_HEADERS, timeout=12)
        if not resp.ok:
            return set(REMOTE_MODEL_IDS)
        data = resp.json()
        remote_ids = {item['id'] for item in data.get('data', []) if item.get('id')}
        with MODELS_LOCK:
            REMOTE_MODEL_IDS.clear()
            REMOTE_MODEL_IDS.update(remote_ids)
            REMOTE_CACHE_AT = now
        return remote_ids
    except Exception:
        return set(REMOTE_MODEL_IDS)


def refresh_model_availability(sync=True):
    remote_ids = fetch_remote_model_ids(force=sync)
    available = set()
    for model in MODEL_CATALOG:
        if _is_listed_in_remote(model, remote_ids):
            available.add(model['id'])
    with MODELS_LOCK:
        AVAILABLE_MODEL_IDS.clear()
        AVAILABLE_MODEL_IDS.update(available)
    print(f'Модели: доступно {len(available)} из {len(MODEL_CATALOG)}')
    return available


def get_available_models():
    with MODELS_LOCK:
        if not AVAILABLE_MODEL_IDS:
            return []
        return [MODEL_BY_ID[mid] for mid in AVAILABLE_MODEL_IDS if mid in MODEL_BY_ID]


def estimate_output_tokens(balance_rub, model):
    if model.get('free'):
        return 999999
    out_price = model.get('output') or model.get('input') or 1.0
    if out_price <= 0:
        return 999999
    cost_per_token_rub = (out_price / 1_000_000) * USD_RUB
    if cost_per_token_rub <= 0:
        return 0
    return int(balance_rub / cost_per_token_rub)


def pick_auto_model(category, balance_rub, available_ids=None, subscription_level=None):
    available_ids = available_ids or AVAILABLE_MODEL_IDS
    if subscription_level:
        available_ids = filter_ids_by_plan(available_ids, subscription_level)
    candidates = [
        m for m in MODEL_CATALOG
        if m['category'] == category and m['id'] in available_ids
    ]
    if not candidates:
        return None
    if is_pro_plan(subscription_level or ''):
        if balance_rub >= 500:
            tier = 'flagship'
        elif balance_rub >= 100:
            tier = 'balanced'
        else:
            tier = 'economy'
    else:
        tier = 'economy'
    for t in (tier, 'balanced', 'economy', 'flagship'):
        tier_models = [m for m in candidates if m['tier'] == t]
        if tier_models:
            tier_models.sort(key=lambda x: x['output'])
            return tier_models[0]['id']
    return candidates[0]['id']


def find_fallback(model_id, available_ids=None, subscription_level=None):
    available_ids = available_ids or AVAILABLE_MODEL_IDS
    if subscription_level:
        available_ids = filter_ids_by_plan(available_ids, subscription_level)
    model = MODEL_BY_ID.get(model_id)
    if not model:
        return pick_auto_model('free', 0, available_ids, subscription_level)
    if model_id in available_ids:
        return model_id
    same_cat = [
        m for m in MODEL_CATALOG
        if m['category'] == model['category'] and m['id'] in available_ids
    ]
    if same_cat:
        same_cat.sort(key=lambda x: abs(TIER_ORDER.get(x['tier'], 1) - TIER_ORDER.get(model['tier'], 1)))
        return same_cat[0]['id']
    auto = pick_auto_model(model['category'], 0, available_ids, subscription_level)
    if auto:
        return auto
    free = [m for m in MODEL_CATALOG if m['category'] == 'free' and m['id'] in available_ids]
    return free[0]['id'] if free else None


def _serialize_model_entry(m, balance, api_ids, subscription_level, selected=None, is_auto=False, auto_meta=None):
    pro = is_pro_plan(subscription_level)
    if is_auto:
        resolves_id = auto_meta.get('resolves_to')
        resolves_model = MODEL_BY_ID.get(resolves_id, m)
        api_ok = bool(resolves_id and resolves_id in api_ids)
        plan_ok = bool(resolves_id and is_plan_allowed(subscription_level, resolves_id))
        model_id = auto_meta['id']
        min_plan = get_model_min_plan(resolves_model)
        display_name = auto_meta['name']
        is_free = auto_meta.get('free', False)
    else:
        api_ok = m['id'] in api_ids
        plan_ok = is_plan_allowed(subscription_level, m['id'])
        model_id = m['id']
        min_plan = get_model_min_plan(m)
        display_name = m['name']
        is_free = m.get('free', False)
        resolves_model = m

    usable = api_ok and plan_ok
    entry = {
        'id': model_id,
        'name': display_name,
        'free': is_free,
        'tier': resolves_model.get('tier'),
        'api_available': api_ok,
        'plan_allowed': plan_ok,
        'available': usable,
        'locked_plan': api_ok and not plan_ok,
        'required_plan': min_plan,
        'required_plan_label': PLAN_LABELS.get(min_plan, min_plan),
        'selected': selected == model_id,
    }
    if is_auto:
        entry['is_auto'] = True
        entry['resolves_to'] = auto_meta.get('resolves_to')
        entry['resolves_name'] = auto_meta.get('resolves_name')
    if pro and usable:
        if is_auto:
            entry['input'] = auto_meta.get('input')
            entry['output'] = auto_meta.get('output')
        else:
            entry['input'] = m['input']
            entry['output'] = m['output']
        entry['tokens_left'] = estimate_output_tokens(balance, resolves_model)
    elif usable and is_free:
        entry['input'] = 0
        entry['output'] = 0
    return entry

def load_pinned_models(user):
    try:
        raw = json.loads(user.pinned_models or '[null,null,null]')
    except (TypeError, json.JSONDecodeError):
        raw = [None, None, None]
    slots = []
    for i in range(PINNED_SLOTS):
        item = raw[i] if i < len(raw) else None
        if isinstance(item, dict) and item.get('model_id'):
            slots.append({'model_id': item['model_id'], 'category': item.get('category')})
        else:
            slots.append(None)
    return slots


def serialize_pinned_for_user(user, available_ids=None):
    available_ids = available_ids or AVAILABLE_MODEL_IDS
    subscription_level = user.subscription_level
    slots = load_pinned_models(user)
    result = []
    for slot in slots:
        if not slot or not slot.get('model_id'):
            result.append(None)
            continue
        model = MODEL_BY_ID.get(slot['model_id'])
        if not model:
            result.append(None)
            continue
        cat = CATEGORIES.get(model['category'], {})
        api_ok = model['id'] in available_ids
        plan_ok = is_plan_allowed(subscription_level, model['id'])
        result.append({
            'model_id': model['id'],
            'category': model['category'],
            'category_name': cat.get('name', model['category']),
            'logo': cat.get('logo', '/static/assets/logo-mini.svg'),
            'name': model['name'],
            'free': model.get('free', False),
            'available': api_ok and plan_ok,
            'locked_plan': api_ok and not plan_ok,
        })
    return result


def serialize_catalog_for_user(user, available_ids=None):
    available_ids = available_ids or AVAILABLE_MODEL_IDS
    subscription_level = user.subscription_level
    plan = normalize_plan(subscription_level)
    pro = is_pro_plan(subscription_level)
    balance = (user.balance or 0) + (user.bonus_balance or 0) if pro else 0
    try:
        selected = json.loads(user.selected_models or '{}')
    except (TypeError, json.JSONDecodeError):
        selected = {}

    categories = []
    for cat_id, cat_meta in CATEGORIES.items():
        models = []
        cat_models = [m for m in MODEL_CATALOG if m['category'] == cat_id]
        cat_min = get_category_min_plan(cat_id)
        cat_accessible = is_category_accessible(subscription_level, cat_id)
        accessible_cat = [
            m for m in cat_models
            if m['id'] in available_ids and is_plan_allowed(subscription_level, m['id'])
        ]
        auto_id = pick_auto_model(cat_id, balance, available_ids, subscription_level) if accessible_cat else None
        sel = selected.get(cat_id, f'auto-{cat_id}')
        if sel.startswith('auto-') or sel == 'auto':
            sel = f'auto-{cat_id}'
        elif sel not in available_ids or not is_plan_allowed(subscription_level, sel):
            resolved = find_fallback(sel, available_ids, subscription_level)
            sel = resolved or (f'auto-{cat_id}' if auto_id else sel)

        if auto_id and cat_accessible:
            auto_model = MODEL_BY_ID[auto_id]
            auto_meta = {
                'id': f'auto-{cat_id}',
                'name': 'AUTO — оптимальный выбор',
                'resolves_to': auto_id,
                'resolves_name': auto_model['name'],
                'input': auto_model['input'],
                'output': auto_model['output'],
                'free': auto_model.get('free', False),
            }
            models.append(_serialize_model_entry(
                auto_model, balance, available_ids, subscription_level,
                selected=sel, is_auto=True, auto_meta=auto_meta,
            ))
        for m in cat_models:
            models.append(_serialize_model_entry(
                m, balance, available_ids, subscription_level, selected=sel,
            ))
        categories.append({
            'id': cat_id,
            'name': cat_meta['name'],
            'logo': cat_meta.get('logo', '/static/assets/logo-mini.svg'),
            'price_source': cat_meta.get('price_source', '') if pro else '',
            'min_plan': cat_min,
            'min_plan_label': PLAN_LABELS.get(cat_min, cat_min),
            'accessible': cat_accessible,
            'selected': sel,
            'model_count': len(cat_models),
            'available_count': len(accessible_cat),
            'models': models,
        })
    return categories
