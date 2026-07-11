import { describe, expect, it } from 'vitest'
import { normalizeApiBase } from './normalizeApiBase'

describe('normalizeApiBase', () => {
  it.each([
    [undefined, ''],
    ['', ''],
    ['  ', ''],
    ['https://api.example.com/', 'https://api.example.com'],
    ['https://api.example.com/api', 'https://api.example.com'],
    ['https://api.example.com/api/v1/', 'https://api.example.com'],
    ['https://api.example.com/api/v2/api/', 'https://api.example.com'],
  ])('normalizes %p to %p', (input, expected) => {
    expect(normalizeApiBase(input)).toBe(expected)
  })
})
