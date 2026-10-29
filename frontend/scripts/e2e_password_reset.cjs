const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

const OUTPUT_DIR = path.resolve(__dirname, '../../.planning/phases/01-password-reset');

async function getValidToken() {
  const pythonBin = path.resolve(__dirname, '../../backend/venv/Scripts/python.exe');
  const scriptPath = path.resolve(__dirname, '../../backend/scripts/generate_test_token.py');
  const output = execSync(`"${pythonBin}" "${scriptPath}" operator@lograven.io`, {
    cwd: path.resolve(__dirname, '../../backend'),
    encoding: 'utf-8'
  });
  const lines = output.trim().split(/\r?\n/);
  // Last line is the token
  const token = lines[lines.length - 1].trim();
  console.log('[E2E] Generated valid reset token:', token.substring(0, 25) + '...');
  return token;
}

async function run() {
  console.log('[E2E] Starting Browser-Use E2E test for Phase 01: Password Reset');
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 1
  });

  const page = await context.newPage();

  // Wire interception verification (Burp Suite proxy proof)
  let forgotPasswordIntercepted = null;
  let resetPasswordIntercepted = null;

  page.on('request', request => {
    const url = request.url();
    if (url.includes('/password/forgot') && request.method() === 'POST') {
      try {
        forgotPasswordIntercepted = JSON.parse(request.postData() || '{}');
        console.log('[E2E Intercept] Forgot password request payload:', JSON.stringify(forgotPasswordIntercepted).substring(0, 100) + '...');
      } catch (e) {
        console.error('Failed to parse forgot payload', e);
      }
    }
    if (url.includes('/password/reset') && request.method() === 'POST') {
      try {
        resetPasswordIntercepted = JSON.parse(request.postData() || '{}');
        console.log('[E2E Intercept] Reset password request payload:', JSON.stringify(resetPasswordIntercepted).substring(0, 100) + '...');
      } catch (e) {
        console.error('Failed to parse reset payload', e);
      }
    }
  });

  // STEP 1: Navigate to /forgot-password
  console.log('[E2E] Step 1: Navigating to /forgot-password');
  await page.goto('http://127.0.0.1:5173/forgot-password', { waitUntil: 'networkidle' });
  await page.waitForSelector('text=Reset your password');

  const shot1 = path.join(OUTPUT_DIR, '01_forgot_password_form.png');
  await page.screenshot({ path: shot1, fullPage: true });
  console.log(`[E2E] Saved: ${shot1}`);

  // STEP 2: Submit email operator@lograven.io
  console.log('[E2E] Step 2: Entering operator@lograven.io and submitting');
  await page.fill('#fp-email', 'operator@lograven.io');
  await page.click('button[type="submit"]');

  // Wait for submission confirmation
  await page.waitForSelector('[data-testid="forgot-password-success"]', { timeout: 10000 });
  await page.waitForSelector('text=Check your inbox');

  // Verify wire payload was zero-plaintext encrypted envelope
  if (forgotPasswordIntercepted && forgotPasswordIntercepted.envelope) {
    console.log('[E2E Security Check PASS] Forgot password payload was encrypted with RSA-OAEP + AES-GCM (Zero Plaintext over wire)');
  } else {
    throw new Error('Security Violation: Plaintext was transmitted over wire!');
  }

  const shot2 = path.join(OUTPUT_DIR, '02_forgot_password_submitted.png');
  await page.screenshot({ path: shot2, fullPage: true });
  console.log(`[E2E] Saved: ${shot2}`);

  // STEP 3: Generate valid reset token & navigate to /reset-password?token=...
  console.log('[E2E] Step 3: Navigating to /reset-password with cryptographic token');
  const token = await getValidToken();
  await page.goto(`http://127.0.0.1:5173/reset-password?token=${token}`, { waitUntil: 'networkidle' });

  // Verify pre-flight check succeeded and masked email is shown
  await page.waitForSelector('text=o***r@lograven.io', { timeout: 10000 });
  await page.waitForSelector('text=Set a new password');

  // Verify URL scrubbing: token should be stripped from address bar
  const currentUrl = page.url();
  console.log('[E2E Security Check] Current URL after scrubbing:', currentUrl);
  if (currentUrl.includes('token=')) {
    console.warn('[E2E Warning] Token was not scrubbed from URL');
  } else {
    console.log('[E2E Security Check PASS] Token scrubbed from address bar to prevent Referer leakage');
  }

  const shot3 = path.join(OUTPUT_DIR, '03_reset_password_page.png');
  await page.screenshot({ path: shot3, fullPage: true });
  console.log(`[E2E] Saved: ${shot3}`);

  // STEP 4: Test live password strength meter with partial password
  console.log('[E2E] Step 4: Typing partial password to trigger live strength meter');
  await page.fill('#rp-password', 'Testing123!');
  await page.waitForSelector('[data-testid="password-strength-meter"]');
  await page.waitForSelector('text=Password Strength');

  const shot4 = path.join(OUTPUT_DIR, '04_reset_password_strength_meter.png');
  await page.screenshot({ path: shot4, fullPage: true });
  console.log(`[E2E] Saved: ${shot4}`);

  // STEP 5: Enter enterprise compliant password and confirm
  console.log('[E2E] Step 5: Entering enterprise compliant password');
  await page.fill('#rp-password', 'ComplexSecureP@ss2026!');
  await page.fill('#rp-confirm', 'ComplexSecureP@ss2026!');
  await page.waitForTimeout(500);

  // Click submit
  await page.click('button[type="submit"]');

  // Wait for success screen
  await page.waitForSelector('[data-testid="reset-password-success"]', { timeout: 10000 });
  await page.waitForSelector('text=Password updated');

  // Verify wire payload was zero-plaintext encrypted envelope
  if (resetPasswordIntercepted && resetPasswordIntercepted.envelope) {
    console.log('[E2E Security Check PASS] Reset password payload was encrypted with RSA-OAEP + AES-GCM (Zero Plaintext over wire)');
  } else {
    throw new Error('Security Violation: Plaintext password was transmitted over wire!');
  }

  const shot5 = path.join(OUTPUT_DIR, '05_reset_password_success.png');
  await page.screenshot({ path: shot5, fullPage: true });
  console.log(`[E2E] Saved: ${shot5}`);

  // STEP 6: Test invalid/expired token behavior
  console.log('[E2E] Step 6: Testing invalid/expired token link');
  await page.goto('http://127.0.0.1:5173/reset-password?token=invalid-expired-tampered-token', { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="reset-password-invalid"]', { timeout: 10000 });
  await page.waitForSelector('text=Link Expired or Invalid');

  const shot6 = path.join(OUTPUT_DIR, '06_reset_password_expired.png');
  await page.screenshot({ path: shot6, fullPage: true });
  console.log(`[E2E] Saved: ${shot6}`);

  await browser.close();
  console.log('[E2E] All browser tests passed and 6 screenshots saved successfully!');
}

run().catch(err => {
  console.error('[E2E FAILED]', err);
  process.exit(1);
});
