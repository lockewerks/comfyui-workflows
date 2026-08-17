# Conventions

Two rules carry this repo: nodes are named for a stranger, and a graph has to earn
its commit.

## Naming nodes

A default node title tells you the class. It does not tell you the job that node is
doing in this particular graph. `CLIPTextEncode` appears three times in a graph and
means something different each time. Title it.

**Every node gets a title that names its role, not its class.**

| Default | Title it |
| --- | --- |
| `CheckpointLoaderSimple` | `Load checkpoint` |
| `CLIPTextEncode` | `Positive prompt` |
| `CLIPTextEncode` | `Negative prompt` |
| `KSampler` | `Sampler` |
| `VAEDecode` | `Decode to image` |
| `EmptyLatentImage` | `Empty latent 1024x1024` |
| `LoraLoader` | `LoRA: film grain` |
| `ImageUpscaleWithModel` | `Upscale to 4K` |

Rules:

- Sentence case. ASCII only. Forty characters or fewer so it reads on the canvas at
  normal zoom.
- Say what it does here. `Upscale to 4K` beats `Upscale`. `LoRA: film grain` beats
  `LoRA 1`.
- No abbreviations. `POS`, `K`, `VD`, `CKPT` are out. They save four keystrokes at
  build time and cost the next reader a graph trace.
- Unique within a graph. Two of a kind get distinguished by role, not by number:
  `Sampler: base pass` and `Sampler: refine pass`, not `Sampler 1` and `Sampler 2`.
- Titles are an interface. Anything submitting jobs by `_meta.title` breaks when you
  rename a node, so a rename is a breaking change to that workflow.

### Canonical role names

Use these verbatim when the role exists, so scripts written against one graph work
against the next one:

```
loaders                  conditioning             sampling / output
Load checkpoint          Positive prompt          Sampler
Load diffusion model     Negative prompt          Sampler: base pass
Load VAE                 Empty latent             Sampler: refine pass
Load CLIP                Encode image to latent   Decode to image
Load LoRA                Load image               Save image
                         Load audio
```

Video graphs add these. `Motion prompt` replaces `Positive prompt` in an
image-to-video graph, because the two are not the same job: the start frame already
supplies the subject, so the text exists to carry what must hold across the clip.

```
Load start frame         Motion prompt            Decode to video frames
Load T5 text encoder     Start frame to latent    Save video
```

Extend with a colon and a specific: `Load LoRA: hand fix`, `Save image: contact
sheet`. Do not invent a synonym for a role that already has a name here.

### Notes on the canvas

A `Note` node explaining a non-obvious choice is worth more than a clever title.
Put the reason in a note: which setting is load-bearing, what happens if you move
it, what was tried and failed. Notes and reroutes are exempt from the title rule.

## What earns a commit

A workflow goes in when all five are true:

1. It ran end to end on the reference box and produced output worth keeping.
2. It does something the stock templates don't, or it encodes a setting that took
   real work to find.
3. A notes file sits next to it: purpose, required models and custom nodes, measured
   VRAM and wall time, and the knobs that matter.
4. `python tools/check_workflow.py` passes on it.
5. It loads on a clean install once the listed models are in place. No absolute
   paths, no filenames only present on one machine.

Not committed: parameter sweeps, diagnostic probes, anything saved mid-debug, and
anything that only worked once.

## Reproducibility

Set `control_after_generate` to `fixed` on every sampler in a graph meant for
comparison. ComfyUI defaults to `randomize`, which silently hands you two different
generations and turns an A/B into two unrelated images. The checker warns about
this, it cannot fix it.

## Structural rules learned the hard way

- Anything that must hold across a video clip belongs in the motion prompt. A start
  frame anchors frame one and argues for nothing after it.
- Keep constraints symmetric. Banning "brightening" while asking for "stays black"
  is a ratchet pointed at zero, and it produces the exact inverse bug.
- Frame interpolation does not belong in a per-shot graph. It fights the diffusion
  model for VRAM and eventually deadlocks in a node you cannot interrupt. Run it
  once over the assembled sequence, as its own workflow.
- **A job that reports `success` can still have produced nothing.** Ask a video model
  for a clip longer than it can hold together and it returns a valid file of the right
  length, right frame count, right codec, containing pure video black. No error, no
  warning. Check mean luma before you trust a run: a clip that reads 16.0 at every
  sample is black, and one that is black from frame zero rather than fading to it was
  never generated at all. Status strings are not verification.
- Motion is a roughly fixed budget, not a rate. Doubling the frame count of a video
  graph does not buy twice the camera movement, it spreads the same movement over twice
  the duration, so a long clip reads slower and eventually nearly static. Length and
  motion amplitude trade against each other and neither is set by the prompt.

## Layout

```
workflows/NAME.json    UI-format graph, drag onto the canvas
workflows/NAME.md      notes: purpose, requirements, cost, knobs
api/NAME.json          optional /prompt-format export for headless submission
tools/                 validation
```

Name files in kebab-case after what they produce, not after the model they use:
`still-life-product-shot.json`, not `sdxl-test-3.json`. Models get swapped, purpose
does not.

## Notes template

Copy this into `workflows/NAME.md` and fill it in. Keep it short. Measured numbers
only, no estimates.

```markdown
# Name of the thing it makes

One paragraph: what this produces and when to reach for it.

## Requires

- Checkpoint: exact-filename.safetensors (source URL)
- LoRA: exact-filename.safetensors (source URL)
- Custom nodes: repo name, or "none"

## Cost

- VRAM: N GB peak
- Wall time: N s per image, or N min per clip, on the reference box
- Output: resolution, frame count, format

## Knobs that matter

- `Sampler` steps: what changes above and below the set value
- Anything load-bearing, and what breaks when you move it

## Known limits

What it does badly, and what to use instead when you hit that.
```
