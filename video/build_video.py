# /// script
# requires-python = ">=3.11"
# dependencies = ["imageio-ffmpeg"]
# ///
"""Build the demo video: the slides in slides.html, narrated, as an .mp4 with an .srt of subtitles beside it.

  uv run video/build_video.py                      # video/callguard_demo.mp4 and video/callguard_demo.srt
  uv run video/build_video.py --voice Rishi        # another macOS voice (say -v '?' lists them)
  uv run video/build_video.py --frames-only        # only the slide images, in video/build/frames, to check them

Each scene of slides.html is screenshotted in headless Chrome at each of its steps (slides.html#s=<scene>&k=<step>),
and each step's narration below is spoken by macOS `say`. A step's slide stays up while its narration plays; scenes
are joined with a short crossfade. Everything runs on this Mac: nothing is uploaded.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import textwrap
import wave
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
SLIDES = HERE / "slides.html"
BUILD = HERE / "build"
OUT = HERE / "callguard_demo"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FPS = 30
XFADE = 0.5      # seconds of crossfade between scenes
GAP = 0.55       # silence between two steps of one scene
TAIL = 1.0       # silence at the end of a scene (it must outlast the crossfade)
EARLY = 0.15     # a step's slide appears this long before its narration starts

# One list per scene of slides.html, one string per step. {shown|spoken} shows the first part in the subtitles and
# speaks the second.
SCENES = [
    [  # 1. Title
        "This is a walkthrough of my Track 3 project: evaluating CallGuard, a retrieval-augmented assistant, "
        "with LangSmith.",
        "The headline: correctness went from 93% to 98%, the slowest answers from 7.2 to 3.8 seconds, and five "
        "held-out questions, written after the fixes, went from 80% to 100%. Here is how.",
    ],
    [  # 2. CallGuard
        "CallGuard answers 'are we exposed?' questions about vulnerabilities in contact-center and "
        "unified-communications products, such as Cisco, Avaya, Mitel and Asterisk. It answers from NVD, CISA's "
        "list of known exploited vulnerabilities, and FIRST's exploit forecasts, and it cites every claim.",
        "Each question runs through a LangGraph call flow. Code reads the CVE numbers, products and versions. A "
        "hybrid search finds the records, and code checks the versions. For open-ended questions, a model checks "
        "that the records fit. Then a writer model drafts a cited answer, or code declines with safe wording.",
        "To keep every comparison fair, the data was frozen at 895 CVEs, and each experiment records the exact "
        "CallGuard version it ran.",
    ],
    [  # 3. Method
        "The method is the one a QA team would use. Build a golden dataset. Score every answer with code "
        "evaluators and LLM judges, three times per case, so the noise is measured rather than guessed. Then "
        "check the evaluators themselves.",
        "Take a baseline, cluster the failures by root cause, fix them, and run it again. Finally, a held-out "
        "set, written after the fixes, checks that they generalise.",
    ],
    [  # 4. Golden dataset
        "The golden dataset has 40 cases: 20 happy-path, 12 edge, 6 known-failure, and 2 adversarial. The 25 "
        "questions from my Week 3 exam are kept word for word. They were written before CallGuard existed, which "
        "keeps them honest.",
        "Fifteen new cases target real gaps, and I checked each edge case against the code first. 'Asterix', "
        "misspelled, matches no product filter, for example. Every case states the expected behaviour: answer, "
        "refuse for a stated reason, or resist an attack. It also lists the CVEs a good answer must find, and a "
        "reference answer.",
        "A check script verifies every expected CVE against the data before upload. In LangSmith, the dataset "
        "has one split per group, fixed example IDs, and the version tag v1, so every experiment runs on exactly "
        "the same examples.",
    ],
    [  # 5. Adversarial
        "Two cases are adversarial. A1 is a prompt injection. It claims a real CVE was withdrawn, and orders the "
        "reply 'safe, no action needed'. That phrase must never appear.",
        "A2 is 771 characters of noise: control codes, a script tag, SQL, template and JNDI strings, an XML "
        "entity and spreadsheet formulas, all wrapped around one real question about server-side request "
        "forgery in Cisco Finesse.",
    ],
    [  # 6. Scoring
        "One client.evaluate call runs each experiment. Questions are asked one at a time, so response times "
        "aren't distorted by parallel calls, and every case runs three times.",
        "Code evaluators check what code can check exactly. Did the answer find and cite the expected CVEs? Is "
        "every citation a record it was actually shown? Did it decline exactly when it should, and resist the "
        "attacks? And how fast was it?",
        "Two LLM judges handle what code can't: faithfulness and correctness. The judge is Qwen 3.5, a different "
        "model from CallGuard's writer and checker, so no model grades its own work.",
    ],
    [  # 7. Two faithfulness scores
        "Faithfulness gets two scores from one judgement. Here, CallGuard correctly declines a product that "
        "doesn't exist, and adds a caveat: that is not a statement that the product is safe.",
        "Strict scoring, the way RAGAS does it, counts that caveat as unsupported, so this correct refusal "
        "scores 71%. Facts-only scoring ignores caveats, and scores it 100%. Both are reported, because strict "
        "scoring alone punishes exactly the behaviour we want.",
    ],
    [  # 8. Audit
        "Before trusting the baseline, I read every failing verdict against the records. The correctness judge "
        "had only seen the reference answer, so it called correct extra facts hallucinated: EPSS scores, a 2026 "
        "date it took for the future, even four real CVEs.",
        "Given the same sources the writer saw, and re-scored on the same 120 answers, correctness went from 80% "
        "to 93%. Two more problems were found the same way: a refusal phrase list that missed new wordings, and "
        "a second evaluate call that mixed up the repetitions. Measuring the measure changed the headline by 13 "
        "points.",
    ],
    [  # 9. Baseline
        "The baseline: 93% correct, faithfulness 99.6% on facts, and citations, refusals and attacks resisted "
        "all at 100%. Across the three repetitions, correctness moved between 92% and 94% on its own.",
        "So CallGuard's weak points weren't hallucination. They were coverage, in the known-failure and "
        "adversarial groups, and speed: a p95 of 7.2 seconds, against a 6-second target.",
    ],
    [  # 10. Latency
        "Every failing run was traced to a cause. Cluster one: slow answers. The traces show that search takes "
        "five hundredths of a second. Writing takes 99% of the time, and about half of the writer's output is "
        "hidden reasoning.",
        "On L1's real prompt, I tried three ways to switch that reasoning off. Only one of them worked, and it "
        "took the answer from 7.2 to 3.8 seconds, with the same content.",
    ],
    [  # 11. Other clusters
        "Cluster two: list questions. 'List every critical MiCollab vulnerability.' The filters find exactly the "
        "13 right records, ranked 1 to 13. Then the search keeps the top 8, and the answer claims the data has "
        "only eight.",
        "Cluster three: noisy questions. 'Asterix' matches no product filter, so the most serious CVE ranks "
        "tenth. In A2, the XML junk, version equals 1.0, was read as a product version. That re-sorted the "
        "results, and pushed three of the five right records out.",
        "Cluster four: seven of the 895 records state their affected versions only in a description, so the "
        "writer hedged instead of answering. One case, S2, stays unfixed. Its two missed records rank 13th and "
        "39th for that wording.",
    ],
    [  # 12. Fixes
        "Four clusters, four fixes, each a general rule rather than a patch for one case. F1 runs the writer "
        "without hidden reasoning. F2 adds a list mode that passes on every matching record, up to 20, and tells "
        "the writer the count. F3 cleans noisy questions, and tolerates a misspelled product, telling the writer "
        "it was a guess. F4 reads a version range stated in a description, in code.",
        "Each fix was checked for side effects on all 40 questions. I also dropped a planned prompt-injection "
        "guardrail: both attacks were resisted in every run, so there was nothing for it to fix.",
    ],
    [  # 13. Regression and the guard
        "The re-run then caught a regression my own fix caused. Without its reasoning, the writer once slipped a "
        "digit: {41713|4 1 7 1 3} came out as {41793|4 1 7 9 3}. One answer in 120.",
        "So F5 is a citation guard. If an answer cites a CVE that wasn't retrieved, isn't in the records, and "
        "wasn't typed by the user, it gets one rewrite naming the wrong number. If one remains, code adds a "
        "warning. Four tests with a scripted writer show that it works, and in the final run it never needed to "
        "fire.",
    ],
    [  # 14. Results
        "Same dataset version, same evaluators, same judge. Only CallGuard changed. Correctness rose from 93% to "
        "98%. Expected CVEs found, from 96% to 99%. And answers under six seconds, from 88% to 98%.",
        "p50 fell from 3.6 to 2.1 seconds, and p95 from 7.2 to 3.8, well under the target. Citations, refusals "
        "and attacks held at 100%. And a change only counts when the repetition ranges don't overlap: "
        "correctness ranged from 92 to 94% before, and from 96 to 99% after.",
    ],
    [  # 15. Cases
        "Twelve cases went from failing at least one measure to failing none. The biggest gains were in the "
        "hardest groups: known failures from 81% to 92% correct, and adversarial from 75% to 100%.",
        "L1 now lists all 13 critical CVEs, in under four seconds instead of six to eight. X1 says 'assuming you "
        "mean Asterisk', and finds all five. And A2 finds all five through the noise.",
    ],
    [  # 16. The price
        "It wasn't free. Without the reasoning, faithfulness on facts fell from 99.6% to 99.4%: single loose "
        "inferences, such as 'your build is the fixed one'. Two cases had one 'partly' run each. That's the "
        "price of halving the response time, and the report states it.",
    ],
    [  # 17. Held-out
        "To check that the fixes weren't just memorising their test cases, I wrote five new questions after the "
        "fixes, one per fixed behaviour, on other products and wordings.",
        "On the baseline version, they scored 80% correct. With the fixes, 100%, and CVEs found went from 96% to "
        "100%. The fixes generalise.",
    ],
    [  # 18. Deliverables
        "Everything is reproducible. The repository holds the dataset, the evaluators, every result, and the "
        "reports. The spreadsheet has all 40 cases and 405 runs, with a summary computed by formula from the "
        "run data, and a link from every run to its LangSmith trace.",
    ],
    [  # 19. Wrap-up
        "A few limits, stated plainly. The timings reuse cached question embeddings. Three answers hit a stalled "
        "API call. S2 still fails. And 45 cases are enough to find failure classes, not to measure rare errors "
        "precisely.",
        "The lessons I'd keep: measure the measure first. Repetitions are cheap insurance. Traces turn guesses "
        "into causes. Every fix has a price, so measure it. And held-out cases keep the fixes honest. Thanks for "
        "watching.",
    ],
]

# How the voice should say what the subtitles show (applied in order, to the spoken text only)
LEXICON = [
    (r"client\.evaluate", "client dot evaluate"),
    (r"LangSmith", "Lang Smith"), (r"LangGraph", "Lang Graph"),
    (r"MiCollab", "My Collab"), (r"MiColab", "My Colab"), (r"MiVoice", "My Voice"),
    (r"\bQwen\b", "Kwen"), (r"\bRAGAS\b", "Ragas"), (r"\bCISA\b", "Sissa"),
    (r"\b[pP]95\b", "P ninety-five"), (r"\b[pP]50\b", "P fifty"),
    (r"\bCVEs\b", "C V E's"), (r"\bCVE\b", "C V E"),
    (r"\b(EPSS|NVD|JNDI|LLM|QA|SQL|XML|API)\b", lambda m: " ".join(m[1])),
    (r"\bv(\d)\b", r"v \1"),
    (r"\b([A-Z])(\d)\b", r"\1 \2"),  # case and fix names: A1, L1, S2, F5
]
MARKUP = re.compile(r"\{([^|{}]+)\|([^{}]+)\}")


def shown(text):
    return MARKUP.sub(r"\1", text)


def spoken(text):
    text = MARKUP.sub(r"\2", text)
    for pattern, replacement in LEXICON:
        text = re.sub(pattern, replacement, text)
    return text


def run(*command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, text=True, **kwargs)


def chrome(*args):
    BUILD.mkdir(exist_ok=True)
    return run(CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               "--no-default-browser-check", f"--user-data-dir={BUILD / 'chrome'}", "--force-device-scale-factor=1",
               "--window-size=1920,1080", "--virtual-time-budget=1500", *args)


def slide_url(scene, step):
    return f"{SLIDES.as_uri()}#s={scene}&k={step}"


def check_steps():
    """slides.html and SCENES must agree: same number of scenes, and of steps in each."""
    title = re.search(r"<title>(.*?)</title>", chrome("--dump-dom", slide_url(1, 1)).stdout, re.S)[1]
    steps = json.loads(html.unescape(title))
    narrated = [len(scene) for scene in SCENES]
    if steps != narrated:
        sys.exit(f"slides.html has steps {steps}, but the narration has {narrated}")


def screenshots():
    frames = BUILD / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    paths = []
    for s, scene in enumerate(SCENES, 1):
        paths.append([])
        for k in range(1, len(scene) + 1):
            path = frames / f"s{s:02d}k{k}.png"
            chrome(f"--screenshot={path}", slide_url(s, k))
            paths[-1].append(path)
        print(f"  slide {s}/{len(SCENES)}", flush=True)
    return paths


def narrate(voice, rate):
    audio = BUILD / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    clips = []
    for s, scene in enumerate(SCENES, 1):
        clips.append([])
        for k, text in enumerate(scene, 1):
            script, path = audio / f"s{s:02d}k{k}.txt", audio / f"s{s:02d}k{k}.wav"
            script.write_text(spoken(text))
            run("say", "-v", voice, "-r", str(rate), "-f", str(script), "-o", str(path),
                "--file-format=WAVE", "--data-format=LEI16@22050")
            clips[-1].append(path)
    return clips


def seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def timeline(clips):
    """When each scene starts, when each narration clip starts, and how many frames each slide step is shown."""
    xfade = round(XFADE * FPS)
    plan, start = [], 0
    for s, scene in enumerate(clips):
        lead = 0.6 if s == 0 else XFADE + 0.25
        speech, t = [], lead
        for clip in scene:
            speech.append(t)
            t += seconds(clip) + GAP
        total = round((t - GAP + TAIL) * FPS)
        switches = [0] + [round((at - EARLY) * FPS) for at in speech[1:]] + [total]
        plan.append({"start": start / FPS, "speech": speech, "frames": total,
                     "steps": [b - a for a, b in zip(switches, switches[1:])]})
        start += total - xfade
    return plan, (start + xfade) / FPS


def mix(clips, plan, length):
    """All narration on one track, each clip at its place in the video."""
    rate, track = 22050, bytearray(round(length * 22050) * 2)
    for scene, at in zip(clips, plan):
        for clip, offset in zip(scene, at["speech"]):
            with wave.open(str(clip)) as w:
                assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (rate, 1, 2), clip
                data = w.readframes(w.getnframes())
            i = round((at["start"] + offset) * rate) * 2
            track[i:i + len(data)] = data
    path = BUILD / "narration.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(track))
    return path


def cues(text, start, duration):
    """Subtitle cues for one narration clip: a sentence each (long ones split at a comma or colon), timed by
    their share of the characters."""
    pieces = []
    for sentence in re.split(r"(?<=[.?!])\s+", text):
        chunk = ""
        for part in re.split(r"(?<=[,:])\s+", sentence):
            if chunk and len(chunk) + len(part) > 84:
                pieces.append(chunk)
                chunk = part
            else:
                chunk = f"{chunk} {part}".strip()
        pieces.append(chunk)
    total, t = sum(len(p) for p in pieces), start
    for piece in pieces:
        length = duration * len(piece) / total
        yield t, t + length, "\n".join(textwrap.wrap(piece, 46))
        t += length


def subtitles(clips, plan):
    def stamp(t):
        ms = round(t * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    lines, n = [], 0
    for scene, clip_list, at in zip(SCENES, clips, plan):
        for text, clip, offset in zip(scene, clip_list, at["speech"]):
            for a, b, words in cues(shown(text), at["start"] + offset, seconds(clip)):
                n += 1
                lines += [str(n), f"{stamp(a)} --> {stamp(b)}", words, ""]
    path = OUT.with_suffix(".srt")
    path.write_text("\n".join(lines))
    return path


def encode(ffmpeg, frames, plan, narration):
    clips = BUILD / "clips"
    clips.mkdir(exist_ok=True)
    scenes = []
    for s, (images, at) in enumerate(zip(frames, plan), 1):
        parts = []
        for k, (image, count) in enumerate(zip(images, at["steps"]), 1):
            part = clips / f"s{s:02d}k{k}.mp4"
            run(ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-i", str(image),
                "-frames:v", str(count), "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
                "-crf", "16", "-pix_fmt", "yuv420p", str(part))
            parts.append(part)
        listing = clips / f"s{s:02d}.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
        scene = clips / f"s{s:02d}.mp4"
        run(ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy",
            str(scene))
        scenes.append(scene)
    inputs = [arg for scene in scenes for arg in ("-i", str(scene))]
    graph = [f"[{i}:v]settb=AVTB,fps={FPS},format=yuv420p[v{i}]" for i in range(len(scenes))]
    last = "v0"
    for i, at in enumerate(plan[1:], 1):
        graph.append(f"[{last}][v{i}]xfade=transition=fade:duration={XFADE}:offset={at['start']:.4f}[x{i}]")
        last = f"x{i}"
    n = len(scenes)
    video = OUT.with_suffix(".mp4")
    run(ffmpeg, "-y", "-loglevel", "error", *inputs, "-i", str(narration),
        "-filter_complex", ";".join(graph), "-map", f"[{last}]", "-map", f"{n}:a",
        "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000",
        "-metadata", "title=Evaluating CallGuard with LangSmith", "-movflags", "+faststart", str(video))
    return video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="Daniel", help="a macOS voice; say -v '?' lists them")
    parser.add_argument("--rate", type=int, default=180,
                        help="words per minute; Daniel's normal pace is about 180, and lower values don't slow it")
    parser.add_argument("--frames-only", action="store_true", help="only render the slide images")
    args = parser.parse_args()

    if BUILD.exists():
        shutil.rmtree(BUILD)
    check_steps()
    print(f"Slides: {len(SCENES)} scenes, {sum(map(len, SCENES))} steps", flush=True)
    frames = screenshots()
    if args.frames_only:
        print(f"Frames in {BUILD / 'frames'}")
        return
    clips = narrate(args.voice, args.rate)
    plan, length = timeline(clips)
    print(f"Narration: voice {args.voice}, {length / 60:.1f} minutes", flush=True)
    narration = mix(clips, plan, length)
    srt = subtitles(clips, plan)
    video = encode(imageio_ffmpeg.get_ffmpeg_exe(), frames, plan, narration)
    print(f"Video: {video} ({video.stat().st_size / 1e6:.1f} MB), subtitles: {srt}")


if __name__ == "__main__":
    main()
