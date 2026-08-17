# Photoreal still, Flux 1 dev

Produces a photographic still at 1280x704, sized to feed straight into
`ltx-2b-image-to-video.json` with no crop. Built while chasing hard science fiction
realism, but nothing in the graph is subject-specific: it is a plain Flux 1 dev sampler
with the settings that hold up for photoreal work.

Ships with the prompt that produced the hero frame of a spacecraft in orbit around a
ringed gas giant. Replace the prompt; keep the structure.

## Requires

- Checkpoint: `flux1-dev-fp8.safetensors` in `models/checkpoints` (17 GB). One
  all-in-one file carrying model, text encoder and VAE, so `CheckpointLoaderSimple`
  supplies all three.
- No custom nodes.

## Cost

RTX 4090 24 GB, 1280x704, 24 steps: roughly **50 to 70 s per image**, plus about 20 s on
the first run of a session to load the checkpoint off disk. VRAM peaks near 17 GB, which
is essentially the checkpoint itself.

## Knobs that matter

- **There is no negative prompt, and there cannot be.** Flux is guidance-distilled, so
  there is no unconditional pass. The graph uses `BasicGuider`, which takes one model and
  one conditioning. Reaching for `CFGGuider` or `KSampler` gets you a negative input that
  does nothing.
- **`Flux guidance`: 3.5.** This is the strength control, not cfg. 3.0 to 3.5 suits
  photoreal. Higher gets glossier and more illustrated, not more controlled. 3.5 is the
  value that produced the shipped prompt's hero frame, confirmed by reading it back out of
  the output PNG rather than trusting notes: ComfyUI embeds the executed prompt in the file,
  which makes the image itself the ground truth for what ran.
- **`Sigma schedule`: simple, 24 steps.** Fewer than about 20 loses fine material detail.
- **`Empty latent 1280x704` must be `EmptySD3LatentImage`.** Flux latents are 16 channel,
  so `EmptyLatentImage` produces garbage.
- **Write structural constraints, not optical ones.** Measured on this graph: "no
  windshield, no wings, no windows" and "boxy and unstreamlined" were obeyed, while "no
  lens flare, no bloom, no glow" and "no fill light at all" were ignored. Remove the cause
  instead. "The sun is off frame to the left and out of shot" killed the bloom that "no
  bloom" could not. "The shadowed side of the hull is solid black" killed the fill.
- **Run several seeds.** The off-frame sun constraint landed on one seed in three with
  identical wording. Hold the seed fixed only when the prompt is the variable under test.

Full writeup in `docs/prompting-flux-for-realism.md`, including why genre nouns like
"vessel" pull toward concept art and why tighter framing buys realism.

## Known limits

Flux writes gibberish lettering on any surface that looks like it wants text. Keep such
surfaces out of frame or plan to paint it out.

Flux 2 is not an option on a 24 GB card. `flux2_dev_fp8mixed` is 34 GB and its
`mistral_3_small_flux2_fp8` encoder is another 17 GB, so it block-swaps over PCIe every
step rather than failing outright. `flux-2-klein-4b` is 7.3 GB and would fit alongside the
encoder sequentially, but is untested here.
