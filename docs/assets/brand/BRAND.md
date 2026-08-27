# OmniNode brand assets

This directory is the canonical home for the OmniNode logo files. Every OmniNode
repository banner, site header, and slide should pull from **these exact files**
so that all surfaces look the same.

The files here are copied verbatim from the supplied brand package. The only
change is the filename, normalised to kebab-case. **The artwork itself is never
modified** — see [Prohibitions](#prohibitions).

Source of record: *Omninode Branding Guideline — 2026-02-04* (RGB / Screen
sheet). That document is not committed here; this page is the rules summary that
travels with the assets.

---

## Palette

The brand palette is four colours: one neutral and three blues. These are the
only colours that appear in the marks.

| Swatch | Role | HEX | RGB |
|---|---|---|---|
| ⬛ | Charcoal — wordmark on light backgrounds, dark background panels | `#41424e` | 65, 66, 78 |
| 🟦 | Deep blue | `#1b41b1` | 27, 65, 177 |
| 🟦 | Blue — the primary brand blue, and the whole of the 2-colour mark | `#3c82f7` | 60, 130, 247 |
| 🟦 | Cyan — the light end of the full-colour gradient | `#67e8f9` | 103, 232, 249 |

The full-colour mark is a gradient running deep blue → blue → cyan. It is
supplied as a finished file; it is never re-created by hand.

## Typography

The wordmark is set in **Poppins Semibold**, lowercase — `omninode`, never
`OmniNode` and never `OMNINODE`. The wordmark is always used as the supplied
vector file, never re-typed in a live font, so the letterforms and spacing stay
identical everywhere.

## Lockups

Four forms exist. Pick by how much horizontal room the surface has.

| Form | File stem | Use for |
|---|---|---|
| **In-line** | `omninode-inline-*` | Wide surfaces — README banners, site headers, email signatures. The default. |
| **Stacked** | `omninode-stacked-*` | Square-ish or narrow surfaces — social avatars, posters, slide title cards. |
| **Icon** | `omninode-icon-*` | The mark alone, where the name is already present — favicons, app icons, avatars. |
| **Wordmark** | `omninode-wordmark-*` | The name alone, where the mark is already present nearby. |

## Which variant on which background

This is the binding rule, and it is the one most often gotten wrong.

| Background | Variant | Why |
|---|---|---|
| **White / light** | Full colour (`-full-color`) | The default. The gradient is designed against white. |
| **White / light, single-colour constraint** | Black (`-black`) | Print, faxable documents, single-ink contexts. |
| **Dark / charcoal / photographic** | White (`-white`) | The guideline shows the white variant exclusively on a dark charcoal field. |

Do not place the full-colour mark on a dark or mid-tone background — the cyan
end of the gradient loses contrast. Do not place the white mark on white.

A 2-colour variant (blue + charcoal, no gradient) also exists in the brand
package for limited-ink work. It is not vendored here because no OmniNode
digital surface currently needs it; pull it from the brand package if a print
job does.

## Clearspace and minimum size

> These two rules are **conventions adopted here**, not values quoted from the
> guideline sheet — that sheet specifies variants, palette, and typography, but
> carries no clearspace or minimum-size diagram. They are recorded so every repo
> applies the same numbers rather than each inventing its own.

**Clearspace.** Keep a margin equal to the height of the icon on all four sides
of any lockup. Nothing — text, rules, badges, borders — enters that margin.

**Minimum size.** The brand package supplies rasters down to 16 px, which sets
the floor:

- In-line lockup: **69 × 16 px** minimum (the supplied 16 px raster).
- Stacked lockup and icon: **16 px** tall minimum.

Below those sizes, drop to the icon alone rather than shrinking a lockup until
the wordmark fills in.

## Prohibitions

Never do any of the following to a supplied file:

- **Recolour it.** No alternative palettes, no brand-adjacent teals, no
  single-colour fills outside the supplied black and white variants.
- **Re-draw or re-type it.** No hand-built approximations of the mark, no
  wordmark set in a substitute font.
- **Add effects.** No drop shadows, glows, outlines, strokes, or bevels.
- **Distort it.** Scale proportionally only — never stretch one axis.
- **Rotate or reflow it.** No re-arranging the icon and wordmark into a lockup
  the brand package does not supply.
- **Add a tagline into the lockup.** Taglines are separate typographic elements
  set beside the logo, not baked into it.
- **Place it on a busy background** without a solid field behind it.

---

## Files

Vector (SVG) is used wherever the supplied vector is correctly framed. For the
single-colour variants the brand package's `Others/` SVGs ship a broken
oversized canvas that clips the artwork, so the correctly-framed `@4x` PNG is
vendored instead — it is the same official artwork at 1143 px wide, which is
ample for any web header.

| File | Format | Intrinsic size |
|---|---|---|
| `omninode-inline-full-color.svg` | SVG | 285.64 × 66.46 |
| `omninode-inline-white.png` | PNG | 1143 × 267 |
| `omninode-inline-black.png` | PNG | 1143 × 267 |
| `omninode-stacked-full-color.svg` | SVG | 260.55 × 279.75 |
| `omninode-stacked-white.png` | PNG | 1043 × 1120 |
| `omninode-stacked-black.png` | PNG | 1043 × 1120 |
| `omninode-icon-full-color.svg` | SVG | 128.86 × 147.53 |
| `omninode-icon-white.png` | PNG | 517 × 592 |
| `omninode-icon-black.png` | PNG | 517 × 592 |
| `omninode-wordmark-black.svg` | SVG | 260.55 × 40.42 |
| `omninode-wordmark-grey.svg` | SVG | 260.55 × 40.42 |
| `omninode-wordmark-white.svg` | SVG | 260.55 × 40.42 |

The full-colour in-line SVG and the white in-line PNG share a 4.29:1 aspect
ratio, so they can be swapped for one another at a fixed width with no layout
shift.

## The README banner recipe

Every OmniNode repository README opens with the same block. Copy it verbatim,
adjusting only the path depth if the assets live elsewhere:

```html
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/brand/omninode-inline-white.png">
    <source media="(prefers-color-scheme: light)" srcset="docs/assets/brand/omninode-inline-full-color.svg">
    <img alt="omninode" src="docs/assets/brand/omninode-inline-full-color.svg" width="420">
  </picture>
</p>
```

`<picture>` with `prefers-color-scheme` is the mechanism GitHub honours for
theme-aware README images. The `<img>` fallback carries the full-colour file so
any renderer that ignores `<picture>` still gets a valid light-background mark.

`width="420"` is the fleet-standard header width. It renders the lockup at
roughly 98 px tall, which clears the 16 px minimum by a wide margin and leaves
the surrounding paragraph margins acting as clearspace.
