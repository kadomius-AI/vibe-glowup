# Vibe Glow Up ✨

Old videos in → glowed-up videos out. Make your back catalog look and feel like what you post today.

| Say this | You get |
|---|---|
| "Glow up this old video to match my new style" + an old video and a recent one | Same content with your current look (color/brightness), tightened pacing, clean loud-enough audio, new captions and hook, vertical 9:16 framing |
| "…and put me in my new set" | Background swapped to your new set, a blur, a color or any image (single talking head) |
| "Make clips from this old webinar" | Captioned vertical clips (`/clips`) |

Everything runs on your own computer. No API keys, no accounts. Only use it on content you own or have rights to.

## Install (in Claude Code)
```
/plugin marketplace add kadomius-AI/vibe-glowup
/plugin install vibe-glowup@vibe-glowup
```
Needs macOS or Linux, Homebrew, Python 3.11–3.13 (set up automatically on first use).

Experimental: light skin touch-up. Real face/beard changes need a generative AI model and are not included.

## Built with (all free and open source, runs on your Mac)
| Job | Framework / model | License |
|---|---|---|
| Video in/out, cutting, loudness | FFmpeg, OpenCV | LGPL/GPL tool, Apache-2.0 |
| Face tracking | OpenCV YuNet | MIT |
| Transcription + word timing | Whisper (mlx-whisper on Apple Silicon) | MIT |
| Voiceover with word timing | Kokoro-82M | Apache-2.0 |
| Original music | ACE-Step | Apache-2.0 |
| Beat detection | librosa | ISC |
| Sound effects | synthesized in code (original) | — |
| Voice isolation | Demucs (htdemucs) | MIT |
| 3D parallax on photos | Depth Anything V2 Small (PyTorch + transformers) | Apache-2.0 |
| Product cut-outs | Segment Anything (SAM ViT-B) | Apache-2.0 |
| Person cut-outs / backgrounds | MediaPipe selfie segmenter | Apache-2.0 |
| Face edits (beard / stubble / shave, consent only) | SDXL Inpainting via diffusers + MediaPipe Face Landmarker | CreativeML Open RAIL++-M / Apache-2.0 |
| AI upscaling of old low-res footage | Real-ESRGAN x4 via spandrel | BSD-3 / MIT |
| Graphics and text | Pillow + NumPy | MIT-CMU / BSD |
| AI runtime | PyTorch (Apple GPU), MLX | BSD / MIT |
No API keys, no accounts, no payments. First use downloads about 10–15 GB of models once.

Fonts: Montserrat, Anton, Playfair Display, Inter — SIL Open Font License 1.1.

## Tests
```
~/.local/share/vibekit/venv/bin/python -m pytest plugins/vibe-glowup/tests -q
```
Every render also writes a `.plan.json` (decisions) and a `.qa.json` (automated checks).
