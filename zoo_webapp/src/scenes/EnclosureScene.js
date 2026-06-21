import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

export default class EnclosureScene extends Phaser.Scene {
  constructor() { super('Enclosures') }

  async create() {
    this.hud = new HUD(this)
    this._objs = []
    await this._refresh()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  async _refresh() {
    try {
      const enc = await api.getEnclosures()
      GameState.setEnclosures(enc)
    } catch (_) {}
    this._render()
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    const { width } = this.scale
    const enc = GameState.enclosures

    const title = this.add.text(width / 2, 78, '🏠 ENCLOSURES', {
      fontFamily: 'monospace', fontSize: '16px', color: '#ffd700',
    }).setOrigin(0.5)
    this._objs.push(title)

    // Collect all button
    const collectBtn = this.add.rectangle(width - 10, 78, 110, 24, 0x1a4a1a).setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
    const collectLabel = this.add.text(width - 10, 78, '💰 Collect All', {
      fontFamily: 'monospace', fontSize: '10px', color: '#ffffff',
    }).setOrigin(1, 0.5)
    collectBtn.on('pointerdown', () => this._collectAll())
    this._objs.push(collectBtn, collectLabel)

    let y = 102
    for (const [habitat, data] of Object.entries(enc)) {
      const row = this.add.rectangle(8, y, width - 16, 52, 0x1a2a3a).setOrigin(0, 0)
      const name = this.add.text(16, y + 8, `${data.emoji} ${data.name}  Lv${data.level}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
      })
      const info = this.add.text(16, y + 28,
        `${data.animals_used}/${data.capacity} animals  •  ${data.coins_per_animal_hr} 🪙/hr/animal`, {
        fontFamily: 'monospace', fontSize: '10px', color: '#aaaaaa',
      })

      // Upgrade button (if not max)
      if (data.upgrade_cost !== null) {
        const upBtn = this.add.rectangle(width - 14, y + 26, 100, 24, 0x2a4a2a).setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
        const upLabel = this.add.text(width - 14, y + 26, `⬆ ${data.upgrade_cost}🪙`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#ffffff',
        }).setOrigin(1, 0.5)
        const h = habitat
        upBtn.on('pointerdown', () => this._upgrade(h))
        this._objs.push(upBtn, upLabel)
      } else {
        const maxLabel = this.add.text(width - 14, y + 26, 'MAX', {
          fontFamily: 'monospace', fontSize: '10px', color: '#ffd700',
        }).setOrigin(1, 0.5)
        this._objs.push(maxLabel)
      }

      this._objs.push(row, name, info)
      y += 60
    }
  }

  async _upgrade(habitat) {
    try {
      await api.upgradeEnclosure(habitat)
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      await this._refresh()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _collectAll() {
    try {
      const res = await api.collectEnclosure()
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._showToast(`Collected ${res.coins_collected} 🪙`)
    } catch (err) {
      this._showToast(err.message)
    }
  }

  _showToast(msg) {
    const { width, height } = this.scale
    const t = this.add.text(width / 2, height - 70, msg, {
      fontFamily: 'monospace', fontSize: '12px', color: '#88ff88',
      backgroundColor: '#000000cc', padding: { x: 8, y: 4 },
    }).setOrigin(0.5).setDepth(200)
    this.time.delayedCall(2500, () => t.destroy())
  }
}
