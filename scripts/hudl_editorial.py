"""Editorial profiles for the existing Shot Tracer renderer.

This module does not fetch, approve, publish or invent facts about the source.
CSV keywords are demand inputs, not verified sporting information. The caller
owns selection, evidence and approval; all returned profiles remain drafts.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit


CATEGORIES = {
    "basketball-skills", "basketball-training", "basketball-teams",
    "basketball-schedules", "basketball-video", "scouting",
    "sports-video", "fan-basketball",
}
EXAMPLE = "/videos/basketball-shot-tracer-example"


def _text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _has(text, pattern):
    return bool(re.search(pattern, text, flags=re.I))


def _query_question(keyword, fallback):
    question = re.sub(r"^whats\s+", "what is ", keyword.strip(), flags=re.I)
    question = re.sub(r"^what field goal\b", "what is a field goal", question, flags=re.I)
    if _has(question, r"^(what|what's|how|why|when|where|can|does|do|is|are)\b"):
        return question[:1].upper() + question[1:].rstrip("?") + "?"
    return fallback


def _source(row, context):
    value = _text(context.get("source_url") or row.get("URL"))
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return None
    return value


def _section(heading, text, subheading, subtext):
    return {"heading": heading, "text": text,
            "subsections": [{"heading": subheading, "text": subtext}]}


def _source_kind(context, source):
    value = _text(context.get("source_type")).lower()
    path = urlsplit(source or "").path.lower()
    for kind, pattern in (
        ("schedule", r"schedule|calendar|fixture"),
        ("roster", r"roster|lineup"),
        ("profile", r"profile|athlete|player"),
        ("video", r"video|watch|broadcast|highlight"),
        ("team", r"team|organization"),
    ):
        if _has(value + " " + path, pattern):
            return kind
    return "reference"


def _intent(keyword, category, context, source):
    """Choose an editorial task from explicit query modifiers first."""
    if _source_kind(context, source) == "profile":
        return "profile"
    if _has(keyword, r"\b(field.goal|fg|fgm|fga)\b"):
        return "field-goal"
    if _has(keyword, r"\bturnovers?\b"):
        return "turnover"
    if _has(keyword, r"\bfouls?\b"):
        return "foul"
    if _has(keyword, r"\bcompress\w*\b"):
        return "compression"
    if _has(keyword, r"\b(schedule|schedules|calendar|fixtures?|tickets?)\b"):
        return "schedule"
    if _has(keyword, r"\b(live|livestream|streaming|stream|watch|broadcast)\b"):
        return "watch"
    if _has(keyword, r"\b(rosters?|lineups?|depth chart)\b"):
        return "roster"
    if _has(keyword, r"\b(scores?|results?|stats?|statistics|standings|rankings?)\b"):
        return "stats"
    if _has(keyword, r"\b(scout|scouting|recruit|recruiting|recruitment|scholarships?)\b"):
        return "scouting"
    if _has(keyword, r"\b(dribbl\w*|crossover|ball.handling|handles)\b"):
        return "handling"
    if _has(keyword, r"\b(pass|passes|passing|assist|assists)\b"):
        return "passing"
    if _has(keyword, r"\b(defen\w*|rebound\w*|blocks?|steals?)\b"):
        return "defense"
    if _has(keyword, r"\b(layups?|lay.up|free.throws?|jump.shots?|bank.shots?|hook.shots?|dunks?|three.point|3.point|shot.types?|types.of.*shots?|shooting)\b"):
        return "shooting"
    if _has(keyword, r"\b(drills?|workouts?|training|practice|exercises?)\b"):
        return "training"
    if _has(keyword, r"\b(edit\w*|software|highlights?|reels?|clips?|video|record\w*|filming|camera|app)\b"):
        return "editing"
    if _has(keyword, r"\b(rules?|violations?|fouls?|what.is|meaning|definition)\b"):
        return "explainer"
    source_kind = _source_kind(context, source)
    if category == "basketball-schedules" or source_kind == "schedule":
        return "schedule"
    if category == "scouting":
        return "scouting"
    if source_kind == "profile":
        return "profile"
    if source_kind == "roster":
        return "roster"
    return {
        "basketball-skills": "skill",
        "basketball-training": "training",
        "basketball-video": "editing",
        "sports-video": "editing",
        "basketball-teams": "team",
        "fan-basketball": "fan",
    }.get(category, "fan")


def _shot_focus(keyword):
    """Only basic, stable visual descriptions; never a coaching prescription."""
    if _has(keyword, r"free.throw"):
        return (
            "Keep the free-throw setup in the frame",
            "A free throw is an uncontested attempt from the free-throw line. Keep the setup, release and finish in your recording so its context remains visible.",
            "Include the ball before release",
            "Start the excerpt before the shooting motion and leave room after the attempt. A cropped ball near the rim alone does not show the full action.",
        )
    if _has(keyword, r"lay.up|layup"):
        return (
            "Show the approach as well as the layup",
            "A layup is a close-range finish. Your example is easier to understand when the recording includes the approach and release, rather than beginning with the ball already at the basket.",
            "Keep the player's path visible",
            "Avoid cropping away the final steps or the backboard. The tracer illustrates the ball after release; the original footage supplies the rest of the movement.",
        )
    if _has(keyword, r"bank.shot"):
        return (
            "Keep the backboard contact visible",
            "A bank shot uses the backboard on its way toward the basket. Include the board and rim so viewers can see that detail instead of relying on the clip's label.",
            "Review the bounce in the original",
            "Check the unedited frames around backboard contact. If the effect does not follow the visible flight, keep the original as the clearer reference.",
        )
    if _has(keyword, r"jump.shot|jumper|pull.up|step.back|fadeaway"):
        return (
            "Retain the movement before the jump shot",
            "A jumper is released while the shooter is airborne. A catch, dribble or step before the release can change what a viewer needs to see, so keep the relevant setup in your example.",
            "Show the setup without judging technique",
            "Use a range that includes the catch or final dribble when it matters. The visual trail does not rate footwork, balance or shooting form.",
        )
    if _has(keyword, r"three.point|3.point"):
        return (
            "Keep the court markings in your shot example",
            "If you describe an attempt as a three-pointer, the relevant court line and release position should be visible. Do not infer the distance or score from a tightly cropped ball-flight clip.",
            "Avoid assigning points from the effect",
            "The tracer does not identify the rule set or award points. Use the full recording and the competition's own rules when a scoring claim matters.",
        )
    if _has(keyword, r"dunk"):
        return (
            "Show the approach and rim action",
            "For a dunk recording, preserve the approach, the finish at the rim and the landing in the original. A very short ball path may add little to a play that is already clear.",
            "Choose the clearer presentation",
            "Compare the traced preview with the original. Keep the version that makes the action easier to follow rather than adding an effect just because it is available.",
        )
    return (
        "Match the shot description to what is visible",
        "A jumper, layup and free throw describe different basketball actions. Some descriptions can overlap: a jumper can also use the backboard. Choose a label that your complete recording supports.",
        "Keep one example focused",
        "Include the approach, release and finish of one attempt. A tracer highlights the ball's flight; it does not automatically classify the shot or evaluate technique.",
    )


def _modifier_tip(keyword):
    """Concrete filming or logging choices from modifiers, not random variation."""
    if _has(keyword, r"\b(left|right|weak.hand|off.hand)\b"):
        return ("Make the side of the action unambiguous",
                "Keep the original orientation and identify whose left or right you mean in your notes. A mirrored recording can make a side-based description confusing.")
    if _has(keyword, r"\b(corner|wing|baseline|elbow|top.of.the.key)\b"):
        return ("Retain the court location",
                "Include enough court markings to show the starting spot. A close crop of the ball alone cannot establish whether the play began at the corner, wing or another location.")
    if _has(keyword, r"\b(catch.and.shoot|catch.shoot|catching)\b"):
        return ("Keep the catch before the release",
                "Start before the pass arrives so the catch and shot remain one sequence. The tracer shows the shot's flight, while the source recording shows the preparation.")
    if _has(keyword, r"\b(transition|fast.break)\b"):
        return ("Keep the lead-in to the finish",
                "A transition finish loses context when the excerpt starts under the rim. Preserve enough of the approach to show how the ball reached the shooter.")
    if _has(keyword, r"\b(at.home|home|indoor|outdoor|driveway)\b"):
        return ("Check your recording environment",
                "Make sure the ball remains visible against the wall, sky or background throughout the attempt. Retain the original if the preview loses the flight in part of the frame.")
    if _has(keyword, r"\b(youth|kids|beginners?|beginner|junior|middle.school)\b"):
        return ("Keep the example simple to follow",
                "Use one clearly framed attempt and a plain description of the action. A short clip should illustrate what happened, not serve as an automatic skill grade.")
    if _has(keyword, r"\b(women|women's|girls|girls')\b"):
        return ("Identify the correct team context",
                "When checking a team reference, confirm the women's or girls' team, season and level. Similar organization names can lead to different squads and separate records.")
    if _has(keyword, r"\b(jv|junior.varsity|varsity|freshman|freshmen)\b"):
        return ("Check the squad level before using a reference",
                "Keep varsity, junior-varsity and freshman records separate. Match the level shown by the source rather than inferring it from a school name alone.")
    return ("Save a source timestamp with the excerpt",
            "Record the start and end time in the original file. This gives you a reliable way to recover the surrounding play after saving a short traced copy.")


def _source_cues(context, source):
    """Describe URL labels as labels, never as a verified entity match."""
    entity = _text(context.get("entity"))
    if entity.lower() in {"tickets", "schedule", "watch", "video", "roster", "about"}:
        entity = ""
    parts = [p for p in urlsplit(source or "").path.split("/") if p]
    cues = []
    if entity:
        cues.append(f'the organization label "{entity}"')
    if "team" in parts:
        i = parts.index("team")
        if i + 2 < len(parts) and not parts[i + 2].isdigit():
            squad = parts[i + 2].replace("-", " ")
            if squad not in {"schedule", "watch", "roster", "tickets"}:
                cues.append(f'the team-path label "{squad}"')
    if len(parts) >= 3 and parts[0] == "usa" and len(parts[1]) == 2:
        city = parts[2].replace("-", " ")
        cues.append(f'the location cue "{city}, {parts[1].upper()}"')
    if not cues:
        return ""
    kind = _source_kind(context, source)
    return f"The related link leads to a {kind} path containing " + ", ".join(cues) + ". Confirm that these identify the school, squad or person you meant before relying on that page."


def _editorial(keyword, category, context, source, intent, non_basketball):
    """Return two intent-led sections and two task-specific FAQ pairs."""
    reference = (
        "The related source is linked below. Check it directly for the details it actually publishes."
        if source else
        "Check the relevant team's or event organizer's current source before relying on a date, name or result."
    )
    modifier_h, modifier_t = _modifier_tip(keyword)
    source_cues = _source_cues(context, source)
    if intent == "field-goal":
        if _has(keyword, r"percent|percentage|fg%"):
            answer = "Field-goal percentage compares made field goals with field-goal attempts: divide makes by attempts and multiply by 100. Keep free throws separate, and do not calculate a percentage from a highlight reel that omits missed attempts."
        elif _has(keyword, r"made|fgm"):
            answer = "FGM means field goals made: successful baskets from normal play. Both two-point and three-point makes contribute to this count; free throws are recorded separately. Keep the count of made baskets separate from the points they produce."
        else:
            answer = "FG means field goal: a basket from normal play, excluding free throws. In a box score, distinguish made field goals from attempts; a shot clip alone does not establish the player's full game totals."
        first = _section(
            f"Understand {keyword} before labeling the clip", answer,
            "Check which box-score column you are reading",
            "Read the column heading rather than treating every shooting number as points. Keep the relevant game or session with your notes so totals from different recordings do not get mixed together.",
        )
        second = _section(
            "Use a visible attempt as your basketball video example",
            "Keep the release and result in frame. If a player or the rim is obscured, mark the outcome as unclear in your personal log rather than counting the attempt from a decorative trail.",
            modifier_h, modifier_t,
        )
        faq = [
            [_query_question(keyword, f"What does {keyword} refer to?"), answer],
            ["Will HoopCut count my field goals automatically?", "No. Shot Tracer adds a visual effect. Keep any manually observed attempts separate from official statistics and retain the complete source recording."],
        ]
    elif intent == "turnover":
        answer = "A turnover records possession lost to the opponent through an error or violation, such as an intercepted pass or traveling. It is different from an ordinary missed shot followed by a defensive rebound."
        first = _section(
            f"Understand {keyword} in the full possession", answer,
            "Keep the action before the possession changes",
            "Start the original sequence early enough to show the pass, dribble or violation involved. A clip beginning after the change of possession cannot explain how the ball was lost.",
        )
        second = _section(
            "Trace a later basketball shot as a separate highlight",
            "If the same recording continues into a visible attempt, you can trace that shot in a short copy. Keep the full source for the turnover context; the effect does not detect a possession change or assign a turnover.",
            modifier_h, modifier_t,
        )
        faq = [
            [_query_question(keyword, f"What does {keyword} mean?"), answer],
            ["Does the tracer identify turnovers?", "No. It highlights the flight of a basketball shot. Use the original possession and an appropriate statistics source when a turnover decision matters."],
        ]
    elif intent == "foul":
        if _has(keyword, r"loose.ball"):
            answer = "Under NBA rules, a loose-ball foul is a personal foul during a period when neither team controls the ball; punching and flagrant fouls have separate treatment. Check the applicable competition's rules for its terminology and penalties."
        elif _has(keyword, r"reach.in"):
            answer = "Reaching toward the ball alone does not establish a foul. In NBA rules, the relevant question is whether the defender makes illegal contact; the full interaction matters, not just the position of an extended arm."
        else:
            answer = "NBA Rule 12 separates technical and personal fouls and covers situations such as offensive, loose-ball, flagrant and double fouls. These labels describe different contexts; use the competition's own rulebook for the applicable penalties."
        first = _section(
            f"Understand {keyword} in its rules context", answer,
            "Keep the contact and surrounding action visible",
            "A short ball-flight crop can omit the part of the play that matters. Retain the full source and the official call rather than using a tracer to decide whether contact was illegal.",
        )
        second = _section(
            "Use the effect only to illustrate a visible basketball shot",
            "If your recording includes a shot, keep the release and result in a separate traced copy. The ball trail illustrates that attempt; it does not detect fouls, identify contact or reverse a referee's decision.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Where can I check the rule for {keyword}?", "The NBA Rule 12 reference below covers NBA foul rules. Use the rulebook for your own competition if it follows a different rules system."],
            ["Can a traced clip prove a foul occurred?", "No. Keep the original sequence and relevant officiating context. This tool is a visual basketball effect, not a referee or contact-detection system."],
        ]
    elif intent == "compression":
        first = _section(
            f"Prepare your file before using {keyword}",
            "Compression and shot tracing are different steps. If your recording exceeds the uploader's 512 MB limit, use a separate video compression tool to create a smaller copy. Keep the original and review the smaller file for a still-visible ball and hoop.",
            "Protect the detail needed for the tracer",
            "Aggressive compression can make a small moving ball hard to distinguish. Compare the compressed copy with the original before choosing it for a basketball effect.",
        )
        second = _section(
            "Bring the prepared basketball clip to the shared uploader",
            "Use a saved MP4, MOV or WebM file within the size limit. Choose up to 30 seconds and check its ball trail in the preview. This page adds Shot Tracer; it does not provide a file compressor or replace the separate compression tool.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Is HoopCut a replacement for {keyword}?", "No. Prepare any necessary file compression in a separate tool. HoopCut's workflow here adds a visual tracer to an eligible saved basketball recording."],
            ["How small does my upload need to be?", "The shared uploader accepts MP4, MOV or WebM files up to 512 MB. Check the ball remains visible after any separate compression step."],
        ]
    elif intent == "schedule":
        first = _section(
            f"Check the schedule context for {keyword}",
            "Match the team, sport, season and date before planning around a listing. Check the venue, stated time zone and any updates rather than treating an old search result as the current schedule. " + reference + (" " + source_cues if source_cues else ""),
            "Confirm the event before labeling a recording",
            "A schedule lists a planned event; it does not prove that a saved clip came from that game. Use the recording date and your own source notes to establish that connection.",
        )
        second = _section(
            "Organize your own basketball footage by session",
            "Keep a folder for the recording date and write down each excerpt's timestamp. If your own basketball session is separate from the event you follow, label it as practice or pickup instead of borrowing an event title.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Where should I confirm {keyword}?", "Use the related source and check the team, season, venue and time zone. This Tracer page does not maintain a live schedule or issue tickets."],
            ["Should I label my clip with a scheduled game's name?", "Only when you can verify that the recording shows that event. Otherwise describe your own basketball session and retain its recording date."],
        ]
    elif intent == "watch":
        first = _section(
            f"Find the viewing source for {keyword}",
            "A live listing, replay and short highlight can be different items. Check the source's date, event title and access instructions before assuming a recording is available. " + reference,
            "Keep the viewing link separate from the editing file",
            "This uploader works with a saved basketball recording you provide. A stream URL is not a local clip, and the tool does not fetch broadcasts from another website.",
        )
        second = _section(
            "Prepare a basketball recording you can edit",
            "Use your own footage or a file you have permission to edit and share. Retain the original and select a clear shot rather than presenting the shared demonstration as the event you were trying to watch.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Can I watch {keyword} on this page?", "This page provides the basketball Tracer and a generic effect demonstration. Use the linked source to check its current viewing options and access terms."],
            ["Can I paste a live-stream link into the uploader?", "No. Use a saved basketball video file. The shared workflow does not download broadcasts, bypass access requirements or turn a stream link into footage."],
        ]
    elif intent in {"roster", "profile", "team", "fan"}:
        profile = intent == "profile"
        focus = "profile" if profile else "team or roster"
        first = _section(
            f"Check the source context for {keyword}",
            f"Match the {focus} using more than a name: check the sport, organization and season when those details are available. " + (source_cues if source_cues else "Similar names can refer to different people or squads.") + " " + reference,
            "Keep an identity check separate from a clip label",
            "A matching name in a search result does not identify a person in your recording. Add only player or team details that your own source material supports.",
        )
        second = _section(
            "Turn your own court moment into a personal highlight",
            "Choose a practice jumper or pickup sequence that you recorded. Keep the original date and timestamp, and describe the exported clip as your personal basketball moment rather than using an unverified team or player identity.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does this page identify or represent {keyword}?", "No. It links a related reference and provides HoopCut's independent basketball editing workflow. It does not verify an athlete's identity or represent a team."],
            ["Is the shared sample footage of the person or team I searched for?", "No. The sample is a generic HoopCut basketball demonstration. Upload your own recording and use accurate context for any player or team you name."],
        ]
    elif intent == "stats":
        first = _section(
            f"Read the data context behind {keyword}",
            "Check whether the source describes one game, a season, a team or an individual. Note the publication date and the definition of the displayed statistic before comparing figures from different pages. " + reference,
            "Keep observed attempts separate from official totals",
            "Your selected clip may show only part of a game. A few visible shots are not a complete stat line, and edited highlights cannot establish all attempts or possessions.",
        )
        second = _section(
            "Keep a simple manual log beside your basketball footage",
            "Write down the timestamp and the outcome you can actually see for each chosen attempt. Mark obscured outcomes as unclear. Keep those personal observations separate from any published box score or ranking.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does HoopCut calculate {keyword}?", "The tool here adds a ball-trail effect. It does not generate box scores, rankings, shot totals or player performance statistics from the uploaded video."],
            ["Can I calculate shooting percentage from my edited highlights?", "Selected highlights may omit attempts. Use a complete, clearly observed attempt set for a manual calculation, and keep any uncertain outcomes separate."],
        ]
    elif intent == "scouting":
        first = _section(
            f"Prepare useful video context for {keyword}",
            "Keep the original recording, player identifier and excerpt timestamps together. If you plan to send footage to a particular program, check that program's own current submission requirements rather than assuming one highlight format suits every recipient. " + reference,
            "Retain an unedited version for review",
            "An effect can make a personal highlight more expressive, but a recipient may want the play without additions. Keep both versions and do not substitute a visual effect for the full sequence.",
        )
        second = _section(
            "Make the basketball excerpt easy to locate",
            "Include the setup and result of the shot. Save a clear filename and a note pointing to the same moment in the original video, so a viewer can recover the surrounding possessions if needed.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does HoopCut handle {keyword} submissions?", "No. This page edits a basketball clip. It does not contact scouts, submit to programs, assess eligibility or arrange recruiting opportunities."],
            ["Should a scouting video always include a tracer?", "Follow the recipient's requirements. Keep the original without effects available, and use the traced copy as a separate edited highlight when appropriate."],
        ]
    elif intent == "handling":
        first = _section(
            f"Keep the full action visible when recording {keyword}",
            "A ball-handling clip needs the ball, hands and enough lower-body movement to show the sequence. Start before the move and keep its transition into the next action, instead of clipping out the setup.",
            "Separate the handling example from a shooting effect",
            "The shared Shot Tracer focuses on a basketball shot's flight. It does not analyze dribbling patterns, count bounces or score the quality of a crossover.",
        )
        second = _section(
            "Use a move-to-shot recording for the tracer workflow",
            "If your own sequence finishes with a jumper or layup, choose a short range that preserves the move and the release. Preview the trail on the shot while retaining the original to show the ball-handling detail.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does Shot Tracer assess {keyword}?", "No. The page can add a visual trail to a shot in your basketball clip. It does not coach ball handling or grade the move."],
            ["What if my recording contains dribbling but no shot?", "Keep it as a ball-handling example. The Tracer workflow is intended for a visible basketball shot, so choose a separate shot clip for the effect."],
        ]
    elif intent == "passing":
        first = _section(
            f"Preserve the pass-to-shot context for {keyword}",
            "An assist credits a pass that directly leads to a teammate's made basket. Keep the passer, receiver and start of the action in the recording; an excerpt beginning after the catch can hide the pass itself.",
            "Do not infer an assist from a cropped highlight",
            "A clip label is not an official statistical ruling. Describe the visible pass and finish without assigning a box-score credit that the recording cannot establish.",
        )
        second = _section(
            "Choose a receiving player's shot for the ball trail",
            "Use your own basketball sequence that ends in a visible attempt. Preserve the catch and release in the selected range, then check the tracer on the shot's flight. Keep the original for the earlier passing action.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does this tool analyze {keyword}?", "It adds a shot-tracer effect to basketball footage. It does not grade passing decisions, identify receivers or automatically award assists."],
            ["Should I start the excerpt before the catch?", "Yes, when the pass is part of the story. Keep enough lead-in to show the connection while staying within the 30-second selected range."],
        ]
    elif intent == "defense":
        first = _section(
            f"Keep the surrounding basketball play when reviewing {keyword}",
            "A defensive moment can depend on what happened before and after the shot. Preserve the original sequence and avoid using a tight ball-flight crop as the only explanation of positioning, a contest or a rebound.",
            "Describe only the visible outcome",
            "If a player or the basket is obscured, leave the outcome unclear in your notes. A tracer is not evidence that a block, steal or rebound should be recorded.",
        )
        second = _section(
            "Use the tracer only where there is a visible shot",
            "For your own sequence containing an attempt, select a range with the release and basket visible. Compare the edited preview with the original so the added effect does not hide the contest or finish.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Can HoopCut evaluate {keyword}?", "No. This workflow adds a visual shot trail. It does not grade defensive decisions, identify players or produce defensive statistics."],
            ["What footage should I retain around a defensive play?", "Keep the original sequence before the shot and after the result. The short traced version should remain a separate illustration of the visible attempt."],
        ]
    elif intent == "shooting":
        sh, st, subh, subt = _shot_focus(keyword)
        first = _section(sh, st, subh, subt)
        second = _section(
            f"Organize your own example of {keyword}",
            "Choose one clear attempt and keep its start and end time in your notes. If you compare several clips, describe only what the recordings show and retain the same source identifiers on the original and traced versions.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does Shot Tracer teach or classify {keyword}?", "No. It illustrates the ball's visible flight in your saved recording. It does not classify the shot, prescribe technique or assess shooting ability."],
            ["What makes a useful shot example?", "Keep the approach, release and finish visible. Use a description supported by the original and check the traced preview before choosing the edited version."],
        ]
    elif intent in {"training", "skill"}:
        first = _section(
            f"Use clear recording notes alongside {keyword}",
            "Record the activity name, session date and the attempt you want to revisit. A short video is easier to interpret when you know where it fits in the session, rather than treating a single selected make as the whole practice.",
            "Keep observations separate from a training assessment",
            "Write down only what is visible, such as the release and result. The tool does not design a drill, assess fitness or decide whether a technique is correct.",
        )
        second = _section(
            "Select one basketball attempt from the session",
            "Choose your own recording with the ball and basket in frame. Keep enough lead-in to understand the setup and enough finish to see the outcome. Store the traced excerpt beside its unedited source.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Does this page provide a {keyword} program?", "It provides a basketball video-editing step, not a training program. Use it to illustrate a recorded attempt without treating the effect as coaching feedback."],
            ["How should I compare practice clips?", "Keep the session date, clip timestamp and visible outcome with each original. A selected highlight alone does not represent every attempt in a session."],
        ]
    elif intent == "explainer":
        first = _section(
            f"Find the right context for {keyword}",
            "A basketball term can describe an action, a rule or a statistic. Establish which meaning the source uses before labeling your clip. For a rule question, check the relevant competition's rulebook and edition. " + reference,
            "A short recording does not settle every rule question",
            "Keep the original sequence, including what happened before the ball was released. Do not infer a referee's ruling or a player's intent from the effect alone.",
        )
        second = _section(
            "Use a basketball clip as a visible example",
            "Pick your own recording that clearly shows the action you want to describe. If it includes a shot, add a tracer to a short copy while retaining the original as the reference for the actual play.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"Can the tracer answer a rules question about {keyword}?", "No. A ball-trail effect is not an officiating decision. Use the full sequence and the applicable rulebook when a rule interpretation matters."],
            ["How do I label an example when the action is unclear?", "Use a broader description or leave the uncertain detail out. Keep the source recording so viewers can see the context beyond your short edit."],
        ]
    else:
        first = _section(
            f"Choose the recording task behind {keyword}",
            "Decide which moment you want the viewer to follow before applying an effect. For the shared basketball workflow, choose a saved clip with one visible attempt, keeping the setup and finish rather than only the ball at the rim.",
            "Keep a usable source file",
            "The uploader accepts saved MP4, MOV or WebM files up to 512 MB. Keep the original file and select a range of up to 30 seconds for the traced highlight.",
        )
        second = _section(
            "Make the ball's flight easy to review",
            "Check the preview against the original where the ball crosses players, lines or a busy background. If the trail is unclear, adjust the selected range or hoop position and compare again before saving an edited copy.",
            modifier_h, modifier_t,
        )
        faq = [
            [f"What part of {keyword} can I do with this page?", "The shared tool adds Shot Tracer to a saved basketball recording. It does not create new footage, fetch videos from other sites or assemble a multi-clip reel."],
            ["Which video file should I prepare?", "Use a saved MP4, MOV or WebM file up to 512 MB, with the ball and hoop visible. Keep the original separately from the exported edit."],
        ]
    if non_basketball:
        # This explicit boundary is added once to the task section, not repeated
        # as a large disclaimer in every module of the page.
        second["text"] += " The editing step here applies to your own basketball footage; it does not provide tracking for other sports."
    return first, second, faq


def make_profile(row, slug, category, source_context=None):
    """Return one draft matching scripts/build_shot_tracer.py's profile schema."""
    context = dict(source_context or {})
    keyword = _text(context.get("keyword") or row.get("Keyword") or row.get("keyword"))
    display = _text(context.get("display_keyword")) or keyword
    operator_match = re.search(r"\s+before:(\d{4}-\d{2}-\d{2})\b", display)
    if operator_match:
        display = re.sub(r"\s+before:\d{4}-\d{2}-\d{2}\b", "", display).strip() + " — historical search"
    slug = _text(slug)
    if not keyword or not display:
        raise ValueError("A source keyword is required")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("A valid non-empty slug is required")
    if category not in CATEGORIES:
        raise ValueError("Unknown editorial category: " + str(category))
    source = _source(row, context)
    sport = _text(context.get("sport")).lower()
    explicit_other_sport = _has(keyword, r"\b(football|soccer|baseball|softball|volleyball|hockey|lacrosse|wrestling|rugby|tennis|swimming|golf)\b")
    non_basketball = bool(
        explicit_other_sport or
        sport and sport not in {"basketball", "unknown", "sports", "sport", "general"}
    )
    intent = _intent(keyword, category, context, source)
    first, second, faq = _editorial(display, category, context, source, intent, non_basketball)
    if operator_match:
        first["text"] += f" The original query includes a before:{operator_match.group(1)} search filter. It is not a verified game date."

    if non_basketball:
        title = f"{display}: Your Basketball Clip | HoopCut"
        heading = f"{display}: a basketball Tracer workflow for your own court clip"
        intro = (
            f"Following {display} and also recording your own basketball sessions? "
            "Use this page for that separate court moment: select a saved shot, preview its ball trail and keep an edited highlight. "
            "The shared uploader is for basketball footage."
        )
        description = f"For {display} fans who also play hoops: add Shot Tracer to your own basketball clip. Preview the trail and export Firework free."
    elif intent in {"team", "profile", "roster", "fan", "watch", "schedule", "stats"}:
        title = f"{display}: Video Context & Shot Tracer | HoopCut"
        heading = f"{display}: find context and trace your own basketball clip"
        intro = (
            f"Keep your interest in {display} connected to accurate video context. "
            "Use the reference notes below to check the relevant source, then bring a shot from your own basketball recording to the shared Tracer. "
            "The demonstration shows the effect on generic footage."
        )
        description = f"Explore {display} video context, then add a tracer to your own basketball clip. Preview a short shot and export Firework free."
    elif intent in {"handling", "passing", "defense", "training", "skill", "explainer", "scouting"}:
        title = f"{display}: Basketball Video Guide | HoopCut"
        heading = f"{display}: preserve the play and add a basketball shot tracer"
        intro = (
            f"Use a clear recording to put {display} in context. "
            "Keep the full action in your original, then select a short basketball shot for a separate traced copy. "
            "This page helps you prepare the footage and preview an effect without treating it as an automatic assessment."
        )
        description = f"Put {display} in video context. Keep the original play, preview a basketball shot tracer and export a short Firework highlight free."
    else:
        title = f"{display}: Basketball Shot Tracer | HoopCut"
        heading = f"{display}: add a tracer to your own basketball shot"
        intro = (
            f"Bring {display} into a concrete basketball video task: choose one saved attempt and make its flight visible with Shot Tracer. "
            "Keep the setup, release and finish together, then compare the preview with your original before saving an edited copy."
        )
        description = f"Use your own footage for {display}. Choose a basketball shot, preview its ball trail and export HoopCut's Firework effect free."

    title = f"{display} | Shot Tracer | HoopCut"
    if len(title) > 68:
        title = f"{display} | Shot Tracer"
    # Keep the full query in H1/title. Descriptions can be concise without
    # fabricating a shortened entity name or silently merging distinct queries.
    if len(description) > 160:
        description = f"{display}: prepare your own basketball clip, preview Shot Tracer and export Firework free."
    if len(description) > 160:
        description = f"{display}: basketball Shot Tracer for your own footage."

    finish = _section(
        "Preview and export a short basketball shot tracer",
        "Upload your saved basketball video, select up to 30 seconds and mark the hoop. Watch the ball through the complete preview. Export Firework free when the result is useful, or compare the other styles before exploring more effects in the HoopCut app.",
        "Keep the effect separate from the evidence",
        "Save the traced version beside the original. The visual trail highlights movement; it does not identify athletes, award points or replace the recording's surrounding context.",
    )
    faq.extend([
        ["Which effect can I export free on this page?", "The browser workflow provides a free Firework export. Other styles can be previewed here, with a link to explore more effects in the HoopCut app."],
        ["Is the example footage specific to this topic?", "No. It is a shared HoopCut basketball demonstration. Use your own saved clip and retain the original when making a personal traced highlight."],
    ])
    result = {
        "slug": slug,
        "status": "draft",
        "intent": "hudl-query-" + slug,
        "keyword": keyword,
        "label": display,
        "title": title,
        "description": description,
        "heading": heading,
        "intro": intro,
        "heroDetail": "Select a basketball recording with the ball and hoop visible. Keep the original, inspect the short preview and save Firework as a separate edited copy.",
        "toolHeading": "Add a tracer to your own basketball video",
        "workflowHeading": "Prepare, preview and save your basketball clip",
        "sampleHeading": "See the effect on a shared basketball sample",
        "faqHeading": f"{display}: footage and Tracer questions",
        "examplesHeading": "Watch the shared HoopCut tracer demonstration",
        "sections": [first, second, finish],
        "faq": faq,
        "sources": ([{"title": "Related Hudl source" if "hudl.com" in urlsplit(source).netloc else "Related source", "url": source}] if source else []),
        "workflowSteps": [
            {"title": "Choose your saved basketball clip", "text": "Upload your own recording with the ball and basket visible."},
            {"title": "Select and preview the shot", "text": "Choose up to 30 seconds, mark the hoop and inspect the ball trail."},
            {"title": "Save a separate traced highlight", "text": "Export Firework free and retain your original for context."},
        ],
        "appCTA": {
            "heading": "Explore more basketball tracer styles",
            "text": "Use the free Firework export here or open HoopCut to explore additional effects for your own basketball recordings.",
        },
        "examples": [[EXAMPLE, "Watch a HoopCut basketball tracer example", "Generic basketball footage showing the effect; not evidence about the query's person, team or event."]],
        "demandEvidence": None,
        "exampleEvidence": None,
        "reviewedBy": None,
        "topic": category,
        "editorialIntent": intent,
    }
    if intent in {"team", "profile", "roster", "fan", "watch", "schedule", "stats"} or non_basketball:
        result["note"] = "HoopCut is independent. The shared sample is generic basketball footage, and this uploader does not supply team broadcasts or identify players."
    if intent == "foul":
        result["sources"].append({"title": "NBA Rule 12: Fouls and Penalties", "url": "https://official.nba.com/rule-no-12-fouls-and-penalties/"})
    return result
