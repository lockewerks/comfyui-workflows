<div align="center">

<img src="assets/comfyui-workflows.ico" width="96" alt="ComfyUI Workflows">

# ComfyUI Workflows

**ComfyUI graphs that earned their place. Every node named for its job, every cost measured.**

[![license](https://img.shields.io/badge/license-MIT-d6262a?style=flat-square)](LICENSE)
![platform](https://img.shields.io/badge/platform-ComfyUI-d6262a?style=flat-square)

</div>

---

Working ComfyUI graphs that earned their place. Every file here ran end to end on
real hardware and produced output worth keeping. Experiments, dead ends, and
"almost" versions do not get committed.

Each workflow ships with a notes file next to it that states what it is for, which
models it needs, what it costs in VRAM and wall time, and which settings actually
matter. If you can't answer those four questions about a graph, it isn't ready to
commit.

## Loading a workflow

Files in `workflows/` are ComfyUI UI-format graphs. Drag the `.json` onto the
ComfyUI canvas, or use Workflow > Open.

Read the matching `.md` first. It lists the checkpoints, LoRAs, and custom nodes
the graph expects. A missing model shows up as a red node with an empty dropdown;
a missing custom node shows up as a red box with the class name in it.

## Submitting without the Run button

Every node that carries meaning is titled, and the titles are stable. That makes
them usable as lookup keys, so you can load a graph once and submit many variants
against it:

```js
const app = window.app;
const api = (await app.graphToPrompt()).output;
const byTitle = t => Object.keys(api).find(k => api[k]._meta?.title === t);

const job = structuredClone(api);
job[byTitle('Positive prompt')].inputs.text = 'a lighthouse at dusk';
job[byTitle('Sampler')].inputs.seed = 1234;

await fetch('/prompt', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ prompt: job, client_id: app.api.clientId }),
});
```

Renaming a titled node breaks anything that looks it up. Treat titles as part of
the interface. `CONVENTIONS.md` defines the canonical role names.

To save a graph back to ComfyUI, **percent-encode the slash in the path**:

```js
await fetch('/userdata/' + encodeURIComponent('workflows/NAME.json') + '?overwrite=true',
  { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(app.graph.serialize()) });
```

`POST /userdata/workflows/NAME.json` returns 405 Method Not Allowed. Only the path
segment is routable, so the subdirectory has to arrive as `workflows%2FNAME.json`. The
same applies to reading it back with GET.

## Validating before commit

```
python tools/sanitize_workflow.py workflows/*.json    # strip machine-specific UI state
python tools/check_workflow.py    workflows/*.json    # then validate
```

Sanitize first. Several nodes cache the last run's results in their serialized widget
values, and VideoHelperSuite's `VHS_VideoCombine` is the worst: it stores a
`videopreview` block with a `fullpath` to the output file, so committing a video graph
straight out of ComfyUI publishes a home directory path and pins the graph to one
machine. The node rebuilds that block on the next run, so dropping it costs nothing.

The checker then fails on untitled nodes, titles that are just the class name, cryptic
abbreviations, duplicate titles within a graph, missing notes files, and any absolute
path that survived. It warns on samplers left in randomize mode, which quietly ruins
A/B comparisons.

## Reference hardware

Graphs were built and timed on this box. Runtimes in the notes files scale from it:

```
GPU     RTX 4090, 24 GB VRAM
RAM     185 GB
Host    ComfyUI in WSL (Debian), port 8188
```

VRAM is the binding constraint on most of these. A model that fits beats a better
model that doesn't: two 14 GB experts on a 24 GB card thrash to disk on every
clip, and the smaller model finishes several times faster with more frames and
more steps.
