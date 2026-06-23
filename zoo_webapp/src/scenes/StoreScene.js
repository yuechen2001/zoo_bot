import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

const TABS = ['Items', 'Lures', 'Titles']

export default class StoreScene extends Phaser.Scene {
  constructor() { super('Store') }

  async create() {
    this.hud = new HUD(this)
    this._tab = 0
    this._items = []
    this._objs = []
    this._scrollContainer = null
    this._scrollY = 0
    this._scrollHandler = null
    this._wheelHandler = null
    try {
      this._items = await api.getStore()
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

    const invBtn = this.add.text(width - 6, 82, '🎒', {
      fontFamily: 'monospace', fontSize: '14px', color: '#aaaaaa',
    }).setOrigin(1, 0.5).setDepth(5).setInteractive({ useHandCursor: true })
    invBtn.on('pointerdown', () => this.scene.start('Inventory'))
    invBtn.on('pointerover', () => invBtn.setColor('#ffd700'))
    invBtn.on('pointerout', () => invBtn.setColor('#aaaaaa'))
    this._objs.push(invBtn)

    const tabW = width / TABS.length
    TABS.forEach((tab, i) => {
      const bg = this.add.rectangle(i * tabW, 68, tabW, 28, i === this._tab ? 0x2a4a6a : 0x1a2a3a).setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const label = this.add.text(i * tabW + tabW / 2, 82, tab, {
        fontFamily: 'monospace', fontSize: '12px', color: i === this._tab ? '#ffd700' : '#888888',
      }).setOrigin(0.5)
      bg.on('pointerdown', () => { this._tab = i; this._scrollY = 0; this._render() })
      this._objs.push(bg, label)
    })

    const filtered = this._items.filter(item => {
      if (this._tab === 1) return item.key?.startsWith('lure_')
      if (this._tab === 0) return item.category === 'item' && !item.key?.startsWith('lure_')
      return item.category === 'cosmetic'
    })

    const TOP = 104
    this._scrollContainer = this.add.container(0, -this._scrollY)
    this._objs.push(this._scrollContainer)

    let y = TOP
    filtered.forEach((item) => {
      const row = this.add.rectangle(8, y, width - 16, 48, 0x1a2a3a).setOrigin(0, 0)
      const nameLabel = this.add.text(16, y + 8, `${item.emoji} ${item.name}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffffff',
      })
      const desc = this.add.text(16, y + 28, item.desc.slice(0, 48) + (item.desc.length > 48 ? '…' : ''), {
        fontFamily: 'monospace', fontSize: '9px', color: '#888888',
      })

      const btnLabel = item.owned ? '✓ Owned' : `${item.price} 🪙`
      const btnColor = item.owned ? 0x1a4a1a : 0x2a4a8a
      const buyBtn = this.add.rectangle(width - 14, y + 24, 80, 26, btnColor).setOrigin(1, 0.5)
        .setInteractive({ useHandCursor: true })
      const buyLabel = this.add.text(width - 14, y + 24, btnLabel, {
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
      y += 56
    })

    this._attachScroll(this._scrollContainer, y - TOP, height - TOP - 56)
  }

  async _buy(itemKey) {
    try {
      await api.buyItem(itemKey)
      const [user, items, inv] = await Promise.all([api.getMe(), api.getStore(), api.getInventory()])
      GameState.setUser(user)
      GameState.setInventory(inv)
      this._items = items
      this.hud.update()
      this._render()
      this._showToast('Purchased!')
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
