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


def _route(route: str, select: str | None = None, development: bool = True) -> dict:
    import os
    from github_community_agent import promotion as pr
    old = os.environ.pop(pr.DEV_WORK_TYPES_ENV, None)
    if development:
        os.environ[pr.DEV_WORK_TYPES_ENV] = "1"
    try:
        definitions = w.WorkService(w.Journal.__new__(w.Journal)).definitions()
    finally:
        os.environ.pop(pr.DEV_WORK_TYPES_ENV, None)
        if old is not None:
            os.environ[pr.DEV_WORK_TYPES_ENV] = old
    return _run(PRELUDE + "function unique(values){return [...new Set(values)].sort()}\n"
                + _function("function renderRoute(") + _function("function renderChoices(")
                + _function("function choose(") + f"""
const els={{}};
const elem=()=>{{const e=mk();e.classList={{toggle(){{}}}};return e}};
const $=id=>els[id]||(els[id]=elem());
globalThis.document={{querySelectorAll:()=>[]}};
const state={{route:{json.dumps(route)},definitions:{json.dumps(definitions)},settings:{{repository:"o/r"}},
             promotion:{{selected:"o/a"}}}};
renderRoute();
const options=[...$("selection").innerHTML.matchAll(/<option value="([^"]+)">([^<]+)</g)].map(m=>[m[1],m[2]]);
const first=state.definition&&state.definition.id;
{"" if select is None else f'$("selection").value={json.dumps(select)};renderChoices();'}
console.log(JSON.stringify({{label:$("selection-label").textContent,options,first,
  selected:state.definition&&state.definition.id,title:$("selected-title").textContent,
  start_disabled:$("start").disabled,note:$("planned-note").textContent}}));
""")


def test_promotion_work_type_dropdown_lists_six_and_selects_only_the_chosen_task():
    r = _route("domain")
    assert r["label"] == "Promotion — Work Type"
    assert [label for _, label in r["options"]] == [
        "GitHub Discussions", "Repository Optimization", "Reddit Promotion",
        "Developer Forums", "Technical Articles", "Social Media"]
    assert r["first"] == "promote_repository" and "automated publishing" in r["note"]
    r = _route("domain", "promote_reddit")
    assert r["selected"] == "promote_reddit" and r["title"] == "Reddit Promotion"
    assert r["start_disabled"] is False and "manual publication only" in r["note"]


def test_community_management_work_types_are_unchanged():
    r = _route("work_type")
    assert r["label"] == "Community Management — Work Type"
    # V1 Work Types keep their defined task order (as before Promotion Work Types).
    assert [v for v, _ in r["options"]] == ["Review Issues", "Review Discussions", "Draft Issue Reply",
                                            "Draft Discussion Reply", "Community Report"]
    assert r["first"] is not None and not r["first"].startswith("promote_")


def test_release_build_promotion_dropdown_lists_only_verified_work_types():
    r = _route("domain", development=False)
    assert [label for _, label in r["options"]] == ["GitHub Discussions", "Repository Optimization"]
    assert r["first"] == "promote_repository"


# --- Repository Optimization: Apply feedback in the change card ---------------------
# Regression: "Apply approved change" looked unresponsive. Its result went to one
# status line at the bottom of the panel (off-screen), a Cancel in the confirmation
# dialog showed nothing, and a refusal before writing changed nothing visible.
CHANGE_JS = (HTML[HTML.index("const CHANGE_LABEL="):HTML.index("function changeValue(")]
             + _function("function changeValue(")
             + HTML[HTML.index("const changeFeedback="):HTML.index("function renderChanges(")]
             + _function("function renderChanges("))
CHANGE = ('{id:2,kind:"topics",status:"approved",action:"Replace the repository topics.",before_value:"[]",'
          'proposed_value:"[\\"a\\"]",approved_sha256:"abc",change_sha256:"abc",result:null,error:null}')


def _apply_flow(call_js: str, confirm: str = "true", extra: str = "") -> dict:
    return _run(PRELUDE + CHANGE_JS + f"""
(async()=>{{
  const t={{id:20,repository:"o/r"}}, c={CHANGE};
  const shown=[], calls=[]; let reopened=0;
  const deps={{confirm:()=>{confirm}, show:(s,l,x)=>shown.push([s,l,x]), reopen:async()=>{{reopened++}},
              call:async(verb,data)=>{{calls.push([verb,data]); return ({call_js})()}}}};
  const out={{}};
  {extra or 'out.result=await applyChangeFlow("20:2",c,t,deps);'}
  out.shown=shown; out.calls=calls; out.reopened=reopened; out.inFlight=changesInFlight.size;
  console.log(JSON.stringify(out));
}})();
""")


def test_apply_shows_applying_then_verified_in_the_card():
    r = _apply_flow('async()=>({status:"applied",verification:{verified_utc:"2026-11-11T13:59:39+00:00"}})')
    assert r["result"] == "applied" and r["calls"] == [["apply", {"sha256": "abc"}]]
    assert [s for s, _, _ in r["shown"]] == ["applying", "verified"]
    assert r["shown"][1][1] == "Verified" and "2026-11-11T13:59:39" in r["shown"][1][2]
    assert r["reopened"] == 1 and r["inFlight"] == 0


def test_cancel_in_the_confirmation_shows_cancelled_and_sends_nothing():
    r = _apply_flow('async()=>({status:"applied"})', confirm="false")
    assert r["result"] == "cancelled" and r["calls"] == []
    assert r["shown"] == [["cancelled", "Cancelled", "Nothing was sent to GitHub."]]
    assert r["inFlight"] == 0


def test_refused_apply_shows_failed_with_the_reason():
    r = _apply_flow('async()=>{throw Error("Refused: The token\'s user has WRITE permission; ADMIN is required.")}')
    assert r["result"] == "failed"
    assert r["shown"][-1][0] == "failed" and "ADMIN is required" in r["shown"][-1][2]
    assert r["reopened"] == 1 and r["inFlight"] == 0


def test_failed_and_uncertain_results_are_shown():
    r = _apply_flow('async()=>({status:"failed",error:"GitHub changed since this proposal; nothing was applied."})')
    assert r["shown"][-1][:2] == ["failed", "Failed"] and "changed since" in r["shown"][-1][2]
    r = _apply_flow('async()=>({status:"uncertain"})')
    assert r["shown"][-1][0] == "uncertain" and "Verify on GitHub" in r["shown"][-1][2]


def test_second_click_while_applying_sends_no_second_request():
    r = _apply_flow("async()=>null", extra="""
  let finish; const pending=new Promise(res=>{finish=res});
  deps.call=async(verb,data)=>{calls.push([verb,data]); return pending};
  const first=applyChangeFlow("20:2",c,t,deps);
  await new Promise(r=>setTimeout(r,0));
  out.busyHTML=renderChanges(t,{changes:[c]});
  out.second=await applyChangeFlow("20:2",c,t,deps);
  finish({status:"applied"}); out.result=await first;""")
    assert r["second"] == "duplicate" and len(r["calls"]) == 1 and r["result"] == "applied"
    assert "Applying…" in r["busyHTML"] and 'class="primary change-apply" disabled' in r["busyHTML"]
    assert r["inFlight"] == 0


def test_change_status_is_rendered_inside_its_own_card():
    r = _run(PRELUDE + CHANGE_JS + f"""
const t={{id:20,repository:"o/r"}}, c={CHANGE};
changeFeedback[changeKey(t,c)]={{state:"failed",label:"Failed",text:"Refused: ADMIN is required."}};
const html=renderChanges(t,{{changes:[c,{{...c,id:3,status:"proposed"}}]}});
const card2=html.slice(html.indexOf('data-change="2"'), html.indexOf('data-change="3"'));
console.log(JSON.stringify({{card2, all:html}}));
""")
    assert 'class="change-status change-status-failed"' in r["card2"] and "ADMIN is required" in r["card2"]
    assert r["all"].count("ADMIN is required") == 1  # only in change #2's card
    assert r["card2"].index("change-apply") < r["card2"].index("change-status")  # right below the button


def test_activity_history_labels_change_events():
    r = _run(PRELUDE + HTML[HTML.index("const CHANGE_EVENTS="):HTML.index("function renderActivity(")] + """
console.log(JSON.stringify([changeEventLabel("change#2:apply_refused:permission"),
  changeEventLabel("change#3:applied_verified"), changeEventLabel("created"), changeEventLabel("change#1:bogus")]));
""")
    assert r == ["Change #2: apply refused — nothing was changed (insufficient permission)",
                 "Change #3: applied and verified on GitHub", "", ""]
