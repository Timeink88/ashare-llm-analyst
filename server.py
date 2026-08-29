#!/usr/bin/env python3
import json
import os
import sys
import threading
import time
import traceback
import subprocess
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

# Import business logic from main.py
try:
    from main import StockAnalyzer
except Exception as e:
    print("[server] Failed to import StockAnalyzer from main.py:", e)
    raise


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


class Config:
    def __init__(self):
        # Public directory to serve
        self.public_dir = os.environ.get("PUBLIC_DIR", os.path.join(os.getcwd(), "public"))
        # Update interval in minutes
        self.update_interval_minutes = int(os.environ.get("UPDATE_INTERVAL_MINUTES", "60"))
        # Port to serve
        self.port = int(os.environ.get("PORT", "8000"))
        # Git auto update
        self.auto_git_update = os.environ.get("AUTO_GIT_UPDATE", "1") in ("1", "true", "True")
        self.git_remote = os.environ.get("GIT_REMOTE", "origin")
        self.git_branch = os.environ.get("GIT_BRANCH", "main")
        self.auto_update_pip = os.environ.get("AUTO_UPDATE_PIP", "0") in ("1", "true", "True")
        # History count
        self.history_count = int(os.environ.get("HISTORY_COUNT", "120"))
        # Stocks config path or inline JSON
        self.stocks_json_env = os.environ.get("STOCKS_JSON")
        self.stocks_file = os.environ.get("STOCKS_FILE", os.path.join(os.getcwd(), "stocks.json"))

    def load_stocks(self):
        # Prefer env JSON
        if self.stocks_json_env:
            try:
                stocks = json.loads(self.stocks_json_env)
                if isinstance(stocks, dict) and stocks:
                    return stocks
                _log("STOCKS_JSON is not a valid non-empty JSON object; ignoring.")
            except Exception as e:
                _log(f"Failed to parse STOCKS_JSON: {e}")
        # Fallback to file
        if os.path.exists(self.stocks_file):
            try:
                with open(self.stocks_file, "r", encoding="utf-8") as f:
                    stocks = json.load(f)
                    if isinstance(stocks, dict) and stocks:
                        return stocks
            except Exception as e:
                _log(f"Failed to load stocks file {self.stocks_file}: {e}")
        # Default
        return {"上证指数": "sh000001"}


class State:
    def __init__(self):
        self.last_update_time = None
        self.last_update_status = None  # "success" or "error"
        self.last_update_error = None
        self.last_update_duration_s = None
        self.current_commit = None
        self.updating = False


STATE = State()
CFG = Config()


class Updater:
    def __init__(self, cfg: Config, state: State):
        self.cfg = cfg
        self.state = state

    def _get_current_commit(self):
        try:
            out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.STDOUT)
            return out.decode().strip()
        except Exception:
            return None

    def _git_pull_if_needed(self):
        if not self.cfg.auto_git_update:
            return False
        try:
            # Fetch remote
            subprocess.check_call(["git", "fetch", self.cfg.git_remote], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            local = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            remote_ref = f"{self.cfg.git_remote}/{self.cfg.git_branch}"
            remote = subprocess.check_output(["git", "rev-parse", remote_ref]).decode().strip()
            if local != remote:
                _log(f"New commit detected: local {local[:7]} -> remote {remote[:7]}, pulling...")
                subprocess.check_call(["git", "pull", self.cfg.git_remote, self.cfg.git_branch])
                if self.cfg.auto_update_pip and os.path.exists(os.path.join(os.getcwd(), "requirement.txt")):
                    _log("Updating Python dependencies from requirement.txt...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirement.txt"])  # noqa: S603,S607
                return True
        except subprocess.CalledProcessError as e:
            _log(f"Git auto-update failed: {e}")
        except Exception as e:
            _log(f"Git auto-update error: {e}")
        return False

    def restart_process(self):
        _log("Restarting process to apply updates...")
        python = sys.executable
        os.execv(python, [python, __file__])

    def generate_report_once(self):
        start = time.time()
        self.state.updating = True
        self.state.last_update_error = None
        try:
            stocks = CFG.load_stocks()
            _log(f"Generating report for stocks: {stocks}")
            analyzer = StockAnalyzer(stocks, count=self.cfg.history_count)
            output_path = os.path.join(self.cfg.public_dir, "index.html")
            result = analyzer.run_analysis(output_path=output_path)
            if result:
                self.state.last_update_status = "success"
                _log(f"Report generated at: {result}")
            else:
                self.state.last_update_status = "error"
                self.state.last_update_error = "run_analysis returned None"
                _log("Report generation returned None")
        except Exception as e:
            self.state.last_update_status = "error"
            self.state.last_update_error = f"{e}\n{traceback.format_exc()}"
            _log(f"Report generation failed: {e}")
        finally:
            self.state.last_update_time = datetime.now(timezone.utc)
            self.state.last_update_duration_s = round(time.time() - start, 2)
            self.state.current_commit = self._get_current_commit()
            self.state.updating = False

    def loop(self):
        # Run once immediately on start
        _log("Initial update...")
        pulled = self._git_pull_if_needed()
        if pulled:
            self.restart_process()
            return  # not reached
        self.generate_report_once()
        interval = max(1, self.cfg.update_interval_minutes) * 60
        while True:
            time.sleep(interval)
            pulled = self._git_pull_if_needed()
            if pulled:
                self.restart_process()
                return  # not reached
            self.generate_report_once()


UPDATER = Updater(CFG, STATE)


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CFG.public_dir, **kwargs)

    def log_message(self, format, *args):  # noqa: A003 - match base signature
        _log("HTTP " + (format % args))

    def _send_json(self, payload: dict, code: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - base class API
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send_json({"status": "ok"})
            return
        if parsed.path == "/status":
            # format last_update_time in Shanghai timezone for readability
            if STATE.last_update_time:
                tz_sh = timezone(timedelta(hours=8))
                sh_time = STATE.last_update_time.astimezone(tz_sh).strftime("%Y-%m-%d %H:%M:%S %z")
            else:
                sh_time = None
            self._send_json({
                "updating": STATE.updating,
                "last_update_status": STATE.last_update_status,
                "last_update_time": sh_time,
                "last_update_duration_s": STATE.last_update_duration_s,
                "current_commit": STATE.current_commit,
                "public_dir": CFG.public_dir,
                "stocks": CFG.load_stocks(),
                "update_interval_minutes": CFG.update_interval_minutes,
                "auto_git_update": CFG.auto_git_update,
                "git_branch": CFG.git_branch,
            })
            return
        if parsed.path == "/update":
            if STATE.updating:
                self._send_json({"message": "already updating"}, code=202)
                return
            # Trigger async update
            threading.Thread(target=UPDATER.generate_report_once, daemon=True).start()
            self._send_json({"message": "update started"}, code=202)
            return
        # For all other paths, serve static files from public/
        super().do_GET()



def run_server():
    # Ensure public dir exists
    os.makedirs(CFG.public_dir, exist_ok=True)
    # Start periodic updater thread
    t = threading.Thread(target=UPDATER.loop, daemon=True)
    t.start()
    _log(f"Serving {CFG.public_dir} on 0.0.0.0:{CFG.port}")
    with HTTPServer(("0.0.0.0", CFG.port), RequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
