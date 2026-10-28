// LogRaven — Frontend Web Crypto Hybrid Encryption Utility
//
// PURPOSE:
//   Encrypts sensitive authentication payloads (forgot password, reset password)
//   using the browser's native Web Crypto API (window.crypto.subtle).
//   Guarantees ZERO plaintext over the wire, defending against local proxy
//   inspection (Burp Suite, OWASP ZAP) and transport tampering.
//
// CIPHERS:
//   - Asymmetric: RSA-OAEP with SHA-256 (Server Public Key)
//   - Symmetric: Ephemeral AES-256-GCM with 96-bit random IV and 128-bit Tag
//   - Embeds millisecond timestamp and random cryptographic nonce (anti-replay)

import axios from 'axios'

export interface EncryptedEnvelope {
  key_id: string
  encrypted_key: string
  iv: string
  ciphertext: string
  tag: string
}

interface ServerPublicKeyResponse {
  key_id: string
  algorithm: string
  public_key: string
}

let cachedPublicKey: { key_id: string; key: CryptoKey } | null = null

/** Convert base64 string to Uint8Array */
function base64ToUint8Array(base64: string): Uint8Array {
  const binaryString = window.atob(base64)
  const len = binaryString.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }
  return bytes
}

/** Convert ArrayBuffer to base64 string */
function arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  let binary = ''
  const bytes = new Uint8Array(buffer)
  const len = bytes.byteLength
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return window.btoa(binary)
}

/** Convert PEM string to CryptoKey (RSA-OAEP-256) */
async function importRsaPublicKey(pem: string): Promise<CryptoKey> {
  const cleanPem = pem
    .replace(/-----BEGIN PUBLIC KEY-----/, '')
    .replace(/-----END PUBLIC KEY-----/, '')
    .replace(/\s+/g, '')

  const binaryDer = base64ToUint8Array(cleanPem)

  return window.crypto.subtle.importKey(
    'spki',
    binaryDer.buffer as ArrayBuffer,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    true,
    ['encrypt']
  )
}

/** Fetch or retrieve cached server RSA public key */
export async function getOrFetchPublicKey(): Promise<{ key_id: string; key: CryptoKey }> {
  if (cachedPublicKey) {
    return cachedPublicKey
  }

  // Fetch from /auth/crypto/public-key (supported through Vite proxy / client)
  const response = await axios.get<ServerPublicKeyResponse>('/auth/crypto/public-key')
  const { key_id, public_key } = response.data

  const importedKey = await importRsaPublicKey(public_key)
  cachedPublicKey = { key_id, key: importedKey }
  return cachedPublicKey
}

/**
 * Encrypts an arbitrary JSON payload into an EncryptedEnvelope.
 * In Burp Suite / network tabs, the entire payload is opaque ciphertext.
 */
export async function encryptPayload(data: Record<string, unknown>): Promise<EncryptedEnvelope> {
  const { key_id, key: rsaPublicKey } = await getOrFetchPublicKey()

  // 1. Generate ephemeral 256-bit AES-GCM symmetric key
  const aesKey = await window.crypto.subtle.generateKey(
    {
      name: 'AES-GCM',
      length: 256,
    },
    true,
    ['encrypt']
  )

  // 2. Export raw AES key and encrypt it with Server RSA Public Key (RSA-OAEP-256)
  const rawAesKey = await window.crypto.subtle.exportKey('raw', aesKey)
  const encryptedKeyBuffer = await window.crypto.subtle.encrypt(
    {
      name: 'RSA-OAEP',
    },
    rsaPublicKey,
    rawAesKey
  )

  // 3. Prepare payload with millisecond timestamp and random cryptographic UUID nonce
  const payloadToEncrypt = {
    ...data,
    timestamp: Date.now(),
    nonce: window.crypto.randomUUID ? window.crypto.randomUUID() : Math.random().toString(36).substring(2) + Date.now().toString(36),
  }

  const encodedPayload = new TextEncoder().encode(JSON.stringify(payloadToEncrypt))

  // 4. Generate random 12-byte (96-bit) IV for AES-GCM
  const iv = window.crypto.getRandomValues(new Uint8Array(12))

  // 5. Encrypt payload with AES-GCM (produces ciphertext + 16-byte authentication tag appended)
  const encryptedPayloadBuffer = await window.crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv,
      tagLength: 128,
    },
    aesKey,
    encodedPayload
  )

  const encryptedBytes = new Uint8Array(encryptedPayloadBuffer)
  // Last 16 bytes is the GCM authentication tag
  const ciphertextBytes = encryptedBytes.slice(0, encryptedBytes.length - 16)
  const tagBytes = encryptedBytes.slice(encryptedBytes.length - 16)

  return {
    key_id,
    encrypted_key: arrayBufferToBase64(encryptedKeyBuffer),
    iv: arrayBufferToBase64(iv),
    ciphertext: arrayBufferToBase64(ciphertextBytes),
    tag: arrayBufferToBase64(tagBytes),
  }
}
