import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

const TABS = ['Items', 'Lures', 'Titles']

export default class InventoryScene extends Phaser.Scene {
  constructor() { super('Inventory') }

  async create() {
    this.hud = new HUD(this)
    this._tab = 0
    this._meta = {}   // key → { name, emoji, desc } from store
    this._objs = []
    try {
      const storeItems = await api.getStore()
      for (const item of storeItems) this._meta[item.key] = item
    } catch (_) {}
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    const { width } = this.scale
    const inv = GameState.inventory

    // Back button
    const back = this.add.text(12, 52, '← Store', {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setDepth(1).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Store'))
    this._objs.push(back)

    // Title
    const title = this.add.text(width / 2, 52, '🎒 INVENTORY', {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffd700',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(title)

    // Tabs
    const tabW = width / TABS.length
    TABS.forEach((tab, i) => {
      const bg = this.add.rectangle(i * tabW, 68, tabW, 26, i === this._tab ? 0x2a4a6a : 0x1a2a3a)
        .setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
      const label = this.add.text(i * tabW + tabW / 2, 81, tab, {
        fontFamily: 'monospace', fontSize: '11px', color: i === this._tab ? '#ffd700' : '#888888',
      }).setOrigin(0.5).setDepth(2)
      bg.on('pointerdown', () => { this._tab = i; this._render() })
      this._objs.push(bg, label)
    })

    if (this._tab === 0) this._renderItems(inv)
    else if (this._tab === 1) this._renderLures(inv)
    else this._renderTitles(inv)
  }

  _renderItems(inv) {
    const { width } = this.scale
    const consumables = inv?.consumables || {}
    const entries = Object.entries(consumables).filter(([, qty]) => qty > 0)
    let y = 102

    if (entries.length === 0) {
      this.add.text(width / 2, 200, 'No items in inventory', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      return
    }

    for (const [key, qty] of entries) {
      const m = this._meta[key] || {}
      const row = this.add.rectangle(8, y, width - 16, 54, 0x1a2a3a).setOrigin(0, 0).setDepth(1)
      const nameTxt = this.add.text(16, y + 8, `${m.emoji || '📦'} ${m.name || key}  ×${qty}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
      }).setDepth(2)
      const descTxt = this.add.text(16, y + 30, (m.desc || '').slice(0, 52) + ((m.desc || '').length > 52 ? '…' : ''), {
        fontFamily: 'monospace', fontSize: '9px', color: '#888888',
      }).setDepth(2)

      const btn = this.add.rectangle(width - 14, y + 27, 70, 24, 0x1a4a6a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(width - 14, y + 27, 'USE', {
        fontFamily: 'monospace', fontSize: '11px', color: '#aaddff',
      }).setOrigin(1, 0.5).setDepth(2)
      const k = key
      btn.on('pointerdown', () => this._useItem(k))
      btn.on('pointerover', () => btn.setFillStyle(0x2a6a9a))
      btn.on('pointerout', () => btn.setFillStyle(0x1a4a6a))

      this._objs.push(row, nameTxt, descTxt, btn, btnLabel)
      y += 62
    }
  }

  _renderLures(inv) {
    const { width } = this.scale
    const lures = inv?.lures || {}
    const entries = Object.entries(lures).filter(([, qty]) => qty > 0)
    let y = 102

    if (entries.length === 0) {
      this.add.text(width / 2, 200, 'No lures in inventory', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      return
    }

    const note = this.add.text(width / 2, y, 'Use lures from the CATCH screen', {
      fontFamily: 'monospace', fontSize: '10px', color: '#555555',
    }).setOrigin(0.5)
    this._objs.push(note)
    y += 18

    for (const [key, qty] of entries) {
      const m = this._meta[key] || {}
      const row = this.add.rectangle(8, y, width - 16, 44, 0x1a2a3a).setOrigin(0, 0).setDepth(1)
      const nameTxt = this.add.text(16, y + 10, `${m.emoji || '🎣'} ${m.name || key}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
      }).setDepth(2)
      const qtyTxt = this.add.text(width - 14, y + 22, `×${qty}`, {
        fontFamily: 'monospace', fontSize: '13px', color: '#ffd700',
      }).setOrigin(1, 0.5).setDepth(2)

      this._objs.push(row, nameTxt, qtyTxt)
      y += 52
    }
  }

  _renderTitles(inv) {
    const { width } = this.scale
    const owned = inv?.titles_owned || []
    const activeTitle = inv?.active_title || null
    let y = 102

    if (owned.length === 0) {
      this.add.text(width / 2, 200, 'No titles owned', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      return
    }

    for (const key of owned) {
      const m = this._meta[key] || {}
      const isActive = key === activeTitle
      const row = this.add.rectangle(8, y, width - 16, 44, isActive ? 0x1a3a1a : 0x1a2a3a).setOrigin(0, 0).setDepth(1)
      const nameTxt = this.add.text(16, y + 12, `${m.emoji || '🎖'} ${m.name || key}${isActive ? '  ✓' : ''}`, {
        fontFamily: 'monospace', fontSize: '12px', color: isActive ? '#44ff44' : '#ffffff',
      }).setDepth(2)

      const btnColor = isActive ? 0x3a1a1a : 0x1a4a1a
      const btnText = isActive ? 'UNEQUIP' : 'EQUIP'
      const btn = this.add.rectangle(width - 14, y + 22, 80, 24, btnColor).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(width - 14, y + 22, btnText, {
        fontFamily: 'monospace', fontSize: '10px', color: '#ffffff',
      }).setOrigin(1, 0.5).setDepth(2)
      const k = key
      if (isActive) {
        btn.on('pointerdown', () => this._unequipTitle())
        btn.on('pointerover', () => btn.setFillStyle(0x5a2a2a))
        btn.on('pointerout', () => btn.setFillStyle(0x3a1a1a))
      } else {
        btn.on('pointerdown', () => this._equipTitle(k))
        btn.on('pointerover', () => btn.setFillStyle(0x2a6a2a))
        btn.on('pointerout', () => btn.setFillStyle(0x1a4a1a))
      }

      this._objs.push(row, nameTxt, btn, btnLabel)
      y += 52
    }
  }

  async _useItem(key) {
    try {
      await api.useItem(key)
      const [user, inv] = await Promise.all([api.getMe(), api.getInventory()])
      GameState.setUser(user)
      GameState.setInventory(inv)
      this.hud.update()
      const m = this._meta[key] || {}
      this._showToast(`✅ ${m.emoji || ''} ${m.name || key} activated!`)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _equipTitle(key) {
    try {
      await api.equipTitle(key)
      const inv = await api.getInventory()
      GameState.setInventory(inv)
      const m = this._meta[key] || {}
      this._showToast(`🎖 Equipped: ${m.name || key}`)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _unequipTitle() {
    try {
      await api.unequipTitle()
      const inv = await api.getInventory()
      GameState.setInventory(inv)
      this._showToast('Title unequipped')
      this._render()
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
