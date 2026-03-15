# LogRaven — Nginx/Apache AI Prompt
# Log-type-specific additions for web access log analysis.
# TODO Month 3 Week 3: Implement.

NGINX_ADDITIONS = """
Web access log specific instructions:
- High 4xx rate from single IP = scanning or brute force (T1595)
- SQL keywords in URL paths = SQL injection attempt (T1190)
- Path traversal patterns (../../../) = directory traversal
- POST to unusual endpoints with large bodies = webshell upload attempt
"""
