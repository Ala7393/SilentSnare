#!/usr/bin/env python3
"""
mitmproxy addon – يرسل الطلبات والردود إلى خادم Flask.
"""

import requests
from mitmproxy import http, ctx
import uuid

# عنوان خادم Flask (التطبيق الرئيسي)
FLASK_URL = "http://127.0.0.1:5000/scenarios/intercept_flow"

class InterceptAddon:
    def request(self, flow: http.HTTPFlow) -> None:
        """معالجة الطلبات الصادرة."""
        try:
            ctx.log(f"📤 [addon] اعتراض طلب إلى {flow.request.url}")
            data = {
                'id': str(uuid.uuid4()),
                'type': 'request',
                'method': flow.request.method,
                'host': flow.request.host,
                'path': flow.request.path,
                'url': flow.request.url,
                'headers': dict(flow.request.headers),
                'content': flow.request.text[:5000],  # نحتفظ بأول 5000 حرف
                'timestamp': flow.request.timestamp_start
            }
            requests.post(FLASK_URL, json=data, timeout=0.1)
            ctx.log(f"✅ [addon] تم إرسال الطلب إلى Flask")
        except Exception as e:
            ctx.log(f"⚠️ [addon] خطأ في إرسال الطلب: {e}")

    def response(self, flow: http.HTTPFlow) -> None:
        """معالجة الردود الواردة."""
        try:
            ctx.log(f"📥 [addon] اعتراض رد من {flow.request.url}")
            data = {
                'id': str(uuid.uuid4()),
                'type': 'response',
                'method': flow.request.method,
                'host': flow.request.host,
                'path': flow.request.path,
                'url': flow.request.url,
                'status_code': flow.response.status_code,
                'headers': dict(flow.response.headers),
                'content': flow.response.text[:5000],
                'size': len(flow.response.content),
                'timestamp': flow.response.timestamp_end
            }
            requests.post(FLASK_URL, json=data, timeout=0.1)
            ctx.log(f"✅ [addon] تم إرسال الرد إلى Flask")
        except Exception as e:
            ctx.log(f"⚠️ [addon] خطأ في إرسال الرد: {e}")

addons = [InterceptAddon()]
