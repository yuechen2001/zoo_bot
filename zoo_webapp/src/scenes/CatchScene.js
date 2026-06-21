import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

const LURES = [
  { key: 'lure_woodland', label: '🌲 Woodland' },
  { key: 'lure_savanna', label: '🌾 Savanna' },
  { key: 'lure_tropical', label: '🌴 Tropical' },
  { key: 'lure_aquatic', label: '🐠 Aquatic' },
  { key: 'lure_tundra', label: '❄️ Tundra' },
  { key: 'lure_desert', label: '🏜️ Desert' },
  { key: 'lure_spectral', label: '👻 Spectral' },
  { key: 'lure_mythic', label: '✨ Mythic' },
]
const RARITY_COLORS = { common: '#888888', rare: '#4488ff', epic: '#aa44ff', legendary: '#ffaa00' }

export default class CatchScene extends Phaser.Scene {
  constructor() { super('Catch') }

  create() {
    this.hud = new HUD(this)
    this._state = 'select'   // select → searching → result
    this._selectedLure = null
    this._objs = []
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    if (this._state === 'select') this._renderSelect()
    else if (this._state === 'searching') this._renderSearching()
    else if (this._state === 'result') this._renderResult()
  }

  _renderSelect() {
    const { width, height } = this.scale
    const title = this.add.text(width / 2, 78, 'SELECT A LURE', {
      fontFamily: 'monospace', fontSize: '16px', color: '#ffd700',
    }).setOrigin(0.5, 0)
    this._objs.push(title)

    // Fetch inventory to show quantities
    const inventory = GameState.user ? {} : {}

    const btnW = (width - 24) / 2
    LURES.forEach((lure, i) => {
      const col = i % 2
      const row = Math.floor(i / 2)
      const x = 8 + col * (btnW + 8)
      const y = 108 + row * 44

      const bg = this.add.rectangle(x, y, btnW, 36, 0x1a3a5a).setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const label = this.add.text(x + btnW / 2, y + 18, lure.label, {
        fontFamily: 'monospace', fontSize: '12px', color: '#cccccc',
      }).setOrigin(0.5)
      bg.on('pointerdown', () => { this._selectedLure = lure.key; this._doSearch() })
      bg.on('pointerover', () => bg.setFillStyle(0x2a5a8a))
      bg.on('pointerout', () => bg.setFillStyle(0x1a3a5a))
      this._objs.push(bg, label)
    })

    // No lure option
    const noLureY = 108 + Math.ceil(LURES.length / 2) * 44 + 8
    const noBg = this.add.rectangle(8, noLureY, width - 16, 36, 0x2a2a2a).setOrigin(0, 0).setInteractive({ useHandCursor: true })
    const noLabel = this.add.text(width / 2, noLureY + 18, '🔍 Search without lure (10 🪙)', {
      fontFamily: 'monospace', fontSize: '12px', color: '#888888',
    }).setOrigin(0.5)
    noBg.on('pointerdown', () => { this._selectedLure = null; this._doSearch() })
    this._objs.push(noBg, noLabel)
  }

  _renderSearching() {
    const { width, height } = this.scale
    const t = this.add.text(width / 2, height / 2, '🔍 Searching...', {
      fontFamily: 'monospace', fontSize: '20px', color: '#ffffff',
    }).setOrigin(0.5)
    this._objs.push(t)
    // Spinning animation
    this.tweens.add({ targets: t, angle: 5, duration: 200, yoyo: true, repeat: -1 })
  }

  _renderResult() {
    const r = this._result
    const { width, height } = this.scale
    const cy = height / 2

    if (!r.caught) {
      const msg = this.add.text(width / 2, cy - 30, `${r.species?.emoji || '?'} ${r.species?.name || ''}`, {
        fontFamily: 'monospace', fontSize: '32px',
      }).setOrigin(0.5)
      const sub = this.add.text(width / 2, cy + 20, '❌ It got away!', {
        fontFamily: 'monospace', fontSize: '16px', color: '#ff6666',
      }).setOrigin(0.5)
      this._objs.push(msg, sub)
    } else {
      const rarityColor = RARITY_COLORS[r.rarity] || '#ffffff'
      const emoji = this.add.text(width / 2, cy - 50, r.species?.emoji || '🐾', {
        fontSize: '48px',
      }).setOrigin(0.5)
      this.tweens.add({ targets: emoji, scale: 1.2, duration: 400, yoyo: true, repeat: 3 })

      const name = this.add.text(width / 2, cy + 10, r.species?.name || 'Unknown', {
        fontFamily: 'monospace', fontSize: '18px', color: '#ffffff',
      }).setOrigin(0.5)
      const rLabel = this.add.text(width / 2, cy + 32, r.rarity?.toUpperCase() || '', {
        fontFamily: 'monospace', fontSize: '14px', color: rarityColor,
      }).setOrigin(0.5)
      const caught = this.add.text(width / 2, cy + 54, r.is_shiny ? '✅ Caught! ⭐ SHINY!' : '✅ Caught!', {
        fontFamily: 'monospace', fontSize: '14px', color: '#44ff44',
      }).setOrigin(0.5)
      this._objs.push(emoji, name, rLabel, caught)
    }

    // Again / Back buttons
    const again = this.add.rectangle(width / 2 - 70, cy + 95, 120, 34, 0x1a4a1a).setInteractive({ useHandCursor: true })
    const againLabel = this.add.text(width / 2 - 70, cy + 95, '🔄 Again', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setOrigin(0.5)
    again.on('pointerdown', () => { this._state = 'select'; this._render() })

    const back = this.add.rectangle(width / 2 + 70, cy + 95, 120, 34, 0x4a1a1a).setInteractive({ useHandCursor: true })
    const backLabel = this.add.text(width / 2 + 70, cy + 95, '← Zoo', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setOrigin(0.5)
    back.on('pointerdown', () => this.scene.start('Zoo'))

    this._objs.push(again, againLabel, back, backLabel)
  }

  async _doSearch() {
    this._state = 'searching'
    this._render()
    try {
      const result = await api.startCatch(this._selectedLure)
      this._result = result
      if (result.caught) {
        const [updatedUser, updatedAnimals] = await Promise.all([api.getMe(), api.getAnimals()])
        GameState.setUser(updatedUser)
        GameState.setAnimals(updatedAnimals)
        this.hud.update()
      } else {
        const updatedUser = await api.getMe()
        GameState.setUser(updatedUser)
        this.hud.update()
      }
      this._state = 'result'
      this._render()
    } catch (err) {
      this._state = 'select'
      this._render()
      const { width, height } = this.scale
      const t = this.add.text(width / 2, height - 70, err.message, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ff6666',
        backgroundColor: '#000000cc', padding: { x: 8, y: 4 },
      }).setOrigin(0.5).setDepth(200)
      this.time.delayedCall(2500, () => t.destroy())
    }
  }
}
