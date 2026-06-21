import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

export default class BreedScene extends Phaser.Scene {
  constructor() { super('Breed') }

  create() {
    this.hud = new HUD(this)
    this._parentA = null
    this._parentB = null
    this._objs = []
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  async _render() {
    this._clear()
    const { width, height } = this.scale

    // Check active breed first
    try {
      const breed = await api.getBreed()
      if (breed.active) {
        this._renderBreedStatus(breed)
        return
      }
    } catch (_) {}

    this._renderPicker()
  }

  _renderBreedStatus(breed) {
    const { width, height } = this.scale
    const cy = height / 2

    const title = this.add.text(width / 2, 82, '🔬 BREEDING IN PROGRESS', {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffd700',
    }).setOrigin(0.5)

    const parents = this.add.text(width / 2, cy - 40,
      `${breed.emoji_a} ${breed.name_a}  ×  ${breed.emoji_b} ${breed.name_b}`, {
      fontFamily: 'monospace', fontSize: '16px', color: '#ffffff',
    }).setOrigin(0.5)

    const readyAt = new Date(breed.ready_at)
    const now = new Date()
    const minsLeft = Math.max(0, Math.round((readyAt - now) / 60000))
    const timeLabel = this.add.text(width / 2, cy,
      breed.is_ready ? '✅ READY TO COLLECT!' : `⏳ ${minsLeft}m remaining`, {
      fontFamily: 'monospace', fontSize: '14px',
      color: breed.is_ready ? '#44ff44' : '#aaaaaa',
    }).setOrigin(0.5)

    if (breed.is_ready) {
      const collectBtn = this.add.rectangle(width / 2, cy + 50, 180, 36, 0x1a4a1a).setInteractive({ useHandCursor: true })
      const collectLabel = this.add.text(width / 2, cy + 50, '🐣 Collect Offspring', {
        fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
      }).setOrigin(0.5)
      collectBtn.on('pointerdown', () => this._collectBreed())
      this._objs.push(collectBtn, collectLabel)
    }

    this._objs.push(title, parents, timeLabel)
  }

  _renderPicker() {
    const { width, height } = this.scale
    const breedable = GameState.animals.filter(a => !a.is_breeding)

    const title = this.add.text(width / 2, 82, this._parentA ? 'SELECT PARENT B' : 'SELECT PARENT A', {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffd700',
    }).setOrigin(0.5)
    this._objs.push(title)

    if (this._parentA) {
      const aLabel = this.add.text(width / 2, 106,
        `A: ${this._parentA.emoji || ''} ${this._parentA.nickname || this._parentA.species_name}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#88ff88',
      }).setOrigin(0.5)
      this._objs.push(aLabel)
    }

    const listY = this._parentA ? 128 : 108
    const itemH = 40
    breedable.forEach((animal, i) => {
      if (this._parentA && animal.animal_id === this._parentA.animal_id) return
      const y = listY + i * itemH
      if (y > height - 60) return

      const bg = this.add.rectangle(8, y, width - 16, 34, 0x1a2a3a).setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const label = this.add.text(16, y + 17,
        `${animal.emoji || '?'} ${animal.nickname || animal.species_name} — ${animal.rarity} — 🍖${animal.hunger}`, {
        fontFamily: 'monospace', fontSize: '11px', color: '#cccccc',
      }).setOrigin(0, 0.5)

      bg.on('pointerover', () => bg.setFillStyle(0x2a4a6a))
      bg.on('pointerout', () => bg.setFillStyle(0x1a2a3a))
      bg.on('pointerdown', () => {
        if (!this._parentA) {
          this._parentA = animal
          this._render()
        } else {
          this._parentB = animal
          this._startBreed()
        }
      })
      this._objs.push(bg, label)
    })

    if (this._parentA) {
      const cancelBtn = this.add.text(width - 10, 82, '✕ Reset', {
        fontFamily: 'monospace', fontSize: '11px', color: '#ff6666',
      }).setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
      cancelBtn.on('pointerdown', () => { this._parentA = null; this._parentB = null; this._render() })
      this._objs.push(cancelBtn)
    }
  }

  async _startBreed() {
    try {
      await api.startBreed(this._parentA.animal_id, this._parentB.animal_id)
      const [user, animals] = await Promise.all([api.getMe(), api.getAnimals()])
      GameState.setUser(user)
      GameState.setAnimals(animals)
      this._parentA = null
      this._parentB = null
      this.hud.update()
      this._render()
    } catch (err) {
      this._showToast(err.message)
      this._parentA = null
      this._parentB = null
      this._render()
    }
  }

  async _collectBreed() {
    try {
      const result = await api.collectBreed()
      const [user, animals] = await Promise.all([api.getMe(), api.getAnimals()])
      GameState.setUser(user)
      GameState.setAnimals(animals)
      this.hud.update()
      this._render()
      this._showToast(`🎉 Got ${result.emoji} ${result.species_name}!`)
    } catch (err) {
      this._showToast(err.message)
    }
  }

  _showToast(msg) {
    const { width, height } = this.scale
    const t = this.add.text(width / 2, height - 70, msg, {
      fontFamily: 'monospace', fontSize: '12px', color: '#ff6666',
      backgroundColor: '#000000cc', padding: { x: 8, y: 4 },
    }).setOrigin(0.5).setDepth(200)
    this.time.delayedCall(2500, () => t.destroy())
  }
}
