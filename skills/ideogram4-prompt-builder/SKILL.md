---
name: ideogram4-prompt-builder
description: >
  Generate structured JSON prompts for Ideogram 4 image generation. Use this skill
  whenever the user wants to create, expand, or refine an Ideogram 4 prompt — whether
  they give a plain natural-language description OR a reference image with annotated
  bounding boxes marking composition elements. Trigger on any request involving
  Ideogram 4 prompt generation, caption building, magic prompt expansion, or structured
  JSON caption creation. Also trigger when the user uploads an image with colored
  bounding boxes/rectangles and labels overlaid on it (composition reference mode).
  Always use this skill instead of writing JSON prompts from scratch.
---

# Ideogram 4 JSON Prompt Builder

Generates a valid Ideogram 4 structured JSON caption from either:
- **Mode A — Natural language**: A plain-text description of the desired image.
- **Mode B — Annotated image**: A reference image with colored bounding boxes and
  text labels marking the spatial elements, plus an optional natural-language
  instruction to guide style/content changes.

The JSON output is the **only deliverable** — inference parameters (`num_steps`,
`sampler_preset`, `height`, `width`, etc.) are set automatically by the pipeline
and must NOT be included.

---

## JSON Caption Schema (strict)

```
{
  "high_level_description": "<string>",   // strongly recommended
  "style_description": {                  // required
    "aesthetics": "<string>",             // required
    "lighting":   "<string>",             // required
    "medium":     "<string>",             // required
    // exactly ONE of:
    "photo":      "<string>",             // photographic medium only
    "art_style":  "<string>",             // all non-photo mediums
    "color_palette": ["#RRGGBB", ...]     // optional, up to 16 colors, UPPERCASE hex
  },
  "compositional_deconstruction": {       // required
    "background": "<string>",             // required, must come before elements
    "elements": [                         // required
      // obj element:
      { "type": "obj",  "bbox": [y_min, x_min, y_max, x_max], "desc": "<string>", "color_palette": [...] }
      // text element:
      { "type": "text", "bbox": [y_min, x_min, y_max, x_max], "text": "<literal>", "desc": "<string>", "color_palette": [...] }
    ]
  }
}
```

**Critical rules:**
- `bbox` coordinates are integers in **0–1000** normalized space (origin top-left).
  Format: `[y_min, x_min, y_max, x_max]`.
- `bbox` and `color_palette` are optional per-element; include only when spatially
  relevant or when the user/image specifies them.
- Key order inside each element **must** match the table above exactly.
- `color_palette` hex values: UPPERCASE `#RRGGBB` only (e.g. `#1B1B2F` not `#1b1b2f`).
- `medium` values: use snake_case (e.g. `"photograph"`, `"digital_illustration"`,
  `"oil_painting"`, `"3d_render"`, `"graphic_design"`).
- Use `"photo"` key for photographic captions, `"art_style"` key for everything else.
  Never include both.

---

## Mode A — Natural Language Input

**Trigger:** User provides a text description with no reference image.

### Steps

1. **Parse intent** — identify subject(s), setting, style, mood, any explicit
   spatial or color requirements.

2. **Infer medium** — decide `photograph` vs a non-photo medium based on
   described style. When ambiguous, prefer `digital_illustration` for
   anime/fantasy/art requests and `photograph` for realistic requests.

3. **Build `high_level_description`** — one or two sentences summarizing the
   full scene. Be specific and vivid.

4. **Build `style_description`** — fill `aesthetics`, `lighting`, `medium`,
   and `photo` or `art_style`. Extract or invent a coherent `color_palette`
   of 3–7 dominant hex colors that match the mood.

5. **Build `compositional_deconstruction`** — write a rich `background`
   paragraph, then list each distinct subject/object as an `"obj"` element and
   any in-image text as a `"text"` element. Assign plausible `bbox` values
   that reflect natural composition (rule of thirds, foreground/background
   layering). For text elements, `text` must contain the **literal string** to
   render.

6. **Output** — emit the final JSON only (no markdown fences, no preamble,
   no inference params). Always pretty-print with 2-space indent.

---

## Mode B — Annotated Image Input

**Trigger:** User uploads an image that has colored bounding boxes (rectangles)
with numbered labels and/or text annotations overlaid on it, optionally
accompanied by a natural-language instruction ("change style to watercolor",
"keep layout, make it daytime", etc.).

### Reading the annotation layer

The annotated image encodes composition information visually:

| Visual cue | Meaning |
|:-----------|:--------|
| Colored rectangle | Bounding box for one element |
| Number label (corner) | Element index / ordering |
| Short text inside/near box | `desc` for that element (or `text` for graffiti/signs) |
| Color swatches strip (bottom or corner) | Suggested `color_palette` for `style_description` |

### Steps

1. **Read the image carefully** — identify every annotated rectangle, its
   number, its text label, and the pixel region it covers relative to the full
   image dimensions (width W × height H).

2. **Convert pixel bbox → 0–1000 space**:
   ```
   y_min = round(box_top    / H * 1000)
   x_min = round(box_left   / W * 1000)
   y_max = round(box_bottom / H * 1000)
   x_max = round(box_right  / W * 1000)
   ```

3. **Classify each element** — if the annotation text is a quoted string or
   clearly a literal word/phrase to render in the image → `"text"` type with a
   `"text"` field. Otherwise → `"obj"` type.

4. **Extract color swatches** — if a color strip is visible, convert each
   swatch to its nearest `#RRGGBB` uppercase hex and populate
   `style_description.color_palette`.

5. **Infer or apply style instruction** — if the user added a natural-language
   modifier, apply it to `style_description` (adjust `aesthetics`, `lighting`,
   `medium`, `art_style`/`photo`). Otherwise, infer style from the visual
   content and mood of the reference image.

6. **Compose the full JSON** following the schema above, ordering `elements`
   by their numbered annotation index.

7. **Output** — same as Mode A: JSON only, 2-space indent, no fences.

---

## Common pitfalls to avoid

- ❌ Including `num_steps`, `guidance_scale`, `sampler_preset`, `height`,
  `width`, `seed` — these are pipeline params, not prompt fields.
- ❌ Mixing `photo` and `art_style` in the same `style_description`.
- ❌ Using lowercase hex (`#ff0000`) — always uppercase (`#FF0000`).
- ❌ Wrong bbox order — must be `[y_min, x_min, y_max, x_max]`, NOT
  `[x_min, y_min, x_max, y_max]`.
- ❌ Markdown code fences around the JSON output.
- ❌ `\uXXXX` escapes for non-ASCII characters — write them literally.
- ❌ Omitting `background` before `elements` in `compositional_deconstruction`.

---

## Quick reference: full example

See `references/full_example.json` for the canonical fox-girl graffiti example
demonstrating both `"obj"` and `"text"` elements, a color palette strip, and
annotated bounding boxes.