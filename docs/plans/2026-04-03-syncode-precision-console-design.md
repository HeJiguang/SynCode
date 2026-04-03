# SynCode Precision Console Design

## Goal

Rebuild the frontend visual language so SynCode feels like a focused developer product instead of a stitched template. The target baseline is a restrained, premium control-surface inspired by Linear, Vercel, Raycast, and Notion:

- premium, but not decorative
- dark-first, but with a complete light theme
- brand-aware, but not gradient-heavy
- dense enough for work, but with clear hierarchy

## Approved Direction

This redesign follows the `Precision Console` direction:

- solid near-black and warm-neutral light backgrounds
- one primary brand hue used consistently as the accent
- hierarchy expressed through spacing, typography, grouping, and border contrast
- almost no glow, and no “marketing-site” gradients inside the product shell

## Design Tokens

### Color strategy

- Backgrounds use two depth levels only: canvas and elevated surface.
- Cards use translucent surfaces with hairline borders, not thick fills.
- One accent hue represents product intent. Secondary semantic colors are only used for system state.
- Text has three levels: primary, secondary, muted.

### Typography strategy

- Use a modern sans stack with strong title rhythm and quiet body copy.
- Titles carry structure. Body copy explains. Labels orient.
- Uppercase metadata is limited to section framing and status context.

### Shape and spacing

- Radius uses a small family: `10px / 14px / 20px`.
- Layout spacing follows 4px/8px increments.
- Panels and actions align to a tighter grid so the dashboard reads as one system.

### Shadow policy

- Standard panels use almost no visible shadow.
- Floating elements use one controlled shadow token.
- Hover uses border/luminance change before shadow.

## Component Language

### Panel

- One default panel surface
- One stronger panel for primary content blocks
- Optional hover state that lifts contrast, not elevation

### Button

- Primary button is quiet but high-contrast
- Secondary button is outline/surface-based
- Ghost button is text-first and used in navigation/actions
- Focus rings are crisp and thin

### Tag

- Tags are small contextual labels, never mini-buttons
- Neutral tag is default
- Accent tag marks current focus
- Semantic tags are reserved for status

## Dashboard Structure

The dashboard will move from “many same-weight cards” to a three-zone layout:

1. Brand and context header
   Shows greeting, product context, and one dominant next action.

2. Primary work surface
   The left main column holds the user’s current plan, current focus, and active tasks.

3. Secondary rail
   The right rail holds announcements, hot problems, and profile summary as supporting modules.

This change intentionally increases the visual weight of the main workflow while lowering the noise of secondary content.

## Before vs After

### Before

- noisy atmospheric background and over-specified hero
- too many panel styles with similar importance
- inconsistent accent usage
- information blocks feel pasted together rather than orchestrated

### After

- one clear visual language across shell, panels, and status elements
- main workflow gets dominant placement and stronger surface treatment
- supporting content moves into quieter modules
- the page feels more deliberate, productized, and brand-coherent

## Implementation Scope

Phase 1 in this pass:

- rebuild global tokens
- restyle shared `Panel`, `Button`, and `Tag`
- refine app shell framing and navigation
- refactor dashboard into smaller semantic sections

Later phases can extend the same system to login, problems, exams, and admin.
