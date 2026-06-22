import Phaser from 'phaser'
import { api } from '../api.js'
import HUD from './HUD.js'

export default class AutofeedScene extends Phaser.Scene {
  constructor() { super('Autofeed') }

  async create() {
    this.hud = new HUD(this)
    this._data = null
    this._objs = []
    this._threshold = 50
    this._maxCoins = 100
    try {
      this._data = await api.getAutofeed()
      if (this._data.enabled) {
        this._threshold = this._data.threshold
        this._maxCoins = this._data.max_coins
      }
    } catch (_) {}
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    const { width, height } = this.scale

    const back = this.add.text(12, 52, '← Games', {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setDepth(1).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Games'))
    this._objs.push(back)

    const title = this.add.text(width / 2, 52, '⚙️ Auto-Feed', {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffd700',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(title)

    // Status badge
    const enabled = this._data?.enabled
    const statusTxt = this.add.text(width / 2, 80, enabled ? '● ON' : '● OFF', {
      fontFamily: 'monospace', fontSize: '13px', color: enabled ? '#44cc44' : '#cc4444',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(statusTxt)

    if (enabled) {
      const infoTxt = this.add.text(width / 2, 100, `Feeds < ${this._data.threshold} hunger  |  max ${this._data.max_coins} 🪙/tick`, {
        fontFamily: 'monospace', fontSize: '10px', color: '#888888',
      }).setOrigin(0.5, 0).setDepth(1)
      this._objs.push(infoTxt)
    }

    let y = 130

    // Threshold setting
    const threshLabel = this.add.text(20, y, 'Hunger threshold (feed below):', {
      fontFamily: 'monospace', fontSize: '11px', color: '#cccccc',
    }).setDepth(1)
    this._objs.push(threshLabel)
    y += 22

    const threshSteps = [20, 30, 40, 50, 60, 70, 80]
    const stepW = (width - 40) / threshSteps.length
    threshSteps.forEach((val, i) => {
      const bx = 20 + i * stepW
      const isSelected = val === this._threshold
      const btnBg = this.add.rectangle(bx, y, stepW - 2, 28, isSelected ? 0x1a3a5a : 0x111111).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
      const btnTxt = this.add.text(bx + (stepW - 2) / 2, y + 14, `${val}`, {
        fontFamily: 'monospace', fontSize: '11px', color: isSelected ? '#ffd700' : '#666666',
      }).setOrigin(0.5).setDepth(2)
      btnBg.on('pointerdown', () => { this._threshold = val; this._render() })
      this._objs.push(btnBg, btnTxt)
    })
    y += 38

    // Max coins setting
    const coinsLabel = this.add.text(20, y, 'Max coins per tick:', {
      fontFamily: 'monospace', fontSize: '11px', color: '#cccccc',
    }).setDepth(1)
    this._objs.push(coinsLabel)
    y += 22

    const coinSteps = [25, 50, 75, 100, 150, 200, 500]
    coinSteps.forEach((val, i) => {
      const bx = 20 + i * stepW
      const isSelected = val === this._maxCoins
      const btnBg = this.add.rectangle(bx, y, stepW - 2, 28, isSelected ? 0x1a3a5a : 0x111111).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
      const btnTxt = this.add.text(bx + (stepW - 2) / 2, y + 14, `${val}`, {
        fontFamily: 'monospace', fontSize: '10px', color: isSelected ? '#ffd700' : '#666666',
      }).setOrigin(0.5).setDepth(2)
      btnBg.on('pointerdown', () => { this._maxCoins = val; this._render() })
      this._objs.push(btnBg, btnTxt)
    })
    y += 46

    // Save button
    const saveBg = this.add.rectangle(20, y, width - 40, 36, 0x1a4a1a).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
    const saveTxt = this.add.text(width / 2, y + 18, '✅ Enable / Update', {
      fontFamily: 'monospace', fontSize: '12px', color: '#44cc44',
    }).setOrigin(0.5).setDepth(2)
    saveBg.on('pointerover', () => saveBg.setFillStyle(0x2a6a2a))
    saveBg.on('pointerout', () => saveBg.setFillStyle(0x1a4a1a))
    saveBg.on('pointerdown', () => this._save())
    this._objs.push(saveBg, saveTxt)
    y += 46

    // Disable button
    const disableBg = this.add.rectangle(20, y, width - 40, 36, 0x2a0a0a).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
    const disableTxt = this.add.text(width / 2, y + 18, '⏹ Disable Auto-Feed', {
      fontFamily: 'monospace', fontSize: '12px', color: '#cc4444',
    }).setOrigin(0.5).setDepth(2)
    disableBg.on('pointerover', () => disableBg.setFillStyle(0x3a1a1a))
    disableBg.on('pointerout', () => disableBg.setFillStyle(0x2a0a0a))
    disableBg.on('pointerdown', () => this._disable())
    this._objs.push(disableBg, disableTxt)

    // Explanation
    const desc = this.add.text(width / 2, y + 46, 'Auto-feed runs every ~30 min in the background.', {
      fontFamily: 'monospace', fontSize: '9px', color: '#444444',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(desc)
  }

  async _save() {
    try {
      const res = await api.setAutofeed(this._threshold, this._maxCoins)
      this._data = { enabled: true, threshold: this._threshold, max_coins: this._maxCoins }
      this._showToast(res.message)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _disable() {
    try {
      await api.disableAutofeed()
      this._data = { enabled: false, threshold: null, max_coins: null }
      this._showToast('Auto-feed disabled.')
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  _showToast(msg) {
    const { width, height } = this.scale
    const t = this.add.text(width / 2, height - 70, msg, {
      fontFamily: 'monospace', fontSize: '12px', color: '#ffd700',
      backgroundColor: '#000000cc', padding: { x: 8, y: 4 },
    }).setOrigin(0.5).setDepth(200)
    this.time.delayedCall(2500, () => t.destroy())
  }
}
