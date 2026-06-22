import Phaser from 'phaser'
import { api } from '../api.js'
import HUD from './HUD.js'

const RARITY_COLORS = { common: '#888888', rare: '#4488ff', epic: '#aa44ff', legendary: '#ffaa00' }
const HABITAT_EMOJIS = {
  woodland: '🌲', savanna: '🌾', tropical: '🌴', aquatic: '🐠',
  tundra: '❄️', desert: '🏜️', mythic: '✨', spectral: '👻',
}

export default class DirectoryScene extends Phaser.Scene {
  constructor() { super('Directory') }

  async create() {
    this.hud = new HUD(this)
    this._data = null
    this._objs = []
    this._container = null
    this._activeHabitat = null
    try {
      this._data = await api.getDirectory()
      if (this._data.habitats.length) {
        this._activeHabitat = this._data.habitats[0].habitat
      }
    } catch (_) {}
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() {
    this._objs.forEach(o => o.destroy())
    this._objs = []
    if (this._container) { this._container.destroy(); this._container = null }
  }

  _render() {
    this._clear()
    const { width, height } = this.scale

    const back = this.add.text(12, 52, '← Zoo', {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setDepth(1).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Zoo'))
    this._objs.push(back)

    if (!this._data) {
      const t = this.add.text(width / 2, height / 2, 'Loading...', {
        fontFamily: 'monospace', fontSize: '14px', color: '#aaaaaa',
      }).setOrigin(0.5)
      this._objs.push(t)
      return
    }

    const { total, discovered, habitats } = this._data

    const title = this.add.text(width / 2, 52, `📖 ${discovered} / ${total} discovered`, {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffd700',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(title)

    // Habitat tab strip
    const tabY = 74
    const tabW = Math.min(56, (width - 8) / habitats.length)
    habitats.forEach(({ habitat }, i) => {
      const tx = 4 + i * tabW + tabW / 2
      const isActive = habitat === this._activeHabitat
      const tabBg = this.add.rectangle(4 + i * tabW, tabY, tabW - 2, 22, isActive ? 0x1a3a5a : 0x111111).setOrigin(0, 0).setDepth(1)
      const emoji = HABITAT_EMOJIS[habitat] || '🌍'
      const tabTxt = this.add.text(tx, tabY + 11, emoji, {
        fontSize: '13px',
      }).setOrigin(0.5).setDepth(2).setInteractive({ useHandCursor: true })
      tabTxt.on('pointerdown', () => {
        this._activeHabitat = habitat
        this._render()
      })
      this._objs.push(tabBg, tabTxt)
    })

    // Species list for active habitat
    const activeData = habitats.find(h => h.habitat === this._activeHabitat)
    if (!activeData) return

    this._container = this.add.container(0, 0)
    this._objs.push(this._container)

    const TOP = 102
    const ROW_H = 40
    let y = TOP

    activeData.species.forEach((s) => {
      const rowBg = this.add.rectangle(8, y, width - 16, ROW_H - 2, s.owned ? 0x0a1a0a : 0x0a0a0a).setOrigin(0, 0)
      const emojiTxt = this.add.text(16, y + ROW_H / 2, s.owned ? s.emoji : '❓', {
        fontSize: '18px',
      }).setOrigin(0, 0.5)
      const nameTxt = this.add.text(44, y + 8, s.owned ? s.name : '???', {
        fontFamily: 'monospace', fontSize: '12px', color: s.owned ? '#ffffff' : '#333333',
      })
      const rarityTxt = this.add.text(44, y + 23, s.rarity.toUpperCase(), {
        fontFamily: 'monospace', fontSize: '9px', color: s.owned ? (RARITY_COLORS[s.rarity] || '#888888') : '#222222',
      })
      const ownedDot = s.owned
        ? this.add.text(width - 16, y + ROW_H / 2, '✓', {
          fontFamily: 'monospace', fontSize: '12px', color: '#44cc44',
        }).setOrigin(1, 0.5)
        : null

      this._container.add([rowBg, emojiTxt, nameTxt, rarityTxt])
      if (ownedDot) this._container.add(ownedDot)
      y += ROW_H
    })

    // Drag-to-scroll
    const contentH = y - TOP
    const usableH = height - TOP - 56
    if (contentH > usableH) {
      this.input.on('pointermove', (p) => {
        if (p.isDown) {
          this._container.y = Phaser.Math.Clamp(
            this._container.y + p.velocity.y * 0.3,
            -(contentH - usableH),
            0,
          )
        }
      })
    }
  }
}
