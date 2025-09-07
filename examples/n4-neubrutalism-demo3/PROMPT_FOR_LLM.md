You are updating our app frontend to use the Niagara Neubrutalism style.

Goal: Render N4 chat as Niagara-style nodes with stateful edges and a collapsible navigator, matching the demo in src/App.tsx.

Implement:
1) Roles and Styles
- Roles: user, system, process.
- Process nodes have dashed 2px border.
- Header/body colors from ROLE_STYLE. Include header icon.

2) Layout
- Fixed bubble width (~440px) in a flex-wrap container so rows step down as the canvas narrows.
- SVG overlay draws edges.

3) Edges
- computeEdgePoints(aRect, bRect, aIsLeft, bIsLeft, canvasRect):
  - if |Δy| < 40 → straight line
  - else elbow: right → down → right
- Animation classes by status: running (poly-run), awaiting_approval (poly-await), changes_requested (poly-change), approved (solid).

4) Project Navigator
- Collapsible 'Chat Sessions' with Rename / Delete / New (prompt/confirm for now).

5) Accessibility
- ≥32px hit areas, contrast ≥4.5:1, semantic buttons/inputs; Enter to send.

State:
Message = { id, role, text, time, status?, blocks? }
status ∈ { running, awaiting_approval, approved, changes_requested }.

Acceptance:
- Demo seed shows alternating lanes with animated edges and navigator actions work.
- Resizing causes step-down layout and elbow edges when wrapping occurs.
