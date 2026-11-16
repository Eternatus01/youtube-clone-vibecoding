# Design spec (YouTube 2024 look, Russian UI). Frontend reads this; follow numbers exactly.

## Anti-slop (forbidden)
No gradients (except skeleton shimmer), no glassmorphism/blur, no glow, no purple/indigo accents, no big soft shadows, no card borders, no emoji as icons, no hero banners, no centered marketing layouts, no hover lift/scale on cards, no animations >200ms, no lorem ipsum, no placeholder "Coming soon" screens.
Icons: lucide-vue-next only (stroke 1.75, size 20/24). Font: Roboto via @fontsource/roboto (400,500,700), self-hosted, no CDN.

## Tokens (CSS variables on :root and [data-theme=light], theme via data attribute, saved in localStorage, respects prefers-color-scheme)
Dark: bg #0f0f0f; surface #272727; surface-hover #3f3f3f; overlay-hover rgba(255,255,255,.1); text #f1f1f1; text-2 #aaaaaa; divider rgba(255,255,255,.1); accent #3ea6ff; danger #ff4e45.
Light: bg #ffffff; surface #f2f2f2; surface-hover #e5e5e5; overlay-hover rgba(0,0,0,.05); text #0f0f0f; text-2 #606060; divider rgba(0,0,0,.1); accent #065fd4; danger #cc0000.
Brand red #ff0000 only on logo mark. Radius: 12 thumbnails/player, 8 menus/dialogs, 18 pill buttons/chips, 4 duration badge, 50% avatars. Spacing scale 4/8/12/16/24/40.
Type: body 14/20; video title 16/22 weight 500 (clamp 2 lines); meta 12/18 text-2; watch title 20/28 weight 700; headings 500-700. Numbers/dates in ru: "1,2 тыс. просмотров", "3 дня назад" (Intl.RelativeTimeFormat/NumberFormat compact), duration "12:34".
Transitions: background-color/opacity 100-150ms ease only. Visible :focus-visible ring (2px accent), keyboard navigable.

## Layout
Header: height 56, fixed; left burger + logo; center search (max-width 640, input height 40, radius 20 left, search button right with surface bg, 1px divider border); right: upload icon-button, avatar 32 (menu) or "Войти" outlined pill with accent text/border.
Sidebar: 240 expanded / 72 mini (icon above 10px label) / hidden+overlay <792. Items height 40, radius 10, icon 24, active = surface bg + weight 500. Sections divided by 1px divider. Collapsed state saved.
Home: sticky chips row under header (height 48, pill chips 32px high, surface bg, selected chip inverted text/bg). Grid: gap 16 horizontal, 40 vertical, columns auto-fill minmax(300px,1fr), max 5 columns. Page padding 24.
Video card: no background/border; 16:9 thumb radius 12 with object-fit cover; duration badge bottom-right 4px offset (rgba(0,0,0,.8), #fff, 12/500, radius 4); below thumb: 12px gap, row of avatar 36 + text column (title, channel name text-2, "N просмотров • время" text-2); hover only: channel name text brightens. Private/unlisted/hidden show a small lock/eye-off label in meta, not a colored banner.
Watch: two columns, max-width ~1750, gap 24; left flexible (player 16:9 radius 12, black bg, native controls ok), right column 402 fixed with compact recommendation rows (thumb 168x94 radius 8 + title 14/500 + meta 12); under 1015px right column goes below. Title 20/700; owner row: avatar 40, name 16/500, subs 12 text-2, Subscribe pill (dark theme: #f1f1f1 bg/#0f0f0f text; light: #0f0f0f bg/#fff text; subscribed state: surface bg + text); like button as pill with icon+count (surface bg, hover surface-hover). Description box: surface bg radius 12 padding 12, collapsed 2 lines + "ещё". Comments: count heading 20/700, input = underline-only field (transparent, 1px bottom border, accent on focus) with Cancel/"Комментировать" pills appearing on focus; comment row avatar 40 + name 13/500 + time 12 text-2 + text 14/20.
Channel: banner area 16:5 neutral surface (no stock images), avatar 128, name 36/700, handle+subs text-2, Subscribe pill, tabs row (Видео, Плейлисты) with 2px bottom underline for active, then the same grid.
Search results: horizontal result rows (thumb 360x202 radius 12 + title 18/400, meta, channel row with small avatar, description 2 lines text-2); stacks under 792.
Upload: centered dialog-like card (surface bg, radius 12, max-width 960), big dashed drop zone with upload icon, selected file row, real progress bar (4px, accent, surface track), metadata form (title with char counter, description, visibility select, thumbnail auto), status line: "Обработка…" → "Готово" with link.
Auth: single centered card 400px (surface bg, radius 12), logo above, labeled inputs 48px high radius 8 1px divider border, accent on focus, full-width accent button 40px, inline error text in danger color (no alert popups).
Moderation/admin: dense table (row 48, sticky header, text-2 header 12/500 uppercase none), status as small outlined text pills (no saturated fills), row actions as icon-buttons with tooltips (title attr).

## States (every screen)
Skeletons matching real card geometry (surface bg, shimmer 1.4s subtle). Empty states: icon 48 text-2 + one sentence + one action. Error states: sentence + "Повторить" button. Toasts bottom-left, surface bg, 4s, no colored backgrounds. Confirm dialogs for delete/hide.

## Responsive
Breakpoints: 1312 (sidebar becomes mini), 1015 (watch single column), 792 (sidebar overlay, search collapses to icon, grid 1-2 cols). Touch targets ≥40px. No horizontal scroll at 360px.