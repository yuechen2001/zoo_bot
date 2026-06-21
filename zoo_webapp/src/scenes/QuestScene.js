import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

export default class QuestScene extends Phaser.Scene {
  constructor() { super('Quests') }

  async create() {
    this.hud = new HUD(this)
    this._data = null
    this._selectedArc = null
    this._objs = []
    try {
      this._data = await api.getQuests()
    } catch (_) {}
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    if (!this._data) {
      const t = this.add.text(this.scale.width / 2, this.scale.height / 2, 'Loading...', {
        fontFamily: 'monospace', fontSize: '14px', color: '#aaaaaa',
      }).setOrigin(0.5)
      this._objs.push(t)
      return
    }

    const { width } = this.scale
    const arcs = this._data.arcs
    const arcKeys = Object.keys(arcs)

    // Arc selector
    const arcW = Math.min(70, (width - 16) / arcKeys.length)
    arcKeys.forEach((num, i) => {
      const isSelected = this._selectedArc === num || (!this._selectedArc && i === 0)
      const x = 8 + i * (arcW + 4)
      const bg = this.add.rectangle(x, 68, arcW, 24, isSelected ? 0x2a4a6a : 0x1a2a3a).setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const label = this.add.text(x + arcW / 2, 80, `Arc ${num}`, {
        fontFamily: 'monospace', fontSize: '9px', color: isSelected ? '#ffd700' : '#888888',
      }).setOrigin(0.5)
      bg.on('pointerdown', () => { this._selectedArc = num; this._render() })
      this._objs.push(bg, label)
    })

    const activeArc = this._selectedArc || arcKeys[0]
    const arcTitle = this.add.text(width / 2, 100, arcs[activeArc] || '', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setOrigin(0.5)
    this._objs.push(arcTitle)

    // Chapters in this arc
    const chapters = this._data.chapters.filter(ch => String(ch.arc) === String(activeArc))
    let y = 122
    chapters.forEach((ch) => {
      const statusIcon = ch.completed ? '✅' : ch.is_active ? '▶' : ch.started ? '⏳' : '🔒'
      const color = ch.completed ? '#44ff44' : ch.is_active ? '#ffd700' : '#555555'

      const row = this.add.rectangle(8, y, width - 16, 36, 0x1a2a3a).setOrigin(0, 0)
      const chTitle = this.add.text(16, y + 18, `${statusIcon} Ch${ch.chapter_num}: ${ch.title}`, {
        fontFamily: 'monospace', fontSize: '11px', color,
      }).setOrigin(0, 0.5)

      // Task progress
      if (ch.is_active && ch.tasks.length > 0) {
        const done = ch.tasks.filter(t => t.done).length
        const prog = this.add.text(width - 16, y + 18, `${done}/${ch.tasks.length}`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#aaaaaa',
        }).setOrigin(1, 0.5)
        this._objs.push(prog)
      }

      if (ch.reward_coins) {
        const reward = this.add.text(width - 16, y + 18, `${ch.reward_coins}🪙`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#ffd700',
        }).setOrigin(1, 0.5)
        this._objs.push(reward)
      }

      this._objs.push(row, chTitle)
      y += 44

      // Show tasks for active chapter
      if (ch.is_active) {
        ch.tasks.forEach((task) => {
          const tRow = this.add.rectangle(16, y, width - 32, 28, 0x111a22).setOrigin(0, 0)
          const tLabel = this.add.text(24, y + 14, `${task.done ? '☑' : '☐'} ${task.desc}`, {
            fontFamily: 'monospace', fontSize: '9px', color: task.done ? '#44ff44' : '#888888',
          }).setOrigin(0, 0.5)
          this._objs.push(tRow, tLabel)
          y += 32
        })
      }
    })
  }
}
