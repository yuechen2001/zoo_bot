import Phaser from 'phaser'
import { api } from '../api.js'
import HUD from './HUD.js'

export default class AchievementsScene extends Phaser.Scene {
  constructor() { super('Achievements') }

  async create() {
    this.hud = new HUD(this)
    this._data = null
    this._objs = []
    this._scrollY = 0
    try {
      this._data = await api.getAchievements()
    } catch (_) {}
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    const { width, height } = this.scale

    const back = this.add.text(12, 52, '← Quests', {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setDepth(1).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Quests'))
    this._objs.push(back)

    if (!this._data) {
      const t = this.add.text(width / 2, height / 2, 'Loading...', {
        fontFamily: 'monospace', fontSize: '14px', color: '#aaaaaa',
      }).setOrigin(0.5)
      this._objs.push(t)
      return
    }

    const all = this._data.all
    const total = Object.keys(all).length
    const earned = Object.values(all).filter(a => a.earned).length

    const title = this.add.text(width / 2, 52, `🏆 ${earned} / ${total}`, {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffd700',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(title)

    // Scrollable container
    if (this._container) this._container.destroy()
    this._container = this.add.container(0, 0)
    this._objs.push(this._container)

    let y = 78
    for (const [, ach] of Object.entries(all)) {
      const rowH = 52
      const bg = this.add.rectangle(8, y, width - 16, rowH, ach.earned ? 0x1a3a1a : 0x1a1a2a).setOrigin(0, 0)
      const nameColor = ach.earned ? '#ffffff' : '#555555'
      const icon = ach.earned ? ach.emoji : '🔒'
      const nameTxt = this.add.text(16, y + 8, `${icon}  ${ach.name}`, {
        fontFamily: 'monospace', fontSize: '12px', color: nameColor,
      })
      const descTxt = this.add.text(16, y + 28, ach.desc.slice(0, 55) + (ach.desc.length > 55 ? '…' : ''), {
        fontFamily: 'monospace', fontSize: '9px', color: ach.earned ? '#88bb88' : '#444444',
      })
      this._container.add([bg, nameTxt, descTxt])
      y += rowH + 4
    }

    // Drag-to-scroll
    const contentH = y - 78
    const usableH = height - 68 - 56
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
