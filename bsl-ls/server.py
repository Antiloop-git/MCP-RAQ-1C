"""BSL Language Server HTTP wrapper.

Thin Flask API around bsl-language-server JAR.
POST /analyze  — check BSL code, return diagnostics.
GET  /health   — liveness probe.
"""

import json
import os
import subprocess
import tempfile
from flask import Flask, request, jsonify

app = Flask(__name__)

BSL_LS_JAR = os.getenv("BSL_LS_JAR", "/app/bsl-ls.jar")
MAX_LINES = 10_000


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    diag_filter = data.get("diagnostics_filter", "all")

    if not code or not code.strip():
        return jsonify({"error": "Код не предоставлен"}), 400

    lines = code.splitlines()
    truncated = False
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES]
        code = "\n".join(lines)
        truncated = True

    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "module.bsl")
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(code)

        report_path = os.path.join(tmpdir, "bsl-ls-report.json")

        try:
            result = subprocess.run(
                [
                    "java", "-jar", BSL_LS_JAR,
                    "--analyze",
                    "--srcDir", tmpdir,
                    "--reporter", "json",
                    "--outputDir", tmpdir,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            return jsonify({"error": "Таймаут анализа (>30 сек)"}), 504

        diagnostics = []

        # BSL LS writes report as json file in outputDir
        json_files = [f for f in os.listdir(tmpdir) if f.endswith(".json")]
        for jf in json_files:
            try:
                with open(os.path.join(tmpdir, jf), encoding="utf-8") as rf:
                    report = json.load(rf)
                if isinstance(report, list):
                    for file_report in report:
                        for d in file_report.get("diagnostics", []):
                            diagnostics.append({
                                "line": d.get("range", {}).get("start", {}).get("line", 0) + 1,
                                "severity": _severity(d.get("severity", 2)),
                                "code": d.get("code", ""),
                                "message": d.get("message", ""),
                            })
                elif isinstance(report, dict):
                    for d in report.get("diagnostics", []):
                        diagnostics.append({
                            "line": d.get("range", {}).get("start", {}).get("line", 0) + 1,
                            "severity": _severity(d.get("severity", 2)),
                            "code": d.get("code", ""),
                            "message": d.get("message", ""),
                        })
            except (json.JSONDecodeError, KeyError):
                continue

    if diag_filter != "all":
        severity_map = {"error": "Error", "warning": "Warning", "info": "Information"}
        target = severity_map.get(diag_filter)
        if target:
            diagnostics = [d for d in diagnostics if d["severity"] == target]

    return jsonify({
        "diagnostics": diagnostics,
        "lines_checked": len(lines),
        "truncated": truncated,
    })


def _severity(code):
    return {1: "Error", 2: "Warning", 3: "Information", 4: "Hint"}.get(code, "Warning")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8005"))
    app.run(host="0.0.0.0", port=port)
