---
name: glowup
description: >
  Give old videos a glow-up: restyle old content to match a creator's current style (color/look, background,
  pacing, audio, captions, vertical framing) so it can be posted again. Use for "refresh my old videos",
  "repurpose old content", "make this old video look new", "match my new style", "glow up", "throwback".
---

# /glowup — old video + a recent "style reference" in, glowed-up video out

Run scripts through `../../scripts/run.sh` (auto-setup on first run). The user is not technical: do every step yourself
and explain in plain words. Never change or delete the original file.

## Steps
1. **Get two videos:** the OLD one to revive and one RECENT video whose look the user likes (the style reference).
   Links work too: `run.sh clips.py prepare "<link>"` downloads + transcribes.
2. **Analyze:** `run.sh glowup.py analyze OLD.mp4 --ref NEW.mp4 --out "<folder>"` → read `analysis.json` and LOOK at
   `compare.jpg` (top row old, bottom row new). Explain the differences simply (darker, quieter, slower, smaller face…).
3. **Pick the best part first.** Old long videos rarely work whole. Skim the transcript and keep the most valuable,
   still-true moment (use `/clips` rules: open on the hook, one idea, a payoff). Cut it with `clips.py render … --no-captions --format horizontal`
   or pass the full file if it's already short.
4. **Apply:** `run.sh glowup.py apply OLD.mp4 --ref NEW.mp4 --out "<folder>/<name>_glowup.mp4" [options]`
   - `--color 0.8` match the new look (0.4 subtle, 1.0 full)
   - `--tighten 0.3` remove pauses longer than 0.3 s (modern pacing)
   - `--audio` clean hiss/hum + even out volume (always with old phone/webinar audio)
   - `--format vertical` face-tracked 9:16 for Reels/Shorts (or `keep`, `square`, `portrait`)
   - `--captions bold|clean|punch|none` and `--headline "Line 1|Line 2"` (a NEW hook for today's audience)
   - `--bg ref|blur|color:#hex|image:file.jpg` put the person in the new set/background (single talking head only;
     it skips crowds automatically — `--force-bg` to try anyway)
   - `--touchup 0.3` EXPERIMENTAL light skin smoothing
5. **Check:** LOOK at the `contact_sheet`. Fix and redo if the face is cut off, the wrong person is followed
   (re-cut tighter, or use `clips.py render --prefer-x 0.3` on the refreshed file), captions clash with burned-in text
   (`--captions none` or move them with `clips.py render --caption-y 0.55`), or the background swap shows halos.
6. Deliver with a short "before → after" note, and suggest posting it as a fresh clip or a "throwback" with a new caption.

## Rules from research on reviving old content
- **Re-edit to reposition, not just to fix.** Keep only the part that still holds value, then give it a tighter intro,
  modern pacing and a fresh title/hook.
- **New hook, first 3 seconds.** Old intros ("hey guys, welcome back…") always go.
- **Modern pacing:** remove pauses and filler; one idea per clip; 20–60 s for vertical.
- **Kinetic captions** so it works on mute; **vertical reframe** for Shorts/Reels/TikTok.
- **Match today's look and sound:** color/brightness to the current style, clean and normalized audio (−14 LUFS).
- **Update anything dated:** wrong prices, years, old offers or links → cut them or cover with a new headline.
- **Add a current point of view:** a new on-screen line or caption framing why it matters now.
- **Relevance over age:** evergreen lessons, stories and frameworks are the best candidates.
- **Honesty and consent:** only restyle content the user owns or has rights to. Face/appearance changes are an
  experiment, never used to mislead about who someone is. Real beard/face changes need a generative AI model and
  are not part of this tool.
