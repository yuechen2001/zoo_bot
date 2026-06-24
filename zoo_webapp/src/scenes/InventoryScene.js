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
    this._meta = {}
    this._objs = []
    this._scrollContainer = null
    this._scrollY = 0
    this._scrollHandler = null
    this._wheelHandler = null
    try {
      const [storeItems, inv] = await Promise.all([api.getStore(), api.getInventory()])
      for (const item of storeItems) this._meta[item.key] = item
      GameState.setInventory(inv)
    } catch (_) {}
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() {
    if (this._scrollHandler) this.input.off('pointermove', this._scrollHandler)
    if (this._wheelHandler) this.input.off('wheel', this._wheelHandler)
    this._scrollHandler = null
    this._wheelHandler = null
    this._objs.forEach(o => o.destroy())
    this._objs = []
    this._scrollContainer = null
  }

  _render() {
    this._clear()
    const { width, height } = this.scale
    const inv = GameState.inventory

    const back = this.add.text(8, 82, '← Store', {
      fontFamily: 'monospace', fontSize: '10px', color: '#888888',
    }).setOrigin(0, 0.5).setDepth(5).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Store'))
    this._objs.push(back)

    const tabW = width / TABS.length
    TABS.forEach((tab, i) => {
      const bg = this.add.rectangle(i * tabW, 68, tabW, 26, i === this._tab ? 0x2a4a6a : 0x1a2a3a)
        .setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
      const label = this.add.text(i * tabW + tabW / 2, 81, tab, {
        fontFamily: 'monospace', fontSize: '11px', color: i === this._tab ? '#ffd700' : '#888888',
      }).setOrigin(0.5).setDepth(2)
      bg.on('pointerdown', () => { this._tab = i; this._scrollY = 0; this._render() })
      this._objs.push(bg, label)
    })

    const TOP = 102
    this._scrollContainer = this.add.container(0, -this._scrollY)
    this._objs.push(this._scrollContainer)

    let finalY
    if (this._tab === 0) finalY = this._renderItems(inv, TOP)
    else if (this._tab === 1) finalY = this._renderLures(inv, TOP)
    else finalY = this._renderTitles(inv, TOP)

    if (finalY !== undefined) {
      this._attachScroll(this._scrollContainer, finalY - TOP, height - TOP - 56)
    }
  }

  _renderItems(inv, TOP) {
    const { width } = this.scale
    const consumables = inv?.consumables || {}
    const entries = Object.entries(consumables).filter(([, qty]) => qty > 0)
    let y = TOP

    if (entries.length === 0) {
      const empty = this.add.text(width / 2, 200, 'No items in inventory', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      this._scrollContainer.add(empty)
      return y + 100
    }

    for (const [key, qty] of entries) {
      const m = this._meta[key] || {}
      const row = this.add.rectangle(8, y, width - 16, 64, 0x1a2a3a).setOrigin(0, 0).setDepth(1)
      const nameTxt = this.add.text(16, y + 8, `${m.emoji || '📦'} ${m.name || key}  ×${qty}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
      }).setDepth(2)
      const descTxt = this.add.text(16, y + 28, m.desc || '', {
        fontFamily: 'monospace', fontSize: '9px', color: '#888888',
        wordWrap: { width: width - 110, useAdvancedWrap: true },
      }).setDepth(2)

      const btn = this.add.rectangle(width - 14, y + 27, 70, 24, 0x1a4a6a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(width - 14, y + 27, 'USE', {
        fontFamily: 'monospace', fontSize: '11px', color: '#aaddff',
      }).setOrigin(1, 0.5).setDepth(2)
      const k = key
      btn.on('pointerdown', () => this._useItem(k))
      btn.on('pointerover', () => btn.setFillStyle(0x2a6a9a))
      btn.on('pointerout', () => btn.setFillStyle(0x1a4a6a))

      this._scrollContainer.add([row, nameTxt, descTxt, btn, btnLabel])
      y += 72
    }
    return y
  }

  _renderLures(inv, TOP) {
    const { width } = this.scale
    const lures = inv?.lures || {}
    const entries = Object.entries(lures).filter(([, qty]) => qty > 0)
    let y = TOP

    if (entries.length === 0) {
      const empty = this.add.text(width / 2, 200, 'No lures in inventory', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      this._scrollContainer.add(empty)
      return y + 100
    }

    const note = this.add.text(width / 2, y, 'Use lures from the CATCH screen', {
      fontFamily: 'monospace', fontSize: '10px', color: '#555555',
    }).setOrigin(0.5)
    this._scrollContainer.add(note)
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

      this._scrollContainer.add([row, nameTxt, qtyTxt])
      y += 52
    }
    return y
  }

  _renderTitles(inv, TOP) {
    const { width } = this.scale
    const owned = inv?.titles_owned || []
    const activeTitle = inv?.active_title || null
    let y = TOP

    if (owned.length === 0) {
      const empty = this.add.text(width / 2, 200, 'No titles owned', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      this._scrollContainer.add(empty)
      return y + 100
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

      this._scrollContainer.add([row, nameTxt, btn, btnLabel])
      y += 52
    }
    return y
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

  _attachScroll(container, contentH, usableH) {
    if (contentH <= usableH) return
    const maxScroll = contentH - usableH
    this._scrollHandler = (p) => {
      if (!p.isDown) return
      const dy = p.prevPosition.y - p.y
      this._scrollY = Phaser.Math.Clamp(this._scrollY + dy, 0, maxScroll)
      container.y = -this._scrollY
    }
    this._wheelHandler = (_, __, ___, dy) => {
      this._scrollY = Phaser.Math.Clamp(this._scrollY + dy * 0.5, 0, maxScroll)
      container.y = -this._scrollY
    }
    this.input.on('pointermove', this._scrollHandler)
    this.input.on('wheel', this._wheelHandler)
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
