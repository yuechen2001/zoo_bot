import Phaser from 'phaser'
import HUD from './HUD.js'

const RARITY_COLORS = { common: '#888888', rare: '#4488ff', epic: '#aa44ff', legendary: '#ffaa00' }

function stars(stat) {
  const filled = Math.min(5, Math.max(1, Math.round((stat + 10) / 20)))
  return '★'.repeat(filled) + '☆'.repeat(5 - filled)
}

export default class InspectScene extends Phaser.Scene {
  constructor() { super('Inspect') }

  init(data) {
    this._animal = data.animal || null
  }

  create() {
    this.hud = new HUD(this)
    this._objs = []
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    const { width, height } = this.scale
    const animal = this._animal

    const back = this.add.text(12, 52, '← Zoo', {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setDepth(1).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Zoo'))
    this._objs.push(back)

    if (!animal) {
      const t = this.add.text(width / 2, height / 2, 'No animal data.', {
        fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
      }).setOrigin(0.5)
      this._objs.push(t)
      return
    }

    const name = animal.nickname || animal.species_name || '?'
    const rarity = animal.rarity || 'common'
    const rarityColor = RARITY_COLORS[rarity] || '#ffffff'

    let y = 72

    // Header
    const headerTxt = this.add.text(width / 2, y, `${animal.emoji || '🐾'}  ${name}`, {
      fontFamily: 'monospace', fontSize: '16px', color: '#ffffff',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(headerTxt)
    y += 24

    const rarityTxt = this.add.text(width / 2, y, rarity.toUpperCase() + (animal.is_shiny ? '  ⭐ SHINY' : ''), {
      fontFamily: 'monospace', fontSize: '11px', color: rarityColor,
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(rarityTxt)
    y += 20

    const habitatTxt = this.add.text(width / 2, y, `Habitat: ${animal.habitat || '—'}`, {
      fontFamily: 'monospace', fontSize: '10px', color: '#666666',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(habitatTxt)
    y += 28

    // Hunger bar
    const hungerBg = this.add.rectangle(20, y, width - 40, 14, 0x222222).setOrigin(0, 0).setDepth(1)
    const hungerFill = this.add.rectangle(20, y, Math.round((width - 40) * (animal.hunger / 100)), 14,
      animal.hunger > 50 ? 0x44cc44 : animal.hunger > 20 ? 0xffaa00 : 0xff3333
    ).setOrigin(0, 0).setDepth(2)
    const hungerTxt = this.add.text(width / 2, y + 7, `Hunger ${animal.hunger}/100`, {
      fontFamily: 'monospace', fontSize: '9px', color: '#ffffff',
    }).setOrigin(0.5, 0.5).setDepth(3)
    this._objs.push(hungerBg, hungerFill, hungerTxt)
    y += 28

    // Stats
    const statRows = [
      { icon: '⚡', label: 'Speed', val: animal.stat_speed ?? 50, desc: 'faster breeding' },
      { icon: '🌟', label: 'Genetics', val: animal.stat_rarity ?? 50, desc: 'rarer offspring' },
      { icon: '🍖', label: 'Temperament', val: animal.stat_temperament ?? 50, desc: 'more income' },
    ]

    const cardX = 16
    const cardW = width - 32
    statRows.forEach(({ icon, label, val, desc }) => {
      const cardBg = this.add.rectangle(cardX, y, cardW, 38, 0x111a28).setOrigin(0, 0).setDepth(1)
      const iconTxt = this.add.text(cardX + 8, y + 10, icon, { fontSize: '14px' }).setDepth(2)
      const labelTxt = this.add.text(cardX + 28, y + 6, label, {
        fontFamily: 'monospace', fontSize: '11px', color: '#cccccc',
      }).setDepth(2)
      const starTxt = this.add.text(cardX + 28, y + 20, stars(val), {
        fontFamily: 'monospace', fontSize: '11px', color: '#ffd700',
      }).setDepth(2)
      const descTxt = this.add.text(cardX + cardW - 8, y + 19, desc, {
        fontFamily: 'monospace', fontSize: '9px', color: '#555555',
      }).setOrigin(1, 0).setDepth(2)
      this._objs.push(cardBg, iconTxt, labelTxt, starTxt, descTxt)
      y += 44
    })

    y += 8

    // Badges row
    const badges = []
    if (animal.is_breeding) badges.push('🔒 Breeding')
    if (animal.is_shiny) badges.push('⭐ Shiny')
    if (badges.length) {
      const badgeTxt = this.add.text(width / 2, y, badges.join('  '), {
        fontFamily: 'monospace', fontSize: '11px', color: '#aaddff',
      }).setOrigin(0.5, 0).setDepth(1)
      this._objs.push(badgeTxt)
      y += 20
    }

    // Caught at
    if (animal.caught_at) {
      const dateTxt = this.add.text(width / 2, y, `Caught: ${animal.caught_at.slice(0, 10)}`, {
        fontFamily: 'monospace', fontSize: '10px', color: '#555555',
      }).setOrigin(0.5, 0).setDepth(1)
      this._objs.push(dateTxt)
      y += 18
    }

    // Sell value estimate
    const sellVal = Math.max(1, Math.round((animal.catch_cost || 10) / 2 * (animal.hunger / 100)))
    const sellTxt = this.add.text(width / 2, y, `Sell value: ~${sellVal} 🪙`, {
      fontFamily: 'monospace', fontSize: '10px', color: '#888888',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(sellTxt)
  }
}
