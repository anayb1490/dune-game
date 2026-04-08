import GameBoard from './components/board/GameBoard.jsx'

// Mock territory data matching backend territory definitions
const TERRITORY_TYPES = {
  'Polar Sink': 'polar_sink',
  'Arrakeen': 'stronghold', 'Carthag': 'stronghold', 'Sietch Tabr': 'stronghold',
  "Tuek's Sietch": 'stronghold', 'Habbanya Sietch': 'stronghold',
  'Hole in the Rock': 'rock', 'Sihaya Ridge': 'rock', 'Plastic Basin': 'rock',
  'Harg Pass': 'rock', 'False Wall East': 'rock', 'False Wall South': 'rock',
  'False Wall West': 'rock', 'Shield Wall': 'rock', 'Rim Wall West': 'rock',
  'Pasty Mesa': 'rock', 'Bight of the Cliff': 'rock', 'South Mesa': 'rock',
  'Tsimpo': 'rock', 'Broken Land': 'rock', 'Cielago East': 'rock',
  'Cielago West': 'rock', 'Cielago North': 'rock', 'Wind Pass': 'rock',
  'Wind Pass North': 'rock',
  'Imperial Basin': 'sand', 'Arsunt': 'sand', 'Hagga Basin': 'sand',
  'Old Gap': 'sand', 'Basin': 'sand',
  'Gara Kulon': 'sand', 'Red Chasm': 'sand',
  'The Minor Erg': 'sand', 'Cielago South': 'sand', 'Cielago Depression': 'sand',
  'Meridian': 'sand', 'Habbanya Ridge Flat': 'sand', 'Habbanya Erg': 'sand',
  'The Greater Flat': 'sand', 'The Great Flat': 'sand', 'Funeral Plain': 'sand',
}

const SPICE_DATA = {
  'Cielago South': 12, 'Red Chasm': 8, 'The Minor Erg': 6,
  'Habbanya Erg': 8, 'Funeral Plain': 6, 'The Great Flat': 10,
  'Hagga Basin': 6, 'Wind Pass North': 6, 'Broken Land': 8,
  'Old Gap': 6, 'Sihaya Ridge': 6, 'Habbanya Ridge Flat': 10,
  'Meridian': 6, 'Gara Kulon': 6,
}

const SECTORS = {
  'Polar Sink': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17],
  // Outer band
  'Old Gap': [17,0,1], 'Basin': [1,2], 'Gara Kulon': [3,4], 'Red Chasm': [4,5],
  'The Minor Erg': [6,7], 'Cielago South': [9,10],
  'Meridian': [11,12], 'Habbanya Ridge Flat': [12,13], 'Habbanya Erg': [13,14],
  'The Greater Flat': [14,15], 'The Great Flat': [15,16], 'Funeral Plain': [16,17],
  // Inner band (touching polar sink)
  'Imperial Basin': [0,1,2], 'Arrakeen': [1,2], 'Carthag': [17],
  'Hole in the Rock': [3,4], 'Harg Pass': [4,5,6], "Tuek's Sietch": [6,7],
  'Cielago North': [9,10], 'Habbanya Sietch': [10,11],
  'Arsunt': [12,13], 'Wind Pass': [15], 'Wind Pass North': [16],
  // Middle band
  'Broken Land': [17,0,1], 'Tsimpo': [17], 'Plastic Basin': [15,16],
  'Bight of the Cliff': [14,15], 'Sietch Tabr': [13,14],
  'Rim Wall West': [1,2], 'Sihaya Ridge': [3], 'Shield Wall': [4],
  'Pasty Mesa': [5], 'False Wall East': [6], 'South Mesa': [7],
  'False Wall South': [8], 'Cielago East': [8,9], 'Cielago Depression': [8,9],
  'Cielago West': [9,10], 'False Wall West': [10,11],
  'Hagga Basin': [12,13],
}

function buildTerritories() {
  const t = {}
  for (const [name, type] of Object.entries(TERRITORY_TYPES)) {
    t[name] = {
      territory_type: type,
      sectors: SECTORS[name] || [],
      has_spice_blow: !!SPICE_DATA[name],
      spice_blow_amount: SPICE_DATA[name] || 0,
      current_spice: 0,
      storm_exception: name === 'Imperial Basin',
    }
  }
  return t
}

export default function BoardTest() {
  const territories = buildTerritories()
  return (
    <div style={{ width: '90vmin', height: '90vmin', margin: '2vmin auto' }}>
      <GameBoard
        territories={territories}
        players={[]}
        stormSector={2}
        highlightFrom=""
        highlightTo=""
        adjacentTo={[]}
      />
    </div>
  )
}
