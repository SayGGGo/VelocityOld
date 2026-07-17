from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

PRO_ENTRY_PRICE = 790.0
PRO_BONUS_TOKENS = 500.0
API_ACCESS_PRICE = 990.0

PLAN_PRICES = {
    'standart': 290.0,
    'prime': 590.0,
    'pro': PRO_ENTRY_PRICE,
    'api': API_ACCESS_PRICE,
}

                                                            
ORG_ALLOWED_PLANS = {'standart', 'prime', 'pro'}

COURSE_CATEGORIES = [
    'Программирование', 'Дизайн', 'Маркетинг', 'Бизнес', 'Финансы',
    'Медицина', 'Языки', 'Физика и математика', 'История и культура',
    'Искусство', 'Психология', 'Другое'
]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    avatar = db.Column(db.String(500), nullable=True)
    original_avatar = db.Column(db.String(500), nullable=True)
    balance = db.Column(db.Float, default=0.0)
    bonus_balance = db.Column(db.Float, default=0.0)
    subscription_level = db.Column(db.String(50), default="Start")
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    auth_provider = db.Column(db.String(50), default="local")
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(100), nullable=True)
    two_factor_method = db.Column(db.String(50), default="app")
    defpay_authorized = db.Column(db.Boolean, default=False)
    pro_activated_at = db.Column(db.DateTime, nullable=True)
    api_access = db.Column(db.Boolean, default=False)
    api_key = db.Column(db.String(128), unique=True, nullable=True)
    selected_models = db.Column(db.Text, default='{}')
    pinned_models = db.Column(db.Text, default='[null,null,null]')

    yandex_id = db.Column(db.String(100), unique=True, nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    telegram_id = db.Column(db.String(100), unique=True, nullable=True)

    @property
    def display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        else:
            return "Пользователь"

    @property
    def total_spendable(self):
        return (self.balance or 0.0) + (self.bonus_balance or 0.0)

    @property
    def subscription_days_left(self):
                                                                        
        if not self.subscription_expires_at:
            return None
        delta = self.subscription_expires_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def can_create_org(self):
                                                                 
        plan = (self.subscription_level or 'start').lower()
        return plan in ORG_ALLOWED_PLANS

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def add_transaction(self, tx_type, amount, balance_type='main', description='', payment_id=None):
        tx = Transaction(
            user_id=self.id,
            tx_type=tx_type,
            amount=amount,
            balance_type=balance_type,
            description=description,
            payment_id=payment_id
        )
        db.session.add(tx)
        return tx


class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    logo = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

    owner = db.relationship('User', backref=db.backref('organizations', lazy=True))


class UserSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    session_key = db.Column(db.String(256), unique=True, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    device_type = db.Column(db.String(100), nullable=True)
    last_active = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    created_at = db.Column(db.DateTime, default=db.func.now())


class UserEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=True)


class UserPasskey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    credential_id = db.Column(db.String(500), unique=True, nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='RUB')
    method = db.Column(db.String(30), nullable=False)
    payment_type = db.Column(db.String(30), default='topup')
    status = db.Column(db.String(20), default='pending')
    external_id = db.Column(db.String(200), nullable=True)
    payment_url = db.Column(db.String(1000), nullable=True)
    bonus_amount = db.Column(db.Float, default=0.0)
    meta_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('payments', lazy=True))


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    tx_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    balance_type = db.Column(db.String(10), default='main')
    description = db.Column(db.String(500), nullable=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    payment = db.relationship('Payment', backref=db.backref('transactions', lazy=True))


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    banner = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    company = db.Column(db.String(150), nullable=True)
    agreement_accepted = db.Column(db.Boolean, default=False)
    structure_json = db.Column(db.Text, default='[]') # Holds JSON representation of course modules, lessons, tasks
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    author = db.relationship('User', backref=db.backref('courses_created', lazy=True))


class CourseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id', ondelete='CASCADE'), nullable=False)
    completed_lessons = db.Column(db.Text, default='[]') # JSON list of lesson IDs
    completed_tasks = db.Column(db.Text, default='{}') # JSON dict of task IDs to their status/score
    last_active_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    user = db.relationship('User', backref=db.backref('course_progresses', lazy=True))
    course = db.relationship('Course', backref=db.backref('progresses', lazy=True))

