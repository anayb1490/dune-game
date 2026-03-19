/**
 * API service — all calls to the FastAPI backend.
 */

// We use a relative path.
// Locally: Vite proxies this to http://127.0.0.1:8000
// Production: Vercel Rewrites handle this to your deployed backend.
const BASE = '/api';

async function post(url, body = {}) {
  const response = await fetch(`${BASE}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }

  return data;
}

async function get(url) {
  const response = await fetch(`${BASE}${url}`);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }

  return data;
}

// ---------------------------------------------------------------------------
// Lobby
// ---------------------------------------------------------------------------

export async function createLobby(hostPlayerId, hostPlayerName, mode = 'basic') {
  return post('/games/lobby', {
    host_player_id: hostPlayerId,
    host_player_name: hostPlayerName,
    mode,
  });
}

export async function joinLobby(playerId, playerName, joinCode) {
  return post('/games/lobby/join', {
    player_id: playerId,
    player_name: playerName,
    join_code: joinCode,
  });
}

export async function selectFaction(gameId, playerId, faction) {
  return post(`/games/${gameId}/faction`, {
    player_id: playerId,
    faction,
  });
}

export async function startGame(gameId, playerId) {
  return post(`/games/${gameId}/start?player_id=${playerId || ''}`);
}

// ---------------------------------------------------------------------------
// Game state
// ---------------------------------------------------------------------------

export async function getGameState(gameId, playerId) {
  const params = playerId ? `?player_id=${playerId}` : '';
  return get(`/games/${gameId}${params}`);
}

// ---------------------------------------------------------------------------
// Game actions
// ---------------------------------------------------------------------------

export async function advancePhase(gameId, playerId) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'advance_phase',
    payload: {},
  });
}

export async function placeBid(gameId, playerId, amount) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'place_bid',
    payload: { amount },
  });
}

export async function passBid(gameId, playerId) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'pass_bid',
    payload: {},
  });
}

export async function selectTraitor(gameId, playerId, traitorCardId) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'select_traitor',
    payload: { traitor_card_id: traitorCardId },
  });
}

export async function submitStormDial(gameId, playerId, number) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'submit_storm_dial',
    payload: { number },
  });
}

// ---------------------------------------------------------------------------
// Revival actions
// ---------------------------------------------------------------------------

export async function reviveForces(gameId, playerId, count) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'revive_forces',
    payload: { count },
  });
}

export async function reviveLeader(gameId, playerId, leaderId) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'revive_leader',
    payload: { leader_id: leaderId },
  });
}

// ---------------------------------------------------------------------------
// Shipment & Movement actions
// ---------------------------------------------------------------------------

export async function shipForces(gameId, playerId, territoryName, sector, count, specialCount = 0) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'ship_forces',
    payload: { territory_name: territoryName, sector, count, special_count: specialCount },
  });
}

export async function moveForces(gameId, playerId, fromTerritory, fromSector, toTerritory, toSector, regularCount, specialCount = 0) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'move_forces',
    payload: {
      from_territory: fromTerritory,
      from_sector: fromSector,
      to_territory: toTerritory,
      to_sector: toSector,
      regular_count: regularCount,
      special_count: specialCount,
    },
  });
}

// ---------------------------------------------------------------------------
// Battle actions
// ---------------------------------------------------------------------------

export async function submitBattlePlan(gameId, playerId, forcesDialed, leaderId = null, weaponCardId = null, defenseCardId = null) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'submit_battle_plan',
    payload: {
      forces_dialed: forcesDialed,
      leader_id: leaderId,
      weapon_card_id: weaponCardId,
      defense_card_id: defenseCardId,
    },
  });
}

// ---------------------------------------------------------------------------
// Nexus (Alliance) actions
// ---------------------------------------------------------------------------

export async function proposeAlliance(gameId, playerId, targetFaction) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'propose_alliance',
    payload: { target_faction: targetFaction },
  });
}

export async function acceptAlliance(gameId, playerId, proposerFaction) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'accept_alliance',
    payload: { proposer_faction: proposerFaction },
  });
}

export async function breakAlliance(gameId, playerId) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'break_alliance',
    payload: {},
  });
}

export async function passNexus(gameId, playerId) {
  return post(`/games/${gameId}/action`, {
    player_id: playerId,
    action_type: 'pass_nexus',
    payload: {},
  });
}

// ---------------------------------------------------------------------------
// Legacy (kept for backward compatibility with tests)
// ---------------------------------------------------------------------------

export async function createGame(players, mode = 'basic') {
  return post('/games', { players, mode });
}