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


def test_promotion_work_type_dropdown_lists_platform_work_types_and_selects_only_the_chosen_task():
    r = _route("domain")
    assert r["label"] == "Promotion — Work Type"
    assert [label for _, label in r["options"]] == [
        "GitHub Discussions", "Repository Optimization", "Reddit Promotion",
        "Developer Forums", "Technical Articles", "Bluesky"]  # no generic "Social Media"
    assert r["first"] == "promote_repository" and "automated publishing" in r["note"]
    r = _route("domain", "promote_reddit")
    assert r["selected"] == "promote_reddit" and r["title"] == "Reddit Promotion"
    assert r["start_disabled"] is False and "manual publication only" in r["note"]


def test_bluesky_new_task_says_the_agent_publishes_after_exact_approval():
    r = _route("domain", "promote_bluesky")
    assert r["selected"] == "promote_bluesky" and r["title"] == "Bluesky" and r["start_disabled"] is False
    assert "the Agent publishes it from the connected project Bluesky account" in r["note"]
    assert "yourself" not in r["note"] and "manual" not in r["note"]
    released = _route("domain", development=False)
    assert "Bluesky" not in [label for _, label in released["options"]]  # unverified: hidden in releases


def test_bluesky_task_card_has_no_manual_publication_controls():
    start = HTML.index("if(bsky){")
    block = HTML[start:HTML.index("continue;", start)]
    assert "Post text (published exactly as approved)" in block and "Label (not published)" in block
    assert "blueskyHTML(a,d)" in block
    for manual in ("promo-approve-manual", "manual publication", "yourself", "promo-preflight", "promo-publish"):
        assert manual not in block
    meta = HTML[HTML.index("const manual=a.channel"):HTML.index("if(manual&&(MANUAL_PUBLISHED")]
    assert "the Agent publishes this exact post from the connected project account after your approval" in meta
    # Legacy Social Media drafts no longer get a Bluesky box (no silent destination).
    assert 'a.channel==="social_media"?blueskyHTML' not in HTML


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


# -- Reddit: Record Manual Publication -----------------------------------------------------

MANUAL_JS = (HTML[HTML.index("const ACTION_EVENTS="):HTML.index("function renderActivity(")]
             + HTML[HTML.index("const MANUAL_PUBLISHED="):HTML.index("function renderPromotionPanel(")])
READY = ('{id:5,channel:"reddit",status:"ready_manual",category:"coolgithubprojects",approved_sha256:"s1",'
         'published_url:null,post_id:null,verification:null}')
POST_URL = "https://www.reddit.com/r/coolgithubprojects/comments/1abc2de/x/"


def _manual(script: str) -> dict:
    return _run(PRELUDE + MANUAL_JS + "\n(async()=>{const a=" + READY + ";const out={};" + script
                + "console.log(JSON.stringify(out));})();")


def test_ready_reddit_draft_shows_the_record_form_with_confirmation():
    r = _manual("out.html=manualPublicationHTML(a);")
    html = r["html"]
    assert "Record manual publication" in html and "promo-post-url" in html and "promo-post-confirm" in html
    assert "r/coolgithubprojects" in html and "nothing is posted" in html
    assert "verified" not in html.lower()


def test_record_flow_requires_url_and_confirmation_and_reports_user_confirmed_only():
    r = _manual(f"""
const calls=[]; const deps={{confirm:()=>true, call:async(v,d)=>{{calls.push([v,d]);
  return {{status:"published_user_confirmed",verified:false,post_id:"1abc2de",subreddit:"coolgithubprojects"}}}}}};
out.noUrl=await recordPublicationFlow(a,"  ",true,deps);
out.noConfirm=await recordPublicationFlow(a,"{POST_URL}",false,deps);
out.cancel=await recordPublicationFlow(a,"{POST_URL}",true,{{...deps,confirm:()=>false}});
out.callsBefore=calls.length;
out.ok=await recordPublicationFlow(a,"{POST_URL}",true,deps);
out.calls=calls;""")
    assert "Paste the Reddit post URL" in r["noUrl"] and "Tick the confirmation" in r["noConfirm"]
    assert r["cancel"] == "Cancelled. Nothing was recorded." and r["callsBefore"] == 0
    assert r["calls"] == [["record_publication", {"url": POST_URL, "confirmed": True, "sha256": "s1"}]]
    assert r["ok"].startswith("Recorded as user-confirmed") and "NOT independently verified" in r["ok"]


def test_refused_record_is_not_reported_as_success():
    r = _manual(f"""
try{{await recordPublicationFlow(a,"{POST_URL}",true,{{confirm:()=>true,
  call:async()=>{{throw Error("This post is in r/programming, but the approved subreddit is r/coolgithubprojects.")}}}});
  out.result="returned"}}catch(e){{out.result="threw:"+e.message}}""")
    assert r["result"].startswith("threw:") and "approved subreddit" in r["result"]


def test_user_confirmed_and_verified_states_are_clearly_distinguished():
    r = _manual("""
const base={...a,published_url:"https://www.reddit.com/r/coolgithubprojects/comments/1abc2de/",post_id:"1abc2de"};
out.confirmed=manualPublicationHTML({...base,status:"published_user_confirmed"});
out.unavailable=manualPublicationHTML({...base,status:"published_user_confirmed",
  verification:{checked_utc:"2026-11-11T20:00:00+00:00",outcome:"unavailable",reason:"unavailable_http_403"}});
out.mismatch=manualPublicationHTML({...base,status:"published_user_confirmed",
  verification:{checked_utc:"t",outcome:"mismatch",checks:{found:true,title:true,body:false}}});
out.verified=manualPublicationHTML({...base,status:"published_verified",
  verification:{checked_utc:"t",outcome:"verified",checks:{found:true,body:true},score:5,num_comments:2}});
out.bad=manualPublicationHTML({...base,status:"published_user_confirmed",published_url:"javascript:alert(1)"});
out.msgs=[verifyMessage({outcome:"verified"}),verifyMessage({outcome:"unavailable",reason:"Reddit refused the public read (HTTP 403)."}),
  verifyMessage({outcome:"removed"})];""")
    assert "User-confirmed only — NOT independently verified" in r["confirmed"] and "Not checked yet" in r["confirmed"]
    assert "Independently verified" not in r["confirmed"] and "Check on Reddit" in r["confirmed"]
    assert "NOT independently verified" in r["unavailable"] and "HTTP 403" in r["unavailable"]
    assert "failed: body" in r["mismatch"] and "NOT independently verified" in r["mismatch"]
    assert "Independently verified on Reddit" in r["verified"] and "score 5" in r["verified"]
    assert "javascript:" not in r["bad"] and "(no URL)" in r["bad"]
    assert r["msgs"][0].startswith("Independently verified")
    assert "nothing new was verified" in r["msgs"][1] and "user-confirmed only" in r["msgs"][2]


def test_activity_history_labels_manual_publication_events():
    r = _manual("""out.labels=[actionEventLabel("action#5:approved_manual"),
  actionEventLabel("action#5:manual_record_refused:subreddit_mismatch"),
  actionEventLabel("action#5:manual_recorded_user_confirmed"),
  actionEventLabel("action#5:manual_verify_unavailable:unavailable_http_403"),
  actionEventLabel("action#5:manual_verified"),actionEventLabel("action#5:bogus"),actionEventLabel("created")];""")
    assert r["labels"] == [
        "Draft #5: approved for manual publication",
        "Draft #5: publication not recorded (post is in a different subreddit)",
        "Draft #5: publication recorded — user-confirmed, not independently verified",
        "Draft #5: Reddit could not be read — not verified (HTTP 403)",
        "Draft #5: independently verified on Reddit", "", ""]


def test_reddit_draft_asks_for_the_subreddit_before_approval():
    block = HTML[HTML.index("if(manual){"):HTML.index("continue;", HTML.index("if(manual){"))]
    assert 'class="promo-subreddit"' in block and 'a.channel==="reddit"' in block
    assert "promo-publish" not in block and "promo-preflight" not in block


# -- Bluesky Work Type ----------------------------------------------------------------------

BSKY_JS = (HTML[HTML.index("const ACTION_EVENTS="):HTML.index("function renderActivity(")]
           + HTML[HTML.index("const BLUESKY_LOCKED="):HTML.index("function renderPromotionPanel(")]
           + _function("function blueskyStatusText("))
BSKY_D = ('{bluesky_available:true,bluesky_account:{available:true,connected:true,handle:"proj.bsky.social",'
          'did:"did:plc:aaaa"}}')
BSKY_A = ('{id:7,channel:"bluesky",status:"draft",approved_sha256:null,verification:null,'
          'bluesky:{text:"I maintain it https://github.com/o/r",graphemes:36,bytes:36,facets:[{}],issues:[],'
          'account_did:"did:plc:aaaa",approval_sha256:"s1",approved_did:null,uri:null,cid:null,url:null}}')


def _bsky(script: str) -> dict:
    return _run(PRELUDE + BSKY_JS + "\n(async()=>{const d=" + BSKY_D + ";const a=" + BSKY_A + ";const out={};"
                + script + "console.log(JSON.stringify(out));})();")


def test_bluesky_card_shows_exact_text_counts_and_account_before_approval():
    r = _bsky("""out.html=blueskyHTML(a,d);out.none=blueskyHTML(a,{...d,bluesky_available:false});
out.noacct=blueskyHTML({...a,bluesky:{...a.bluesky,approval_sha256:null}},{...d,bluesky_account:{connected:false}});""")
    assert "I maintain it https://github.com/o/r" in r["html"] and "36/300 characters" in r["html"]
    assert "36/3000 bytes" in r["html"] and "@proj.bsky.social" in r["html"] and "bsky-approve" in r["html"]
    assert "bsky-publish" not in r["html"] and r["none"] == ""
    assert "No Bluesky account connected" in r["noacct"] and 'bsky-approve" disabled' in r["noacct"]


def test_bluesky_approve_and_publish_flows_confirm_and_report_only_server_results():
    r = _bsky("""
const calls=[];const deps={confirm:()=>true,call:async(v,x)=>{calls.push([v,x]);
  return v==="bluesky_publish"?{status:"bluesky_published",url:"https://bsky.app/profile/did:plc:aaaa/post/3k"}:{status:"bluesky_approved"}}};
out.cancel=await blueskyApproveFlow(a,d,{...deps,confirm:()=>false});
out.approve=await blueskyApproveFlow(a,d,deps);
const ready={...a,status:"bluesky_approved",approved_sha256:"s2",bluesky:{...a.bluesky,approved_did:"did:plc:aaaa"}};
out.readyHTML=blueskyHTML(ready,d);
out.publish=await blueskyPublishFlow(ready,d,deps);
out.uncertain=await blueskyPublishFlow(ready,d,{...deps,call:async()=>({status:"bluesky_uncertain"})});
out.failed=await blueskyPublishFlow(ready,d,{...deps,call:async()=>({status:"bluesky_failed",error:"HTTP 400"})});
out.calls=calls;""")
    assert r["cancel"] == "Cancelled. Nothing was approved."
    assert r["calls"][0] == ["bluesky_approve", {"sha256": "s1"}]
    assert r["calls"][1] == ["bluesky_publish", {"sha256": "s2"}]
    assert "bsky-publish" in r["readyHTML"] and "refuses any other account" in r["readyHTML"]
    assert "NOT independently verified" in r["publish"]
    assert "Do not publish again" in r["uncertain"] and "nothing was posted" in r["failed"]


def test_bluesky_published_and_verified_states_are_distinct_and_safe():
    r = _bsky("""
const pub={...a,status:"bluesky_published",bluesky:{...a.bluesky,uri:"at://did:plc:aaaa/app.bsky.feed.post/3k",
  cid:"bafy",url:"https://bsky.app/profile/did:plc:aaaa/post/3k"}};
out.pub=blueskyHTML(pub,d);
out.ver=blueskyHTML({...pub,status:"bluesky_verified",verification:{checked_utc:"t",outcome:"verified",checks:{found:true},likeCount:2}},d);
out.mis=blueskyHTML({...pub,verification:{checked_utc:"t",outcome:"mismatch",checks:{found:true,text:false}}},d);
out.bad=blueskyHTML({...pub,bluesky:{...pub.bluesky,url:"javascript:alert(1)"}},d);
out.unc=blueskyHTML({...pub,status:"bluesky_uncertain"},d);
out.msgs=[blueskyVerifyMessage({outcome:"verified"}),blueskyVerifyMessage({outcome:"not_found"}),
  blueskyVerifyMessage({outcome:"unavailable",reason:"HTTP 503"})];""")
    assert "NOT independently verified yet" in r["pub"] and "at://did:plc:aaaa/app.bsky.feed.post/3k" in r["pub"]
    assert "CID bafy" in r["pub"] and "bsky-verify" in r["pub"]
    assert "Independently verified on Bluesky" in r["ver"] and "2 likes" in r["ver"]
    assert "failed: text" in r["mis"] and "NOT independently verified" in r["mis"]
    assert "javascript:" not in r["bad"] and "(no URL)" in r["bad"]
    assert "bsky-reconcile" in r["unc"] and "Do not approve or publish again" in r["unc"]
    assert r["msgs"][0].startswith("Independently verified") and "NOT verified" in r["msgs"][1]
    assert "unchanged" in r["msgs"][2]


def test_bluesky_settings_status_and_activity_labels():
    r = _bsky("""out.s=[blueskyStatusText({available:false}),blueskyStatusText({available:true,connected:false}),
  blueskyStatusText({available:true,connected:true,handle:"proj.bsky.social",did:"did:plc:aaaa"})];
out.l=[actionEventLabel("action#7:bluesky_published"),actionEventLabel("action#7:bluesky_publish_refused:account_mismatch"),
  actionEventLabel("action#7:bluesky_failed:http_429"),actionEventLabel("action#7:bluesky_verified")];""")
    assert r["s"] == ["", "No Bluesky account connected.",
                      "Connected: @proj.bsky.social (did:plc:aaaa). The app password is stored encrypted."]
    assert r["l"] == ["Draft #7: published on Bluesky (not yet verified)",
                      "Draft #7: Bluesky publish refused — nothing was sent (different Bluesky account)",
                      "Draft #7: Bluesky publication failed — nothing was posted (http_429)",
                      "Draft #7: independently verified on Bluesky"]


def test_bluesky_settings_never_prefill_or_echo_the_app_password():
    block = HTML[HTML.index('<div id="bluesky-settings"'):HTML.index("</details>", HTML.index('<div id="bluesky-settings"'))]
    assert 'type="password" id="bsky-password"' in block and "hidden" in block
    load = _function("async function loadBlueskySettings(")
    assert '$("bsky-password").value=""' in load and "app_password" not in load


# -- Settings → Promotion platform selector --------------------------------------------------

SELECTOR_JS = (HTML[HTML.index("const PROMOTION_PLATFORMS="):HTML.index("function promotionPlatforms(")]
               + _function("function promotionPlatforms(") + _function("function renderPromotionPlatforms(")
               + _function("function selectPromotionPlatform("))


def _selector(script: str) -> dict:
    return _run(PRELUDE + SELECTOR_JS + """
const els={}; const $=id=>els[id]||(els[id]=mk());
const sent=[]; const postJSON=async(p,d)=>{sent.push(p)}; const getJSON=async p=>{sent.push(p)};
const state={promotion:{selected:"o/a"},selectedTask:{id:7,channel:"social_media"}};
const out={};
""" + script + "\nconsole.log(JSON.stringify(out));")


def test_platform_selector_lists_only_supported_platforms():
    r = _selector("""
state.promotionPlatforms={bluesky:false}; renderPromotionPlatforms(); out.off=$("promo-platform").innerHTML;
state.promotionPlatforms={bluesky:true,mastodon:true,linkedin:true}; renderPromotionPlatforms(); out.on=$("promo-platform").innerHTML;
""")
    assert 'value="github"' in r["off"] and "bluesky" not in r["off"]
    assert 'value="github"' in r["on"] and 'value="bluesky"' in r["on"] and "Bluesky (development)" in r["on"]
    for unsupported in ("mastodon", "linkedin", "reddit", "x\""):
        assert unsupported not in r["on"].lower()


def test_switching_platform_shows_one_panel_and_changes_nothing_else():
    r = _selector("""
state.promotionPlatforms={bluesky:true}; renderPromotionPlatforms();
$("promo-token").value="typed-gh"; $("bsky-password").value="typed-bs"; $("bsky-handle").value="proj.bsky.social";
out.github=[$("promo-github-settings").hidden,$("bluesky-settings").hidden];
selectPromotionPlatform("bluesky");
out.bluesky=[$("promo-github-settings").hidden,$("bluesky-settings").hidden,$("promo-platform").value];
selectPromotionPlatform("github");
out.back=[$("promo-github-settings").hidden,$("bluesky-settings").hidden];
out.fields=[$("promo-token").value,$("bsky-password").value,$("bsky-handle").value];
out.sent=sent; out.task=state.selectedTask; out.promo=state.promotion;
""")
    assert r["github"] == [False, True]
    assert r["bluesky"] == [True, False, "bluesky"]
    assert r["back"] == [False, True]
    # Switching deletes, overwrites and sends nothing, and never touches a Task.
    assert r["fields"] == ["typed-gh", "typed-bs", "proj.bsky.social"] and r["sent"] == []
    assert r["task"] == {"id": 7, "channel": "social_media"} and r["promo"] == {"selected": "o/a"}


def test_unavailable_bluesky_falls_back_to_github():
    r = _selector("""
state.promotionPlatforms={bluesky:true}; renderPromotionPlatforms(); selectPromotionPlatform("bluesky");
state.promotionPlatforms={bluesky:false}; renderPromotionPlatforms();
out.v=[state.promotionPlatform,$("promo-github-settings").hidden,$("bluesky-settings").hidden];
selectPromotionPlatform("unknown"); out.u=[state.promotionPlatform,$("bluesky-settings").hidden];
""")
    assert r["v"] == ["github", False, True] and r["u"] == ["github", True]


def test_each_platform_panel_holds_only_its_own_credentials():
    gh = HTML[HTML.index('<div id="promo-github-settings"'):HTML.index('<div id="bluesky-settings"')]
    bs_end = HTML.index("</details>", HTML.index('<div id="bluesky-settings"'))
    bs = HTML[HTML.index('<div id="bluesky-settings"'):bs_end]
    assert 'id="promo-repo"' in gh and 'id="promo-token"' in gh and "bsky-" not in gh
    assert 'id="bsky-handle"' in bs and 'id="bsky-password"' in bs and "promo-token" not in bs
    assert 'id="promo-platform"' in HTML[HTML.index('<details id="settings-promotion"'):HTML.index('<div id="promo-github-settings"')]
    # Each save sends its own fields to its own endpoint only.
    save_gh = _function("async function savePromotion(") + _function("async function savePendingPromotion(")
    save_bs = _function("async function saveBluesky(")
    assert "/api/promotion/settings" in save_gh and "bsky" not in save_gh and "/api/promotion/bluesky" not in save_gh
    assert "/api/promotion/bluesky" in save_bs and "promo-token" not in save_bs and "/api/promotion/settings" not in save_bs
    # The selector itself never saves or removes anything.
    assert "postJSON" not in SELECTOR_JS and "getJSON" not in SELECTOR_JS
