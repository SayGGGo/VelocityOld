import json
import os
import uuid
import threading
import time
from datetime import datetime, timedelta

import requests

from models import db, Payment, User, PRO_ENTRY_PRICE, PRO_BONUS_TOKENS, PLAN_PRICES, API_ACCESS_PRICE

DEFPAY_BOT_TOKEN = os.environ.get('DEFPAY_BOT_TOKEN', '7662730963:AAH-TFWdklp2duYJC2mRcCF8EtjuzSKAoOo')
DEFPAY_BOT_LINK = os.environ.get('DEFPAY_BOT_LINK', 'https://t.me/defpayrobot?start=_tgr_bqrbCoxjMzdi')
CRYPTOBOT_TOKEN = os.environ.get('CRYPTOBOT_TOKEN', '604762:AAEyDbeA0BGceO7rxDyPEsCrXdQgjJyQfb0')
YOOKASSA_SECRET = os.environ.get('YOOKASSA_SECRET_KEY', 'test_BJ7X9AtJIFeGW7CV1RznYP_4qr8swm6hlIYz1CwYXM8')
YOOKASSA_SHOP_ID = os.environ.get('YOOKASSA_SHOP_ID', '')


def _tg_api(method, payload):
    url = f'https://api.telegram.org/bot{DEFPAY_BOT_TOKEN}/{method}'
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data.get('ok'):
        raise RuntimeError(data.get('description', 'Telegram API error'))
    return data.get('result')


def rub_to_usdt(amount_rub):
    return max(1, int((amount_rub + 91) // 92))


def rub_to_stars(amount_rub):
    return max(1, int(amount_rub))


def get_plan_price(plan_type, duration_days=30):
    if plan_type not in PLAN_PRICES:
        return 0.0
    base_price = PLAN_PRICES[plan_type]
    if plan_type in ('standart', 'prime'):
        if duration_days == 90:
            return round(base_price * 3 * 0.90, 2)
        elif duration_days == 180:
            return round(base_price * 6 * 0.80, 2)
        elif duration_days == 365:
            return round(base_price * 12 * 0.70, 2)
    return base_price


def refund_remaining_subscription(user):
    level = (user.subscription_level or '').lower()
    if level not in ('standart', 'prime'):
        return 0.0, 0
    expires = user.subscription_expires_at
    if not expires:
        return 0.0, 0
    now = datetime.utcnow()
    if expires <= now:
        return 0.0, 0
    days_left = (expires - now).days + 1
    if days_left <= 0:
        return 0.0, 0
    daily_rate = 290.0 / 30.0 if level == 'standart' else 590.0 / 30.0
    unused_value = daily_rate * days_left
    refund_amount = round(unused_value * 0.8, 2)
    if refund_amount > 0:
        user.balance = (user.balance or 0.0) + refund_amount
        user.add_transaction(
            'refund',
            refund_amount,
            balance_type='main',
            description=f'Возврат 80% за неиспользованные {days_left} дн. подписки {user.subscription_level}'
        )
    user.subscription_expires_at = None
    return refund_amount, days_left


def create_payment_record(user, amount, method, payment_type='topup', bonus_amount=0.0, duration_days=30):
    payment = Payment(
        user_id=user.id,
        amount=float(amount),
        method=method,
        payment_type=payment_type,
        bonus_amount=bonus_amount,
        status='pending',
        meta_json=json.dumps({'duration_days': duration_days})
    )
    db.session.add(payment)
    db.session.commit()
    return payment


def get_payment_amount(payment_type, custom_amount=None, duration_days=30):
    if payment_type in PLAN_PRICES:
        return get_plan_price(payment_type, duration_days)
    if payment_type == 'topup':
        return float(custom_amount or 0)
    return float(custom_amount or 0)


def get_plan_topup_amount(user, payment_type, duration_days=30):
                                                                                  
    if payment_type not in PLAN_PRICES:
        return 0.0
    plan_price = get_plan_price(payment_type, duration_days)
    main_balance = user.balance or 0.0
    return max(0.0, round(plan_price - main_balance, 2))


def purchase_plan_from_balance(user, payment_type, duration_days=30):
                                                                                         
    if payment_type not in PLAN_PRICES:
        return False, 'Неизвестный тариф'

    PLAN_RANKS = {'free': 0, 'start': 0, 'standart': 1, 'prime': 2, 'pro': 3}
    current_level = (user.subscription_level or 'Start').lower()
    current_rank = PLAN_RANKS.get(current_level, 0)
    target_rank = PLAN_RANKS.get(payment_type, 0)

    if target_rank < current_rank:
        refund_remaining_subscription(user)

    plan_price = get_plan_price(payment_type, duration_days)
    main_balance = user.balance or 0.0
    if main_balance < plan_price:
        missing = round(plan_price - main_balance, 2)
        return False, f'Недостаточно средств. Пополните баланс на {missing:.0f} ₽'

    if payment_type == 'pro' and (user.subscription_level or '').lower() == 'pro':
        return False, 'Тариф PRO уже активен'
    if payment_type == 'api' and user.api_access:
        return False, 'Доступ к API уже куплен'

    user.balance = main_balance - plan_price
    now = datetime.utcnow()
    if payment_type == 'pro':
        user.subscription_level = 'Pro'
        user.pro_activated_at = now
                                                                
        user.subscription_expires_at = None
        user.bonus_balance = (user.bonus_balance or 0.0) + PRO_BONUS_TOKENS
        user.add_transaction(
            'pro_bonus',
            PRO_BONUS_TOKENS,
            balance_type='bonus',
            description='Бонусные токены при активации PRO'
        )
        user.add_transaction(
            'pro_activation',
            plan_price,
            balance_type='main',
            description='Списание за активацию тарифа PRO'
        )
    elif payment_type in ('standart', 'prime'):
        current_expiry = user.subscription_expires_at
        if current_expiry and current_expiry > now and (user.subscription_level or '').lower() == payment_type:
            user.subscription_expires_at = current_expiry + timedelta(days=duration_days)
        else:
            user.subscription_expires_at = now + timedelta(days=duration_days)
        user.subscription_level = payment_type.capitalize()
        desc = f'Оплата подписки {payment_type.upper()} на {duration_days} дней'
        user.add_transaction(
            'subscription',
            plan_price,
            balance_type='main',
            description=desc
        )
    elif payment_type == 'api':
        user.api_access = True
        user.add_transaction(
            'api_access',
            plan_price,
            balance_type='main',
            description='Разовая покупка доступа к API'
        )
    db.session.commit()
    return True, None


def create_yookassa_payment(user, amount, return_url, payment_type='topup', duration_days=30):
    if not YOOKASSA_SHOP_ID:
        raise RuntimeError('YOOKASSA_SHOP_ID не настроен. Укажите ID магазина в .env')
    from yookassa import Configuration, Payment as YKPayment

    Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET)
    payment = create_payment_record(user, amount, 'yookassa', payment_type, duration_days=duration_days)
    description = 'Пополнение баланса VELOCITY'
    descriptions = {
        'pro': 'Активация тарифа PRO VELOCITY',
        'standart': 'Подписка СТАНДАРТ VELOCITY',
        'prime': 'Подписка ПРАЙМ VELOCITY',
        'api': 'Разовый доступ к VELOCITY API',
    }
    description = descriptions.get(payment_type, description)

    return_with_id = return_url + ('&' if '?' in return_url else '?') + f'payment_id={payment.id}'

    yk_payment = YKPayment.create({
        'amount': {'value': f'{amount:.2f}', 'currency': 'RUB'},
        'confirmation': {'type': 'redirect', 'return_url': return_with_id},
        'capture': True,
        'description': description,
        'metadata': {'payment_id': payment.id, 'user_id': user.id, 'payment_type': payment_type}
    }, uuid.uuid4())

    payment.external_id = yk_payment.id
    payment.payment_url = yk_payment.confirmation.confirmation_url
    db.session.commit()
    return payment


def create_cryptobot_invoice(user, amount_rub, return_url, payment_type='topup', duration_days=30):
    payment = create_payment_record(user, amount_rub, 'crypto', payment_type, duration_days=duration_days)
    usdt_amount = rub_to_usdt(amount_rub)
    headers = {'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN}
    payload = {
        'asset': 'USDT',
        'amount': str(usdt_amount),
        'description': 'Пополнение VELOCITY' if payment_type == 'topup' else 'Активация PRO VELOCITY',
        'payload': json.dumps({'payment_id': payment.id, 'user_id': user.id}),
        'paid_btn_name': 'openChannel',
        'paid_btn_url': return_url,
        'allow_comments': False,
        'expires_in': 3600
    }
    resp = requests.post('https://pay.crypt.bot/api/createInvoice', headers=headers, json=payload, timeout=15)
    data = resp.json()
    if not data.get('ok'):
        payment.status = 'canceled'
        db.session.commit()
        raise RuntimeError(data.get('error', {}).get('name', 'CryptoBot error'))
    result = data['result']
    payment.external_id = str(result['invoice_id'])
    payment.payment_url = result.get('pay_url') or result.get('bot_invoice_url')
    
                                        
    meta = {'duration_days': duration_days, 'usdt_amount': usdt_amount}
    payment.meta_json = json.dumps(meta)
    
    db.session.commit()
    return payment


def create_stars_invoice(user, amount_rub, payment_type='topup', duration_days=30):
    if not user.telegram_id:
        raise RuntimeError('Сначала привяжите Telegram в разделе «Безопасность»')
    if not user.defpay_authorized:
        raise RuntimeError('defpay_not_authorized')

    payment = create_payment_record(user, amount_rub, 'stars', payment_type, duration_days=duration_days)
    stars_amount = rub_to_stars(amount_rub)
    title = 'Пополнение VELOCITY' if payment_type == 'topup' else 'Активация PRO VELOCITY'
    description = f'Зачисление {amount_rub:.0f} ₽ на баланс VELOCITY'

    invoice_link = _tg_api('createInvoiceLink', {
        'title': title,
        'description': description,
        'payload': json.dumps({'payment_id': payment.id, 'user_id': user.id, 'type': payment_type}),
        'currency': 'XTR',
        'prices': [{'label': title, 'amount': stars_amount}]
    })
    payment.external_id = f'stars_{payment.id}'
    payment.payment_url = invoice_link
    
    meta = {'duration_days': duration_days, 'stars_amount': stars_amount}
    payment.meta_json = json.dumps(meta)
    
    db.session.commit()
    return payment


def complete_payment(payment, provider_note=''):
    if payment.status == 'succeeded':
        return False

    user = User.query.get(payment.user_id)
    if not user:
        return False

    payment.status = 'succeeded'
    payment.completed_at = datetime.utcnow()

    if payment.payment_type in PLAN_PRICES:
        duration_days = 30
        if payment.meta_json:
            try:
                meta = json.loads(payment.meta_json)
                duration_days = meta.get('duration_days', 30)
            except Exception:
                pass
                
        plan_price = get_plan_price(payment.payment_type, duration_days)
        user.balance = (user.balance or 0.0) + payment.amount
        user.balance = max(0.0, (user.balance or 0.0) - plan_price)

        if payment.payment_type == 'pro':
            user.subscription_level = 'Pro'
            user.pro_activated_at = datetime.utcnow()
            user.bonus_balance = (user.bonus_balance or 0.0) + PRO_BONUS_TOKENS
            user.add_transaction(
                'pro_bonus',
                PRO_BONUS_TOKENS,
                balance_type='bonus',
                description='Бонусные токены при активации PRO',
                payment_id=payment.id
            )
            user.add_transaction(
                'pro_activation',
                plan_price,
                balance_type='main',
                description='Оплата активации тарифа PRO',
                payment_id=payment.id
            )
        elif payment.payment_type in ('standart', 'prime'):
            PLAN_RANKS = {'free': 0, 'start': 0, 'standart': 1, 'prime': 2, 'pro': 3}
            current_level = (user.subscription_level or 'Start').lower()
            current_rank = PLAN_RANKS.get(current_level, 0)
            target_rank = PLAN_RANKS.get(payment.payment_type, 0)
            if target_rank < current_rank:
                refund_remaining_subscription(user)

            now = datetime.utcnow()
            current_expiry = user.subscription_expires_at
            if current_expiry and current_expiry > now and (user.subscription_level or '').lower() == payment.payment_type:
                user.subscription_expires_at = current_expiry + timedelta(days=duration_days)
            else:
                user.subscription_expires_at = now + timedelta(days=duration_days)
                
            user.subscription_level = payment.payment_type.capitalize()
            desc = f'Оплата подписки {payment.payment_type.upper()} на {duration_days} дней'
            user.add_transaction(
                'subscription',
                plan_price,
                balance_type='main',
                description=desc,
                payment_id=payment.id
            )
        elif payment.payment_type == 'api':
            user.api_access = True
            user.add_transaction(
                'api_access',
                plan_price,
                balance_type='main',
                description='Разовая покупка доступа к API',
                payment_id=payment.id
            )
    else:
        user.balance = (user.balance or 0.0) + payment.amount
        user.add_transaction(
            'topup',
            payment.amount,
            balance_type='main',
            description=provider_note or f'Пополнение через {payment.method}',
            payment_id=payment.id
        )

    db.session.commit()
    return True


def apply_promo_bonus(user, amount, code):
    user.bonus_balance = (user.bonus_balance or 0.0) + float(amount)
    user.add_transaction(
        'promo_bonus',
        float(amount),
        balance_type='bonus',
        description=f'Бонус по промокоду {code}'
    )
    db.session.commit()


def spend_tokens(user, amount, prefer_bonus=True):
    amount = float(amount)
    if amount <= 0:
        return True

    bonus = user.bonus_balance or 0.0
    main = user.balance or 0.0
    total = bonus + main
    if total < amount:
        return False

    remaining = amount
    if prefer_bonus and bonus > 0:
        from_bonus = min(bonus, remaining)
        user.bonus_balance = bonus - from_bonus
        remaining -= from_bonus
        if from_bonus > 0:
            user.add_transaction('spend', from_bonus, balance_type='bonus', description='Списание бонусных токенов')

    if remaining > 0:
        user.balance = main - remaining
        user.add_transaction('spend', remaining, balance_type='main', description='Списание с основного баланса')

    db.session.commit()
    return True


def check_yookassa_status(payment):
    if not payment.external_id or not YOOKASSA_SHOP_ID:
        return payment.status
    from yookassa import Configuration, Payment as YKPayment

    Configuration.configure(YOOKASSA_SHOP_ID, YOOKASSA_SECRET)
    yk_payment = YKPayment.find_one(payment.external_id)
    if yk_payment.status == 'succeeded':
        complete_payment(payment, 'Пополнение через ЮKassa')
    elif yk_payment.status == 'canceled':
        payment.status = 'canceled'
        db.session.commit()
    return payment.status


def check_cryptobot_status(payment):
    if not payment.external_id:
        return payment.status
    headers = {'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN}
    resp = requests.get(
        'https://pay.crypt.bot/api/getInvoices',
        headers=headers,
        params={'invoice_ids': payment.external_id},
        timeout=15
    )
    data = resp.json()
    if data.get('ok') and data.get('result', {}).get('items'):
        item = data['result']['items'][0]
        if item.get('status') == 'paid':
            complete_payment(payment, 'Пополнение через CryptoBot')
        elif item.get('status') == 'expired':
            payment.status = 'canceled'
            db.session.commit()
    return payment.status


def handle_defpay_update(update):
    message = update.get('message') or {}
    text = (message.get('text') or '').strip()
    chat = message.get('chat') or {}
    tg_id = str(chat.get('id', ''))
    if not tg_id:
        return

    if text.lower().startswith('/start') or text.lower() == 'start':
        user = User.query.filter_by(telegram_id=tg_id).first()
        if user:
            user.defpay_authorized = True
            db.session.commit()
            print(f'Бот DefPay запущен для пользователя {user.id}')
            _tg_api('sendMessage', {
                'chat_id': tg_id,
                'text': '✅ Авторизация VELOCITY успешна!\n\nВернитесь на сайт и нажмите «Оплатить» для пополнения баланса через Telegram Stars.'
            })
        else:
            print(f'Бот DefPay запущен без привязки к Telegram {tg_id}')
            _tg_api('sendMessage', {
                'chat_id': tg_id,
                'text': '⚠️ Сначала привяжите Telegram к аккаунту VELOCITY в личном кабинете (Профиль → Безопасность), затем снова нажмите Start.'
            })
        return

    successful = message.get('successful_payment')
    if successful:
        payload_raw = successful.get('invoice_payload') or '{}'
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            payload = {}
        payment_id = payload.get('payment_id')
        payment = Payment.query.get(payment_id) if payment_id else None
        if payment and payment.status == 'pending':
            complete_payment(payment, 'Пополнение через Telegram Stars')
        return

    pre_checkout = update.get('pre_checkout_query')
    if pre_checkout:
        query_id = pre_checkout.get('id')
        payload_raw = pre_checkout.get('invoice_payload') or '{}'
        ok = True
        try:
            payload = json.loads(payload_raw)
            payment = Payment.query.get(payload.get('payment_id'))
            if not payment or payment.status != 'pending':
                ok = False
        except json.JSONDecodeError:
            ok = False
        _tg_api('answerPreCheckoutQuery', {'pre_checkout_query_id': query_id, 'ok': ok})


def handle_yookassa_webhook(event):
    obj = event.get('object') or {}
    external_id = obj.get('id')
    if not external_id:
        return
    payment = Payment.query.filter_by(external_id=external_id, method='yookassa').first()
    if not payment:
        return
    if obj.get('status') == 'succeeded':
        complete_payment(payment, 'Пополнение через ЮKassa')
    elif obj.get('status') == 'canceled':
        payment.status = 'canceled'
        db.session.commit()


def handle_cryptobot_webhook(update):
    if update.get('update_type') != 'invoice_paid':
        return
    payload_raw = update.get('payload') or {}
    invoice_id = str(payload_raw.get('invoice_id', ''))
    payment = Payment.query.filter_by(external_id=invoice_id, method='crypto').first()
    if payment:
        complete_payment(payment, 'Пополнение через CryptoBot')


def get_pro_payment_amount():
    return PRO_ENTRY_PRICE


def start_defpay_poller(app):
    def poll_loop():
        try:
            requests.post(
                f'https://api.telegram.org/bot{DEFPAY_BOT_TOKEN}/deleteWebhook',
                json={'drop_pending_updates': False},
                timeout=10
            )
        except Exception as e:
            print(f'Ошибка удаления вебхука DefPay: {e}')
        offset = 0
        fail_streak = 0
        last_fail_log = 0.0
        print('Опрос обновлений DefPay запущен')
        while True:
            try:
                with app.app_context():
                    resp = requests.get(
                        f'https://api.telegram.org/bot{DEFPAY_BOT_TOKEN}/getUpdates',
                        params={
                            'offset': offset,
                            'timeout': 25,
                            'allowed_updates': ['message', 'pre_checkout_query'],
                        },
                        timeout=35
                    )
                    try:
                        data = resp.json()
                    except ValueError:
                        data = {}
                    if resp.status_code == 409:
                        fail_streak += 1
                        now = time.time()
                        if now - last_fail_log > 120:
                            print('Конфликт обновлений DefPay: запущен другой процесс')
                            last_fail_log = now
                        time.sleep(min(30, 3 + fail_streak * 2))
                        continue
                    if not resp.ok or not data.get('ok'):
                        fail_streak += 1
                        now = time.time()
                        if now - last_fail_log > 60:
                            err = data.get('description') or resp.text[:120] or f'HTTP {resp.status_code}'
                            print(f'Ошибка опроса обновлений DefPay: {err}')
                            last_fail_log = now
                        time.sleep(min(20, 3 + fail_streak))
                        continue
                    fail_streak = 0
                    for update in data.get('result', []):
                        offset = update['update_id'] + 1
                        try:
                            handle_defpay_update(update)
                        except Exception as e:
                            print(f'Ошибка обновления DefPay: {e}')
            except Exception as e:
                fail_streak += 1
                now = time.time()
                if now - last_fail_log > 60:
                    print(f'Ошибка поллинга DefPay: {e}')
                    last_fail_log = now
                time.sleep(min(20, 3 + fail_streak))
    thread = threading.Thread(target=poll_loop, daemon=True, name='defpay-poller')
    thread.start()
    return thread
