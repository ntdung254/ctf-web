#!/usr/bin/env python3
# Bulletin API. Only reachable through the edge proxy (listens on loopback).
import hmac
import os

from flask import Flask, jsonify, request
from waitress import serve

FLAG = os.environ.get("FLAG", "gctf{FAKE_FAKE_FAKE_FAKE_FAKE_FAKE}")
AUDIT_TOKEN = os.environ["AUDIT_TOKEN"]

BULLETINS = {
    "valley": {"level": 1, "note": "Low danger. Enjoy the powder."},
    "ridge": {"level": 3, "note": "Considerable. Wind slabs on north aspects."},
    "glacier": {"level": 2, "note": "Moderate. Mind the crevasses."},
    "summit": {"level": 5, "note": "Extreme. Station closed to the public.", "flag": FLAG},
}
RESTRICTED_FIELDS = {"flag"}

app = Flask(__name__)


@app.route("/api/bulletin", methods=["QUERY"])
def bulletin():
    q = request.get_json(force=True, silent=True)
    if not isinstance(q, dict) or not isinstance(q.get("region"), str):
        return jsonify(error="query must be an object with a 'region'"), 422
    fields = q.get("fields", ["level", "note"])
    if not isinstance(fields, list):
        return jsonify(error="'fields' must be a list"), 422
    fields = [f for f in fields if isinstance(f, str)]

    region = q["region"]
    if region not in BULLETINS:
        return jsonify(error="unknown region"), 404

    auditor = hmac.compare_digest(
        request.headers.get("Authorization", ""), f"Bearer {AUDIT_TOKEN}"
    )
    if (region == "summit" or RESTRICTED_FIELDS & set(fields)) and not auditor:
        return jsonify(error="auditors only"), 403

    data = {f: BULLETINS[region][f] for f in fields if f in BULLETINS[region]}
    resp = jsonify(region=region, window=q.get("window"), **data)
    # Bulletins are the same for everyone, let the edge cache them.
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp


serve(app, host="127.0.0.1", port=8000)
