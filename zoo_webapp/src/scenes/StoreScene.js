import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

const TABS = ['Items', 'Lures', 'Titles', 'Bag']

export default class StoreScene extends Phaser.Scene {
  constructor() { super('Store') }

  async create() {
    this.hud = new HUD(this)
    this._tab = 0
    this._items = []
    this._inv = null
    this._meta = {}
    this._objs = []
    this._scrollContainer = null
    this._scrollY = 0
    this._scrollHandler = null
    this._wheelHandler = null
    try {
      const [items, inv] = await Promise.all([api.getStore(), api.getInventory()])
      this._items = items
      this._inv = inv
      for (const item of items) this._meta[item.key] = item
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

    const tabW = width / TABS.length
    TABS.forEach((tab, i) => {
      const bg = this.add.rectangle(i * tabW, 68, tabW, 28, i === this._tab ? 0x2a4a6a : 0x1a2a3a)
        .setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const label = this.add.text(i * tabW + tabW / 2, 82, tab, {
        fontFamily: 'monospace', fontSize: '11px', color: i === this._tab ? '#ffd700' : '#888888',
      }).setOrigin(0.5)
      bg.on('pointerdown', () => { this._tab = i; this._scrollY = 0; this._render() })
      this._objs.push(bg, label)
    })

    const TOP = 104
    this._scrollContainer = this.add.container(0, -this._scrollY)
    this._objs.push(this._scrollContainer)

    const finalY = this._tab === 3 ? this._renderBag(TOP) : this._renderStoreTab(TOP)
    this._attachScroll(this._scrollContainer, finalY - TOP, height - TOP - 56)
  }

  _renderStoreTab(TOP) {
    const { width } = this.scale
    const filtered = this._items.filter(item => {
      if (this._tab === 1) return item.key?.startsWith('lure_')
      if (this._tab === 0) return item.category === 'item' && !item.key?.startsWith('lure_')
      return item.category === 'cosmetic'
    })

    let y = TOP
    filtered.forEach((item) => {
      const row = this.add.rectangle(8, y, width - 16, 60, 0x1a2a3a).setOrigin(0, 0)
      const nameLabel = this.add.text(16, y + 8, `${item.emoji} ${item.name}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
      })
      const desc = this.add.text(16, y + 28, item.desc, {
        fontFamily: 'monospace', fontSize: '9px', color: '#888888',
        wordWrap: { width: width - 110, useAdvancedWrap: true },
      })

      const btnLabel = item.owned ? '✓ Owned' : `${item.price} 🪙`
      const btnColor = item.owned ? 0x1a4a1a : 0x2a4a8a
      const buyBtn = this.add.rectangle(width - 14, y + 32, 80, 26, btnColor)
        .setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
      const buyLabel = this.add.text(width - 14, y + 32, btnLabel, {
        fontFamily: 'monospace', fontSize: '10px', color: '#ffffff',
      }).setOrigin(1, 0.5)

      if (!item.owned) {
        const k = item.key
        buyBtn.on('pointerdown', () => this._buy(k))
      }

      const toAdd = [row, nameLabel, desc, buyBtn, buyLabel]
      if (item.quantity !== undefined) {
        const qty = this.add.text(width - 14, y + 8, `×${item.quantity}`, {
          fontFamily: 'monospace', fontSize: '9px', color: '#aaaaaa',
        }).setOrigin(1, 0)
        toAdd.push(qty)
      }

      this._scrollContainer.add(toAdd)
      y += 68
    })
    return y
  }

  _renderBag(TOP) {
    const { width } = this.scale
    const inv = this._inv || {}
    const consumables = inv.consumables || {}
    const lures = inv.lures || {}
    const owned = inv.titles_owned || []
    const activeTitle = inv.active_title || null

    const consumableEntries = Object.entries(consumables).filter(([, qty]) => qty > 0)
    const lureEntries = Object.entries(lures).filter(([, qty]) => qty > 0)

    if (consumableEntries.length === 0 && lureEntries.length === 0 && owned.length === 0) {
      const empty = this.add.text(width / 2, TOP + 80, 'Bag is empty', {
        fontFamily: 'monospace', fontSize: '12px', color: '#555555',
      }).setOrigin(0.5)
      this._scrollContainer.add(empty)
      return TOP + 180
    }

    let y = TOP
    const section = (label) => {
      const t = this.add.text(16, y, label, {
        fontFamily: 'monospace', fontSize: '9px', color: '#555555',
      })
      this._scrollContainer.add(t)
      y += 18
    }

    if (consumableEntries.length > 0) {
      section('ITEMS')
      for (const [key, qty] of consumableEntries) {
        const m = this._meta[key] || {}
        const row = this.add.rectangle(8, y, width - 16, 56, 0x1a2a3a).setOrigin(0, 0)
        const nameTxt = this.add.text(16, y + 8, `${m.emoji || '📦'} ${m.name || key}  ×${qty}`, {
          fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
        })
        const descTxt = this.add.text(16, y + 28, m.desc || '', {
          fontFamily: 'monospace', fontSize: '9px', color: '#888888',
          wordWrap: { width: width - 110, useAdvancedWrap: true },
        })
        const btn = this.add.rectangle(width - 14, y + 28, 70, 24, 0x1a4a6a)
          .setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
        const btnLabel = this.add.text(width - 14, y + 28, 'USE', {
          fontFamily: 'monospace', fontSize: '11px', color: '#aaddff',
        }).setOrigin(1, 0.5)
        const k = key
        btn.on('pointerdown', () => this._useItem(k))
        btn.on('pointerover', () => btn.setFillStyle(0x2a6a9a))
        btn.on('pointerout', () => btn.setFillStyle(0x1a4a6a))
        this._scrollContainer.add([row, nameTxt, descTxt, btn, btnLabel])
        y += 64
      }
    }

    if (lureEntries.length > 0) {
      section('LURES')
      const note = this.add.text(width / 2, y, 'Use lures from the CATCH screen', {
        fontFamily: 'monospace', fontSize: '9px', color: '#444444',
      }).setOrigin(0.5)
      this._scrollContainer.add(note)
      y += 16
      for (const [key, qty] of lureEntries) {
        const m = this._meta[key] || {}
        const row = this.add.rectangle(8, y, width - 16, 40, 0x1a2a3a).setOrigin(0, 0)
        const nameTxt = this.add.text(16, y + 10, `${m.emoji || '🎣'} ${m.name || key}`, {
          fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
        })
        const qtyTxt = this.add.text(width - 14, y + 20, `×${qty}`, {
          fontFamily: 'monospace', fontSize: '13px', color: '#ffd700',
        }).setOrigin(1, 0.5)
        this._scrollContainer.add([row, nameTxt, qtyTxt])
        y += 48
      }
    }

    if (owned.length > 0) {
      section('TITLES')
      for (const key of owned) {
        const m = this._meta[key] || {}
        const isActive = key === activeTitle
        const row = this.add.rectangle(8, y, width - 16, 40, isActive ? 0x1a3a1a : 0x1a2a3a).setOrigin(0, 0)
        const nameTxt = this.add.text(16, y + 10, `${m.emoji || '🎖'} ${m.name || key}${isActive ? '  ✓' : ''}`, {
          fontFamily: 'monospace', fontSize: '12px', color: isActive ? '#44ff44' : '#ffffff',
        })
        const btnColor = isActive ? 0x3a1a1a : 0x1a4a1a
        const btn = this.add.rectangle(width - 14, y + 20, 80, 24, btnColor)
          .setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
        const btnLabel = this.add.text(width - 14, y + 20, isActive ? 'UNEQUIP' : 'EQUIP', {
          fontFamily: 'monospace', fontSize: '10px', color: '#ffffff',
        }).setOrigin(1, 0.5)
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
        y += 48
      }
    }

    return y
  }

  async _buy(itemKey) {
    try {
      await api.buyItem(itemKey)
      const [user, items, inv] = await Promise.all([api.getMe(), api.getStore(), api.getInventory()])
      GameState.setUser(user)
      GameState.setInventory(inv)
      this._items = items
      this._inv = inv
      for (const item of items) this._meta[item.key] = item
      this.hud.update()
      this._render()
      this._showToast('Purchased!')
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _useItem(key) {
    try {
      await api.useItem(key)
      const [user, inv] = await Promise.all([api.getMe(), api.getInventory()])
      GameState.setUser(user)
      GameState.setInventory(inv)
      this._inv = inv
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
      this._inv = inv
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
      this._inv = inv
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
