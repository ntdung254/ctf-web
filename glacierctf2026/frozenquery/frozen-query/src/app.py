#!/usr/bin/env python3
# glacier-edge: caching reverse proxy with QUERY (RFC 10008) support.
import hashlib
import hmac
import json
import os
import threading
import time
import zlib

import requests
from flask import Flask, Response, abort, jsonify, request
from waitress import serve

BACKEND = "http://127.0.0.1:8000"
AUDIT_TOKEN = os.environ["AUDIT_TOKEN"]
MAX_BODY = 16 * 1024
MAX_CODINGS = 3
MAX_ENTRIES = 256
BLOCKLIST = ("flag", "summit")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY

cache = {}  # key -> (expires, status, headers, body)
cache_lock = threading.Lock()

INDEX = open(os.path.join(os.path.dirname(__file__), "index.html"), "rb").read()


def is_auditor():
    return hmac.compare_digest(
        request.headers.get("Authorization", ""), f"Bearer {AUDIT_TOKEN}"
    )


def parse_codings(header):
    codings = [c.strip().lower() for c in header.split(",") if c.strip()]
    if len(codings) > MAX_CODINGS:
        abort(413)
    if any(c != "gzip" for c in codings):
        abort(415)
    return codings


def gunzip(data):
    d = zlib.decompressobj(wbits=31)
    try:
        out = d.decompress(data, MAX_BODY + 1)
    except zlib.error:
        abort(400)
    if len(out) > MAX_BODY or d.unconsumed_tail:
        abort(413)
    return out


def waf_allows(body, encoding):
    # Peek through the transfer compression our SDK applies, then look at what
    # the query actually says.
    codings = parse_codings(encoding)
    if codings and codings[-1] == "gzip":
        body = gunzip(body)
    try:
        text = json.dumps(json.loads(body))
    except ValueError:
        text = body.decode("latin-1")
    return not any(word in text.lower() for word in BLOCKLIST)


def decode_content(body, encoding):
    # RFC 10008 2.7: content codings are removed before keying.
    for _ in reversed(parse_codings(encoding)):
        body = gunzip(body)
    return body


def normalize_media_type(value):
    mt = value.split(";")[0].strip().lower()
    # RFC 10008 2.7: normalize by media subtype suffix (+json)
    if mt.startswith("application/") and mt.endswith("+json"):
        mt = "application/json"
    return mt


def cache_key(path, media_type, accept, content):
    try:
        canonical = json.dumps(
            json.loads(content), sort_keys=True, separators=(",", ":")
        )
    except ValueError:
        abort(400)
    material = "\n".join([path, media_type, accept, canonical])
    return hashlib.sha256(material.encode()).hexdigest()


def cache_get(key):
    with cache_lock:
        entry = cache.get(key)
        if entry and entry[0] > time.time():
            return entry
        cache.pop(key, None)
        return None


def cache_put(key, ttl, status, headers, body):
    with cache_lock:
        now = time.time()
        for k in [k for k, v in cache.items() if v[0] <= now]:
            del cache[k]
        while len(cache) >= MAX_ENTRIES:
            del cache[next(iter(cache))]
        cache[key] = (now + ttl, status, headers, body)


def max_age(cache_control):
    for directive in cache_control.split(","):
        name, _, value = directive.strip().partition("=")
        if name.lower() == "max-age" and value.isdigit():
            return int(value)
    return 0


@app.get("/")
def index():
    return Response(INDEX, mimetype="text/html")


@app.route("/api/bulletin", methods=["GET", "HEAD"])
def bulletin_discovery():
    resp = jsonify(error="use QUERY")
    resp.status_code = 405
    resp.headers["Allow"] = "QUERY"
    resp.headers["Accept-Query"] = "application/json"
    return resp


@app.route("/api/bulletin", methods=["QUERY"])
def bulletin():
    raw = request.get_data()
    encoding = request.headers.get("Content-Encoding", "")
    auditor = is_auditor()

    if not auditor and not waf_allows(raw, encoding):
        return jsonify(error="blocked by glacier-edge"), 403

    media_type = normalize_media_type(request.headers.get("Content-Type", ""))
    if media_type != "application/json":
        resp = jsonify(error="unsupported query media type")
        resp.status_code = 415
        resp.headers["Accept-Query"] = "application/json"
        return resp

    content = decode_content(raw, encoding)
    accept = request.headers.get("Accept", "*/*")
    key = cache_key(request.path, media_type, accept, content)

    if "no-cache" not in request.headers.get("Cache-Control", ""):
        hit = cache_get(key)
        if hit:
            expires, status, headers, body = hit
            resp = Response(body, status=status, headers=headers)
            resp.headers["X-Cache"] = "HIT"
            return resp

    upstream = requests.request(
        "QUERY",
        BACKEND + request.path,
        data=content,
        headers={
            "Content-Type": media_type,
            "Accept": accept,
            "Authorization": request.headers.get("Authorization", ""),
        },
        timeout=5,
    )
    headers = {
        "Content-Type": upstream.headers.get("Content-Type", "application/json"),
        "Cache-Control": upstream.headers.get("Cache-Control", "no-store"),
    }
    cc = headers["Cache-Control"].lower()
    ttl = max_age(cc)
    # RFC 9111 3.5: authenticated responses are only shared when marked public.
    shareable = not request.headers.get("Authorization") or "public" in cc
    if upstream.status_code == 200 and ttl and "no-store" not in cc and shareable:
        cache_put(key, ttl, upstream.status_code, headers, upstream.content)

    resp = Response(upstream.content, status=upstream.status_code, headers=headers)
    resp.headers["X-Cache"] = "MISS"
    return resp


def auditor_loop():
    # Re-checks the summit bulletin every few seconds, bypassing the cache.
    while True:
        query = {
            "region": "summit",
            "fields": ["level", "note", "flag"],
            "window": int(time.time() // 30),
        }
        try:
            requests.request(
                "QUERY",
                "http://127.0.0.1:1337/api/bulletin",
                data=json.dumps(query),
                headers={
                    "Authorization": f"Bearer {AUDIT_TOKEN}",
                    "Content-Type": "application/vnd.glacier.bulletin+json",
                    "Accept": "application/json",
                    "Cache-Control": "no-cache",
                },
                timeout=5,
            )
        except requests.RequestException:
            pass
        time.sleep(5)


threading.Thread(target=auditor_loop, daemon=True).start()
serve(app, host="0.0.0.0", port=1337, threads=16)
