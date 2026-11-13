#!/usr/bin/env python3
"""/glowup — give old videos the glow-up: make them look and feel like your new ones.

  glowup.py analyze OLD.mp4 --ref NEW.mp4 --out DIR
      Compares the old video with a recent "style reference": look (brightness, contrast, color, saturation),
      pacing (cuts per minute, pauses), loudness, framing. Saves side-by-side stills (compare.jpg) and
      suggested settings (analysis.json).

  glowup.py apply OLD.mp4 --ref NEW.mp4 --out OUT.mp4
                   [--color 0.8]            match the reference's color/brightness (0 = off, 1 = full)
                   [--tighten 0.35]         remove pauses longer than this many seconds (0 = off)
                   [--audio]                isolate the voice (removes old music, crowd, noise) + polish
                   [--bg keep|blur|ref|color:#hex|image:path.jpg]   replace the background behind the person
                   [--format keep|vertical|square|portrait]          vertical = face-tracked 9:16
                   [--captions none|bold|clean|punch] [--headline "Line 1|Line 2"]
                   [--touchup 0.0-1.0]      EXPERIMENTAL light skin smoothing on faces
                   [--music-prompt "..."]  add an original, royalty-free music bed (ducked under the voice)
      Steps run in that order; the original file is never changed.
"""
import argparse, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv2
import numpy as np
from vibekit import media, qa
from vibekit.env import FFMPEG, probe, loudness
from vibekit.render import render, SIZES
from vibekit.faces import FaceFinder


# ---------- analysis ----------
def _frames(video, n=24):
    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    out = []
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int((k + 0.5) * total / n))
        ok, f = cap.read()
        if ok:
            out.append(f)
    cap.release()
    return out


def look_stats(frames):
    lab = np.concatenate([cv2.cvtColor(cv2.resize(f, (320, 180)), cv2.COLOR_BGR2LAB).reshape(-1, 3) for f in frames]).astype(np.float32)
    hsv = np.concatenate([cv2.cvtColor(cv2.resize(f, (320, 180)), cv2.COLOR_BGR2HSV).reshape(-1, 3) for f in frames]).astype(np.float32)
    return {"lab_mean": lab.mean(0).tolist(), "lab_std": lab.std(0).tolist(),
            "brightness": round(float(lab[:, 0].mean() / 2.55), 1), "contrast": round(float(lab[:, 0].std() / 2.55), 1),
            "saturation": round(float(hsv[:, 1].mean() / 2.55), 1),
            "warmth": round(float(lab[:, 2].mean() - 128), 1)}


def cut_rate(video):
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step, i, prev, cuts = max(1, int(fps / 5)), 0, None, 0
    while cap.grab():
        if i % step == 0:
            ok, f = cap.retrieve()
            h = cv2.calcHist([cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 16], [0, 180, 0, 256])
            cv2.normalize(h, h)
            if prev is not None and cv2.compareHist(prev, h, cv2.HISTCMP_BHATTACHARYYA) > 0.45:
                cuts += 1
            prev = h
        i += 1
    cap.release()
    dur = i / fps
    return round(cuts / max(dur / 60, 1e-6), 1), dur


def analyze(old, ref, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    res = {}
    for name, v in (("old", old), ("ref", ref)):
        info = probe(v)
        fr = _frames(v)
        sil = media.silences(v, min_len=0.35)
        cpm, dur = cut_rate(v)
        faces = [FaceFinder().find(f) for f in fr[::4]]
        face_h = [fs[0][3] / f.shape[0] for fs, f in zip(faces, fr[::4]) if fs]
        res[name] = {"size": [info["width"], info["height"]], "duration": round(info["duration"], 1),
                     "lufs": loudness(v) if info["has_audio"] else None, "cuts_per_min": cpm,
                     "pause_share": round(sum(e - s for s, e in sil) / max(dur, 1), 3),
                     "long_pauses": sum(1 for s, e in sil if e - s > 0.6),
                     "face_height": round(float(np.mean(face_h)), 2) if face_h else None,
                     **look_stats(fr)}
    o, r = res["old"], res["ref"]
    sug = {"color": 0.8 if abs(o["brightness"] - r["brightness"]) + abs(o["saturation"] - r["saturation"]) + abs(o["warmth"] - r["warmth"]) > 6 else 0.4,
           "tighten": 0.3 if o["pause_share"] > max(0.08, r["pause_share"] * 1.3) else 0.0,
           "audio": (o["lufs"] or -30) < -20,
           "format": "vertical" if r["size"][1] > r["size"][0] and o["size"][0] > o["size"][1] else "keep"}
    res["suggested"] = sug
    a, b = _frames(old, 3), _frames(ref, 3)
    row = lambda fs: np.hstack([cv2.resize(f, (480, int(480 * f.shape[0] / f.shape[1]))) if f.shape[1] >= f.shape[0]
                                else cv2.resize(f, (int(270 * f.shape[1] / f.shape[0]), 270)) for f in fs])
    ra, rb = row(a), row(b)
    w = max(ra.shape[1], rb.shape[1])
    pad = lambda m: cv2.copyMakeBorder(m, 0, 0, 0, w - m.shape[1], cv2.BORDER_CONSTANT)
    sheet = np.vstack([pad(ra), pad(rb)])
    cv2.imwrite(str(out / "compare.jpg"), sheet)
    (out / "analysis.json").write_text(json.dumps(res, indent=1))
    res["compare_image"] = str(out / "compare.jpg")
    return res


# ---------- look filters ----------
def color_filter(old_frames, ref_frames, strength):
    so, sr = look_stats(old_frames), look_stats(ref_frames)
    mo, do = np.array(so["lab_mean"]), np.array(so["lab_std"]) + 1e-3
    mr, dr = np.array(sr["lab_mean"]), np.array(sr["lab_std"])
    gain = np.clip(dr / do, 0.6, 1.6)
    lut = []
    for c in range(3):  # per-channel lookup tables = fast per-frame transfer
        x = np.arange(256, dtype=np.float32)
        y = (x - mo[c]) * gain[c] + mr[c]
        lut.append(np.clip(x + strength * (y - x), 0, 255).astype(np.uint8))

    def f(frame, t):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        for c in range(3):
            lab[..., c] = cv2.LUT(lab[..., c], lut[c])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return f


def clean_plate(video, n=12):
    """A background image with the person removed (median of frames + inpainting)."""
    from vibekit.segment import person_mask
    fr = _frames(video, max(n, 24))
    # use only frames from the main set: a face is visible and the scene matches the most common look
    ff = FaceFinder()
    fr = [f for f in fr if ff.find(f)] or fr
    hs = []
    for f in fr:
        h = cv2.calcHist([cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 16], [0, 180, 0, 256])
        cv2.normalize(h, h); hs.append(h)
    score = [sum(cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA) for b in hs) for a in hs]
    anchor = hs[int(np.argmin(score))]
    fr = [f for f, h in zip(fr, hs) if cv2.compareHist(anchor, h, cv2.HISTCMP_BHATTACHARYYA) < 0.3][:n] or fr[:n]
    stack, masks = [], []
    for f in fr:
        m = person_mask(f)
        stack.append(f.astype(np.float32)); masks.append(m < 0.3)
    stack, masks = np.array(stack), np.array(masks)
    plate = np.zeros_like(stack[0])
    cnt = masks.sum(0)
    for c in range(3):
        v = np.where(masks, stack[..., c], np.nan)
        plate[..., c] = np.nan_to_num(np.nanmedian(v, axis=0))
    plate = plate.astype(np.uint8)
    hole = (cnt == 0).astype(np.uint8) * 255
    if hole.any():
        plate = cv2.inpaint(plate, cv2.dilate(hole, np.ones((15, 15), np.uint8)), 9, cv2.INPAINT_TELEA)
    return plate


def bg_filter(mode, ref, W, H):
    from vibekit.segment import person_mask, MaskSmoother
    smooth = MaskSmoother(0.55)
    bgimg = None
    if mode == "ref":
        bgimg = clean_plate(ref)
    elif mode.startswith("image:"):
        bgimg = cv2.imread(mode[6:])
    elif mode.startswith("color:"):
        h = mode[6:].lstrip("#")
        bgimg = np.full((H, W, 3), [int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.uint8)
    if bgimg is not None:
        s = max(W / bgimg.shape[1], H / bgimg.shape[0])
        r = cv2.resize(bgimg, (int(bgimg.shape[1] * s + 1), int(bgimg.shape[0] * s + 1)))
        y0, x0 = (r.shape[0] - H) // 2, (r.shape[1] - W) // 2
        bgimg = r[y0:y0 + H, x0:x0 + W]

    def f(frame, t):
        m = smooth(person_mask(frame))
        m = cv2.GaussianBlur(m, (0, 0), 2.0)[..., None]
        back = cv2.GaussianBlur(frame, (0, 0), 22) if bgimg is None else bgimg
        return (frame * m + back * (1 - m)).astype(np.uint8)
    return f


def touchup_filter(strength):
    ff = FaceFinder()
    state = {"faces": [], "i": 0}

    def f(frame, t):
        if state["i"] % 6 == 0:
            state["faces"] = ff.find(frame)
        state["i"] += 1
        out = frame
        for x, y, w, h, _ in state["faces"][:2]:
            x0, y0 = max(0, int(x - w * 0.1)), max(0, int(y - h * 0.15))
            x1, y1 = min(frame.shape[1], int(x + w * 1.1)), min(frame.shape[0], int(y + h * 1.15))
            roi = out[y0:y1, x0:x1]
            if roi.size == 0:
                continue
            sm = cv2.bilateralFilter(roi, 9, 40, 9)
            mask = np.zeros(roi.shape[:2], np.float32)
            cv2.ellipse(mask, (roi.shape[1] // 2, roi.shape[0] // 2), (roi.shape[1] // 2, roi.shape[0] // 2), 0, 0, 360, 1, -1)
            mask = cv2.GaussianBlur(mask, (0, 0), 9)[..., None] * strength
            out[y0:y1, x0:x1] = (sm * mask + roi * (1 - mask)).astype(np.uint8)
        return out
    return f


# ---------- apply ----------
def tighten_segments(video, min_pause, keep=0.12):
    dur = probe(video)["duration"]
    sil = media.silences(video, noise_db=-35, min_len=min_pause)
    segs, cur = [], 0.0
    for s, e in sil:
        a, b = cur, s + keep
        if b - a > 0.25:
            segs.append([round(a, 3), round(b, 3)])
        cur = max(cur, e - keep)
    if dur - cur > 0.25:
        segs.append([round(cur, 3), round(dur, 3)])
    return segs or [[0, dur]]


def apply(a):
    old, ref, out = Path(a.old), Path(a.ref), Path(a.out)
    work = out.parent / f"{out.stem}_work"
    work.mkdir(parents=True, exist_ok=True)
    src = old
    # 1) tighten pauses
    if a.tighten and a.tighten > 0 and probe(old)["has_audio"]:
        segs = tighten_segments(old, a.tighten)
        if len(segs) > 1:
            media.cut(old, segs, work / "tight.mp4")
            src = work / "tight.mp4"
    # 2) audio cleanup: isolate the voice (removes old music, crowd and noise), then polish it
    if a.audio and probe(src)["has_audio"]:
        from vibekit import sound
        voice = sound.isolate_voice(src)
        vw = work / "voice.wav"
        sound.save_wav(vw, voice)
        dst = work / "audio_clean.mp4"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-i", str(vw), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", "highpass=f=70,afftdn=nf=-30,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120",
                        "-c:a", "pcm_s16le", "-shortest", str(dst)], check=True)
        src = dst
    # 3) transcript for captions
    words = None
    if a.captions != "none":
        words = media.transcribe(src, work / "transcript.json")["words"]
    # 4) look filters, applied on the final frame size
    fmt = a.format
    if fmt == "keep":
        info = probe(src)
        fmt = "horizontal" if info["width"] >= info["height"] else "vertical"
    W, H = SIZES[fmt]
    filters = []
    if a.color > 0:
        filters.append(color_filter(_frames(src), _frames(ref), a.color))
    notes = []
    if a.bg != "keep":
        crowd = [len(FaceFinder().find(f)) for f in _frames(src, 12)]
        if np.median(crowd) > 1 and not a.force_bg:
            notes.append("Background swap skipped: more than one person in most shots (works best on a single talking head). "
                         "Use --force-bg to try anyway.")
        else:
            filters.append(bg_filter(a.bg, ref, W, H))
    if a.touchup > 0:
        filters.append(touchup_filter(min(1.0, a.touchup)))
    music = None
    if a.music_prompt:
        music = str(work / "music.wav")
        subprocess.run([str(Path.home() / ".local/share/vibekit/acestep-venv/bin/python"),
                        str(Path(__file__).resolve().parent / "music_gen.py"), "--prompt", a.music_prompt,
                        "--seconds", str(round(probe(src)["duration"] + 2)), "--out", music], check=True)
    render(src, out, fmt=fmt, words=words, caption_style=a.captions if a.captions != "none" else "bold",
           headline=a.headline, follow_face=a.format != "keep", filters=filters, music=music,
           punch=a.format != "keep", sfx=True)
    rep = qa.report(out)
    if notes:
        rep["notes"] = notes
    return rep


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("analyze"); z.add_argument("old"); z.add_argument("--ref", required=True); z.add_argument("--out", required=True)
    p = sub.add_parser("apply"); p.add_argument("old"); p.add_argument("--ref", required=True); p.add_argument("--out", required=True)
    p.add_argument("--color", type=float, default=0.8); p.add_argument("--tighten", type=float, default=0.35)
    p.add_argument("--audio", action="store_true"); p.add_argument("--bg", default="keep")
    p.add_argument("--format", default="keep"); p.add_argument("--captions", default="bold")
    p.add_argument("--headline"); p.add_argument("--touchup", type=float, default=0.0)
    p.add_argument("--force-bg", action="store_true")
    p.add_argument("--music-prompt", help="add an original music bed, e.g. 'warm lofi, mellow piano, 85 bpm, instrumental'")
    a = ap.parse_args()
    if a.cmd == "analyze":
        print(json.dumps(analyze(a.old, a.ref, a.out), indent=1))
    else:
        print(json.dumps(apply(a), indent=1))


if __name__ == "__main__":
    main()
