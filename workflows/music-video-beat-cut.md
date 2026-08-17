# A music video cut to the beat, from one prompt and an audio file

Takes a song and a master prompt and returns a finished video the full length of
the track, cut on bar lines, with a different shot for every cut. The audio is
analysed inside ComfyUI: tempo, beat grid, bar lines, per-band transients and
section boundaries. The shot list comes out of that analysis, so quiet sections
hold on long shots and loud ones cut fast, and every cut lands on a bar.

Reach for it when you want a full-length video rather than a single clip. For one
shot from one still, use `ltx-2b-image-to-video` instead.

It runs in a single queue press. The shot count is not known until the audio has
been analysed, so the render nodes expand into one chain per shot at runtime.

## Requires

- Custom nodes: [comfyui-musicvideo](https://github.com/lockewerks/comfyui-musicvideo),
  which provides every `MV*` node here. No Python dependencies beyond what
  ComfyUI already ships; it calls `ffmpeg` as a subprocess.
- Custom nodes: none others. VideoHelperSuite is not used.
- Checkpoint: `juggernautXL_juggXIByRundiffusion.safetensors` in `models/checkpoints`,
  for the start frames (https://civitai.com/models/133005)
- Checkpoint: `ltxv-2b-0.9.8-distilled.safetensors` in `models/checkpoints`
  (https://huggingface.co/Lightricks/LTX-Video, 6.34 GB)
- Text encoder: `t5xxl_fp8_e4m3fn_scaled.safetensors` in `models/text_encoders`
  (https://huggingface.co/comfyanonymous/flux_text_encoders, 5.16 GB)
- An audio file in `input/`. The graph points at `superfunk.mp3`, which ships with
  the node pack. Swap in your own.

## Cost

Measured on an RTX 4090 24 GB against a 195.04 s track at 1280x704, 25 fps, which
planned to 58 shots and 4876 frames.

- VRAM: **22.0 GB peak of 23.0 GB**, during the start-frame pass with SDXL
  resident. That figure decides whether this fits your card. The video pass is
  lighter.
- Start frames: 5.3 s each at 28 steps, so 58 of them in about 5.1 minutes.
- Shots: 11.2 minutes for 58 shots and 4876 frames, about 0.14 s per output
  frame including per-shot overhead.
- Whole graph: **about 17 minutes**, roughly 5x realtime.
- Output: 1280x704, 25 fps, H.264 yuv420p with the original audio muxed as AAC.
  195.043 s against 195.040 s of audio. 197 MB.

Each shot is also written to `output/musicvideo/shots/` as it finishes, so a
failure at shot 50 does not cost the run.

## Knobs that matter

- **`limit` on both render nodes, and they must match.** 8 renders the first 8
  shots in about 3 minutes to check a look. 0 renders the whole song. Fewer start
  frames than shots is an error rather than a silent truncation.
- **`Render shots` cfg must stay 1.0.** LTX 2B distilled is trained to run without
  classifier-free guidance. Raising it degrades the image rather than adding
  control, and with no unconditional pass the negative prompt on that node does
  nothing at all. `steps` 8 is the intended range for a distilled checkpoint.
- **`Render start frames` steps 28, not 8.** An 8-step Hyper checkpoint is four
  times faster and grows extra torsos on full-body shots. This is where anatomy
  is won or lost, because LTX then animates whatever it is given.
- **Name the wardrobe in `master_prompt`.** Describing clothing only by material,
  "gold sequins", produced sequin-textured skin and a nude figure. "a woman
  wearing a gold sequinned dress" fixed it.
- **Keep `lightings` in one colour family.** Options that swing hue turn 58 cuts
  into strobing. Varying direction and contrast reads as shot variety instead.
- `min_bars` applies at peak energy and `max_bars` in the quiet parts. Lengths
  snap to 1, 2, 4 or 8 bars; three-bar shots read as a mistake in 4/4.
- `grid_mode` rigid holds one tempo across the track with zero drift. Use
  adaptive only for music played by hand that genuinely speeds up.
- `downbeat_offset` rotates whole beats within the bar. `phase_offset_beats`
  slides the whole grid and takes fractions. They are different knobs and the
  second one is usually what you want; see below.

## Known limits

**Identity is not held across cuts.** Every start frame is an independent
text-to-image generation, so the subject's face and hair change from shot to
shot. The world stays consistent, the person does not. For a performance video
this is the first thing to fix, with an IPAdapter reference feeding every start
frame.

**The beat grid locks to energy, not to musical function.** The tempo estimator
finds the pulse carrying the most spectral flux. On funk that is often the
offbeat, so cuts land on the pickup eighth before each phrase rather than on the
downbeat. It reads as an anticipation cut and is not unpleasant, but it is not
what was asked for. `phase_offset_beats` of 0.5 moves it. The analyser's own lock
score prefers the wrong answer here, so trust your ear over the number.

**Downbeat phase is often a near tie.** On the reference track beat 1 beat beat 4
by 5.4%. The Analyse audio report prints the per-phase scores and a confidence
figure; when it is under about 6%, check by ear before trusting the bars.

**Motion is a fixed budget per clip, not a rate.** A longer shot spreads the same
movement thinner rather than moving further. Short shots therefore read as more
energetic, which happens to suit the loud sections that get them.

**A `success` status proves nothing.** Ask a video model for a clip longer than it
can hold and it returns a valid file of the right length containing mud or black.
Check the last frame of a shot, never the first: in image-to-video the first frame
is baked in from the start frame and is guaranteed to look right.
