"""V2 Promotion UI behaviour, executed with Node against the real functions in home.html.

Regressions:
- "Checking with the token saved for …" stayed forever when the permission check
  failed (e.g. no token saved) because the error went to a different line.
- The main Settings "Save" closed the dialog and silently discarded a token typed
  under Settings → Promotion, so no promotion.dpapi was ever written.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from github_community_agent import work_center as w

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")
HTML = (Path(w.__file__).parent / "home.html").read_text(encoding="utf-8")


def _function(name: str) -> str:
    """Source of one top-level JS function (or const) from home.html, by brace matching."""
    start = HTML.index(name)
    depth, i, seen = 0, HTML.index("{", start), False
    while True:
        ch = HTML[i]
        if ch == "{":
            depth, seen = depth + 1, True
        elif ch == "}":
            depth -= 1
            if seen and depth == 0:
                return HTML[start:i + 1]
        i += 1


def _run(script: str) -> dict:
    proc = subprocess.run([NODE, "-e", script], capture_output=True, encoding="utf-8", timeout=30)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout.strip().splitlines()[-1])


PRELUDE = """
const escapeHTML=s=>String(s).replace(/[&<>"']/g,"");
const mk=()=>({textContent:"",innerHTML:"",disabled:false,value:"",open:false,onchange:null});
"""


def _preflight(request_js: str) -> dict:
    return _run(PRELUDE + _function("async function runPreflight(") + f"""
(async()=>{{
  const out=mk(), sel=mk(), approve=mk();
  sel.disabled=true; approve.disabled=true;
  await runPreflight("o/r", out, sel, approve, {request_js});
  console.log(JSON.stringify({{out:out.textContent, sel:sel.disabled, approve:approve.disabled, options:sel.innerHTML}}));
}})();
""")


def test_preflight_failure_replaces_checking_with_the_error():
    r = _preflight('async()=>{throw Error("No GitHub token is saved for o/r. Add it in Settings → Promotion.")}')
    assert "Checking" not in r["out"]
    assert r["out"] == "Permission check failed: No GitHub token is saved for o/r. Add it in Settings → Promotion."
    assert r["sel"] is True and r["approve"] is True


def test_preflight_success_enables_category():
    r = _preflight('async()=>({can_publish:true,viewer:"me",permission:"ADMIN",reasons:[],categories:["General"]})')
    assert r["out"].startswith("Ready to publish") and "Checking" not in r["out"]
    assert r["sel"] is False and "General" in r["options"]
    assert r["approve"] is True  # enabled only after a category is chosen


def test_preflight_not_ready_keeps_controls_disabled():
    r = _preflight('async()=>({can_publish:false,permission:"READ",reasons:["Discussions are disabled."],categories:[]})')
    assert r["out"].startswith("Not ready") and "Discussions are disabled." in r["out"]
    assert r["sel"] is True and r["approve"] is True


def test_post_json_times_out_instead_of_hanging():
    r = _run(_function("async function postJSON(") + """
const headers=()=>({});
// A server that never answers, but honours abort like the browser fetch.
globalThis.fetch=(p,o)=>new Promise((_,rej)=>o.signal.addEventListener("abort",()=>{const e=Error("aborted");e.name="AbortError";rej(e)}));
(async()=>{
  try{await postJSON("/x",{},50);console.log(JSON.stringify({ok:true}))}
  catch(e){console.log(JSON.stringify({ok:false,msg:e.message}))}
})();
""")
    assert r == {"ok": False, "msg": "No response after 0 seconds. Try again."}


def _pending(fields: dict, post_js: str) -> dict:
    return _run(PRELUDE + _function("function promotionState(") + _function("async function savePendingPromotion(") + f"""
const els={{}}; const $=id=>els[id]||(els[id]=mk());
const state={{promotion:{{available:true,selected:"o/a",repositories:[],selectedHasToken:false}}}};
for(const [k,v] of Object.entries({json.dumps(fields)})) $(k).value=v;
const posted=[]; const postJSON=async(path,data)=>{{posted.push({{path,data}}); {post_js} }};
(async()=>{{
  const ok=await savePendingPromotion();
  console.log(JSON.stringify({{ok, posted, token_field:$("promo-token").value, msg:$("promo-settings-message").textContent,
    open:$("settings-promotion").open, has:state.promotion.selectedHasToken, selected:state.promotion.selected}}));
}})();
""")


def test_main_save_also_saves_a_typed_promotion_token():
    r = _pending({"promo-repo": "o/a", "promo-token": "TYPED-TOKEN"},
                 'return {selected:"o/a",repositories:[{repository:"o/a"}],selected_has_token:true};')
    assert r["ok"] is True
    assert r["posted"] == [{"path": "/api/promotion/settings",
                            "data": {"repository": "o/a", "token": "TYPED-TOKEN", "remove_token": False}}]
    assert r["token_field"] == "" and r["has"] is True


def test_main_save_with_nothing_pending_does_not_touch_promotion():
    r = _pending({"promo-repo": "o/a", "promo-token": ""}, "throw Error('must not be called');")
    assert r["ok"] is True and r["posted"] == []


def test_main_save_reports_a_failed_promotion_save_and_keeps_dialog_open():
    r = _pending({"promo-repo": "o/a", "promo-token": "bad"}, 'throw Error("That does not look like a GitHub token.");')
    assert r["ok"] is False and r["open"] is True
    assert r["msg"] == "Promotion target not saved: That does not look like a GitHub token."


def test_main_save_wires_pending_promotion_before_closing():
    body = _function("async function saveSettings(")
    assert body.index("savePendingPromotion()") < body.index("closeSettings()")
