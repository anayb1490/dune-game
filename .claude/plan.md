# Plan: Territory Adjacency, Event Log, and Board Highlighting

## Overview
Three interconnected features:
1. **Territory adjacency enforcement** — backend validates movement is legal; frontend filters dropdown to only show reachable territories
2. **Persistent event log** — `game_log` accumulates all phase notifications; right-column panel always shows history (not just current phase)
3. **Board highlighting** — selecting a "From" or "To" territory in the shipment panel glows it on the SVG board

---

## Backend Changes (4 files)

### 1. `backend/app/data/adjacency.py` (NEW)
Compute adjacency algorithmically from sector + ring data. No hardcoding — derived purely from `TERRITORIES`.

**Algorithm:**
- Ring numbers: POLAR_SINK = -1, STRONGHOLD = 0, ROCK = 1, SAND = 2
- `sectors_touch(s1, s2)`: any sector pair within 1 step (mod-18 wraparound)
- **Polar Sink** → adjacent to all STRONGHOLD and ROCK territories (ring 0 & 1)
- **All other pairs** → adjacent if `|ring1 - ring2| ≤ 1` AND their sectors touch

Exports:
```python
ADJACENCY: dict[str, frozenset[str]]   # territory → frozenset of adjacent territory names
def is_adjacent(t1: str, t2: str) -> bool
```

### 2. `backend/app/models/player.py`
Add one field after `is_eliminated`:
```python
has_moved: bool = Field(default=False,
    description="True if this player has already moved forces this Shipment turn.")
```

### 3. `backend/app/models/game_state.py`
Add one field (public, not secret):
```python
game_log: list[str] = Field(default_factory=list,
    description="Cumulative event log — all phase messages appended over game history.")
```

### 4. `backend/app/services/game/shipment.py`
Two enforcement additions to `move_forces()`:

**Adjacency check** (raises `ValueError` if non-adjacent):
```python
from ...data.adjacency import is_adjacent
if not is_adjacent(from_territory, to_territory):
    raise ValueError(f"{from_territory} is not adjacent to {to_territory}.")
```

**One-move-per-turn** (raises `ValueError` if already moved):
```python
if player.has_moved:
    raise ValueError("You have already moved forces this turn.")
# After successful move:
updated_player = player.model_copy(update={"has_moved": True})
```

### 5. `backend/app/services/game/engine.py`
Two changes:

**A. Populate `game_log` in Step 1 (resolve)** — in every automated phase case, append messages to game_log:
```python
case GamePhase.STORM:
    resolved = resolve_storm(game_state)
    messages = _storm_messages(game_state, resolved)
    new_log = (game_state.game_log + messages)[-60:]   # cap at 60
    return resolved.model_copy(update={
        "current_phase": GamePhase.STORM,
        "phase_messages": messages,
        "game_log": new_log,
        "current_player_index": 0,
    })
# … same pattern for SPICE_BLOW, CHOAM_CHARITY, SPICE_COLLECTION, MENTAT_PAUSE
```
Step 2 (advance) does NOT re-append — game_log already has the entries.

**B. Reset `has_moved` in `_advance_player_or_phase()`** — when a player ends their shipment turn, reset their flag:
```python
def _advance_player_or_phase(game_state, current_phase):
    next_idx = game_state.current_player_index + 1
    curr_idx = game_state.current_player_index

    # Reset has_moved for the player finishing their turn
    players = list(game_state.players)
    if 0 <= curr_idx < len(players):
        players[curr_idx] = players[curr_idx].model_copy(update={"has_moved": False})

    if next_idx >= len(players):
        return game_state.model_copy(update={
            "current_phase": next_phase(current_phase),
            "current_player_index": 0,
            "players": players,
        })
    else:
        return game_state.model_copy(update={
            "current_player_index": next_idx,
            "players": players,
        })
```

*(state_filter.py needs no changes — `game_log` and `has_moved` are not secret fields)*

---

## Frontend Changes (5 files)

### 6. `frontend/src/utils/adjacency.js` (NEW)
Mirror the backend algorithm in JavaScript so the "To" dropdown can be filtered client-side:
```js
export function getAdjacentTerritories(fromName, territories) {
  // Returns array of territory names adjacent to fromName
  // Uses same ring + sector-touch logic as backend
}
```

### 7. `frontend/src/components/board/GameBoard.jsx`
Add two new props: `highlightFrom` (string) and `highlightTo` (string).

In `TerritoryNode`, add a `highlight` prop with values `'from' | 'to' | null`:
- `'from'` → green glow ring behind the node circle (`stroke="#22c55e"`, `strokeWidth=3`, outer ring at `r + 5`)
- `'to'`   → blue glow ring (`stroke="#3b82f6"`, same style)

Pass `highlight` to each `TerritoryNode` based on whether its name matches `highlightFrom` or `highlightTo`.

### 8. `frontend/src/components/game/ShipmentPanel.jsx`
Two additions:

**A. `onHighlight` callback prop** — called whenever selection changes:
```js
export default function ShipmentPanel({ ..., onHighlight }) {
  // When moveFrom changes → onHighlight(newFrom, '')
  // When moveTo changes   → onHighlight(moveFrom, newTo)
  // When shipTerritory changes → onHighlight('', '') (ship doesn't highlight move)
}
```

**B. Filter "To" dropdown to adjacent territories** — when `moveFrom` is set:
```js
import { getAdjacentTerritories } from '../../utils/adjacency.js'

const validMoveTargets = moveFrom
  ? getAdjacentTerritories(moveFrom, territories)
  : territoryNames
```
Use `validMoveTargets` for the "To..." dropdown options instead of `territoryNames`.

Also reset `moveTo` / `moveToSector` when `moveFrom` changes (to avoid stale selection).

### 9. `frontend/src/components/game/GameLog.jsx` (NEW)
Compact scrollable event log component:
```jsx
export default function GameLog({ entries = [] }) {
  // Auto-scroll to bottom when entries change
  // Show last 30 entries, newest at bottom
  // Color-code by content keywords: storm=blue, spice=amber, loses=red, collects=green
  // Max height ~150px with overflow-y-auto
}
```

### 10. `frontend/src/components/game/GameView.jsx`
Three additions:

**A. Import GameLog**

**B. Board highlight state:**
```js
const [boardHighlight, setBoardHighlight] = useState({ from: '', to: '' })
```
Pass to ShipmentPanel:
```jsx
<ShipmentPanel
  ...
  onHighlight={(from, to) => setBoardHighlight({ from, to })}
/>
```
Pass to GameBoard:
```jsx
<GameBoard
  territories={territories}
  players={players}
  stormSector={storm_sector}
  highlightFrom={boardHighlight.from}
  highlightTo={boardHighlight.to}
/>
```
Clear highlight when shipment phase ends:
```js
// Reset when phase changes away from shipment
useEffect(() => {
  if (current_phase !== 'shipment_and_movement') {
    setBoardHighlight({ from: '', to: '' })
  }
}, [current_phase])
```

**C. Replace the `hasMessages` section with a persistent `GameLog`:**
```jsx
{/* Persistent event log — always shown once game has events */}
{gameState.game_log?.length > 0 && (
  <GameLog entries={gameState.game_log} />
)}
```
Remove the old `{hasMessages && ...}` block (game_log subsumes it since messages are appended there).

---

## Execution Order

1. Backend data + models first (adjacency.py, player.py, game_state.py)
2. Backend services (shipment.py, engine.py)
3. Run `python -B -m pytest backend/tests/ -v` — all 155 should still pass
4. Frontend utility (adjacency.js)
5. Frontend components (GameBoard, ShipmentPanel, GameLog, GameView)
6. Manual smoke test via browser

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Adjacency data | Computed from sectors, not hardcoded | Stays in sync if sectors are corrected later |
| One-move tracking | `has_moved` on Player model | Simplest; resets naturally at turn-end |
| Game log location | `game_log` on GameState (backend) | All players see same history; survives reconnect |
| Log cap | 60 entries server-side | Prevents unbounded growth; 60 covers ~7 full turns |
| Frontend adjacency | Mirror JS algorithm | Avoids extra API call; territory data already in gameState |
| Board highlight | Green=From, Blue=To glow rings | Intuitive; doesn't obscure existing territory visuals |
