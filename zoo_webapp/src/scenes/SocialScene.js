import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

const RARITY_COLORS = { common: '#888888', rare: '#4488ff', epic: '#aa44ff', legendary: '#ffaa00' }
const TABS = ['VISIT', 'GIFT', 'TRADE']

export default class SocialScene extends Phaser.Scene {
  constructor() { super('Social') }

  async create() {
    this.hud = new HUD(this)
    this._objs = []
    this._container = null
    this._tab = 'VISIT'
    this._partner = null
    this._trades = null
    this._selectingMyAnimal = null
    this._scrollY = 0
    this._scrollHandler = null
    this._wheelHandler = null

    try { this._partner = await api.getPartner() } catch (_) {}
    try {
      const t = await api.getTrades()
      this._trades = t
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
    this._container = null
  }

  _render() {
    this._clear()
    const { width, height } = this.scale

    const back = this.add.text(12, 52, '← Zoo', {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setDepth(1).setInteractive({ useHandCursor: true })
    back.on('pointerdown', () => this.scene.start('Zoo'))
    this._objs.push(back)

    const partner = this._partner
    const partnerName = partner ? `@${partner.username}` : '—'

    const headerTxt = this.add.text(width / 2, 52, `💌 Social  ${partnerName}`, {
      fontFamily: 'monospace', fontSize: '13px', color: partner ? '#ffd700' : '#666666',
    }).setOrigin(0.5, 0).setDepth(1)
    this._objs.push(headerTxt)

    if (!partner) {
      const noPartnerTxt = this.add.text(width / 2, height / 2,
        'No partner found.\nMake sure you both share a group chat.', {
          fontFamily: 'monospace', fontSize: '12px', color: '#666666',
          align: 'center',
        }).setOrigin(0.5)
      this._objs.push(noPartnerTxt)
      return
    }

    // Tab strip
    const tabY = 74
    const tabW = width / TABS.length
    TABS.forEach((tab, i) => {
      const isActive = tab === this._tab
      const tabBg = this.add.rectangle(i * tabW, tabY, tabW, 22, isActive ? 0x1a3a5a : 0x111111).setOrigin(0, 0).setDepth(1)
      const tabTxt = this.add.text(i * tabW + tabW / 2, tabY + 11, tab, {
        fontFamily: 'monospace', fontSize: '10px', color: isActive ? '#ffd700' : '#666666',
      }).setOrigin(0.5).setDepth(2).setInteractive({ useHandCursor: true })
      tabTxt.on('pointerdown', () => {
        this._tab = tab
        this._selectingMyAnimal = null
        this._scrollY = 0
        this._render()
      })
      this._objs.push(tabBg, tabTxt)
    })

    const TOP = 100
    this._container = this.add.container(0, -this._scrollY)
    this._objs.push(this._container)

    if (this._tab === 'VISIT') this._renderVisit(TOP, width, height)
    else if (this._tab === 'GIFT') this._renderGift(TOP, width, height)
    else if (this._tab === 'TRADE') this._renderTrade(TOP, width, height)
  }

  // ── VISIT ──────────────────────────────────────────────────────────────────

  _renderVisit(TOP, width, height) {
    const partner = this._partner
    let y = TOP

    const feedBg = this.add.rectangle(16, y, width - 32, 40, 0x1a3a1a).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
    const feedTxt = this.add.text(width / 2, y + 20, `🍖 Feed ${partner.username}'s hungriest animal`, {
      fontFamily: 'monospace', fontSize: '11px', color: '#44cc44',
    }).setOrigin(0.5).setDepth(2)
    feedBg.on('pointerover', () => feedBg.setFillStyle(0x2a5a2a))
    feedBg.on('pointerout', () => feedBg.setFillStyle(0x1a3a1a))
    feedBg.on('pointerdown', () => this._doFeed())
    this._container.add([feedBg, feedTxt])
    y += 48

    const subTxt = this.add.text(width / 2, y, `(once per 24h — earn +15 🪙 bonus)`, {
      fontFamily: 'monospace', fontSize: '9px', color: '#444444',
    }).setOrigin(0.5, 0).setDepth(1)
    this._container.add(subTxt)
    y += 22

    const animals = partner.animals || []
    if (!animals.length) {
      const emptyTxt = this.add.text(width / 2, y + 20, `${partner.username}'s zoo is empty.`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#444444',
      }).setOrigin(0.5, 0).setDepth(1)
      this._container.add(emptyTxt)
      return
    }

    const countTxt = this.add.text(width / 2, y, `${partner.username}'s zoo  (${animals.length} animals)`, {
      fontFamily: 'monospace', fontSize: '11px', color: '#888888',
    }).setOrigin(0.5, 0).setDepth(1)
    this._container.add(countTxt)
    y += 20

    animals.forEach((a) => {
      const name = a.nickname || a.species_name || '?'
      const rowBg = this.add.rectangle(8, y, width - 16, 34, 0x0d1b2a).setOrigin(0, 0)
      const emojiTxt = this.add.text(16, y + 17, a.emoji || '🐾', { fontSize: '16px' }).setOrigin(0, 0.5)
      const nameTxt = this.add.text(40, y + 6, name, {
        fontFamily: 'monospace', fontSize: '11px', color: '#cccccc',
      })
      const rarityColor = RARITY_COLORS[a.rarity] || '#888888'
      const rarTxt = this.add.text(40, y + 20, a.rarity?.toUpperCase() || '', {
        fontFamily: 'monospace', fontSize: '9px', color: rarityColor,
      })
      const hungerW = Math.round((width - 90) * (a.hunger / 100))
      const hBarBg = this.add.rectangle(width - 74, y + 10, 60, 8, 0x333333).setOrigin(0, 0)
      const hBarFill = this.add.rectangle(width - 74, y + 10, hungerW * 60 / (width - 90), 8,
        a.hunger > 50 ? 0x44cc44 : a.hunger > 20 ? 0xffaa00 : 0xff3333
      ).setOrigin(0, 0)
      this._container.add([rowBg, emojiTxt, nameTxt, rarTxt, hBarBg, hBarFill])
      y += 38
    })

    this._attachScroll(this._container, y - TOP, height - TOP - 56)
  }

  // ── GIFT ───────────────────────────────────────────────────────────────────

  _renderGift(TOP, width, height) {
    let y = TOP
    const animals = (GameState.animals || []).filter(a => !a.is_breeding)

    const hintTxt = this.add.text(width / 2, y, 'Tap an animal to gift it to your partner.', {
      fontFamily: 'monospace', fontSize: '10px', color: '#666666',
    }).setOrigin(0.5, 0).setDepth(1)
    this._container.add(hintTxt)
    y += 20

    if (!animals.length) {
      const emptyTxt = this.add.text(width / 2, y + 20, 'No giftable animals.', {
        fontFamily: 'monospace', fontSize: '12px', color: '#444444',
      }).setOrigin(0.5, 0).setDepth(1)
      this._container.add(emptyTxt)
      return
    }

    animals.forEach((a) => {
      const name = a.nickname || a.species_name || '?'
      const isSelected = this._selectingMyAnimal?.animal_id === a.animal_id
      const rowBg = this.add.rectangle(8, y, width - 16, 38, isSelected ? 0x1a3a5a : 0x0d1b2a)
        .setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const emojiTxt = this.add.text(16, y + 19, a.emoji || '🐾', { fontSize: '16px' }).setOrigin(0, 0.5)
      const nameTxt = this.add.text(40, y + 8, name, {
        fontFamily: 'monospace', fontSize: '11px', color: '#cccccc',
      })
      const rarityColor = RARITY_COLORS[a.rarity] || '#888888'
      const rarTxt = this.add.text(40, y + 22, a.rarity?.toUpperCase() || '', {
        fontFamily: 'monospace', fontSize: '9px', color: rarityColor,
      })
      rowBg.on('pointerover', () => rowBg.setFillStyle(isSelected ? 0x2a5a8a : 0x1a2a3a))
      rowBg.on('pointerout', () => rowBg.setFillStyle(isSelected ? 0x1a3a5a : 0x0d1b2a))
      rowBg.on('pointerdown', () => { this._selectingMyAnimal = a; this._render() })
      this._container.add([rowBg, emojiTxt, nameTxt, rarTxt])
      y += 42
    })

    if (this._selectingMyAnimal) {
      const a = this._selectingMyAnimal
      const name = a.nickname || a.species_name || '?'
      const confirmBg = this.add.rectangle(16, y + 8, width - 32, 44, 0x2a1a00).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
      const confirmTxt = this.add.text(width / 2, y + 30, `🎁 Gift ${a.emoji} ${name} to @${this._partner.username}?`, {
        fontFamily: 'monospace', fontSize: '11px', color: '#ffaa44',
      }).setOrigin(0.5).setDepth(2)
      const confirmBtn = this.add.text(width / 2, y + 52, '[ CONFIRM GIFT ]', {
        fontFamily: 'monospace', fontSize: '12px', color: '#ffd700',
        backgroundColor: '#442200', padding: { x: 6, y: 3 },
      }).setOrigin(0.5, 0).setDepth(2).setInteractive({ useHandCursor: true })
      confirmBtn.on('pointerdown', () => this._doGift(a.animal_id))
      this._container.add([confirmBg, confirmTxt, confirmBtn])
      y += 72
    }

    this._attachScroll(this._container, y - TOP, height - TOP - 56)
  }

  // ── TRADE ──────────────────────────────────────────────────────────────────

  _renderTrade(TOP, width, height) {
    let y = TOP
    const trades = this._trades?.trades || []
    const incoming = trades.filter(t => t.is_incoming)
    const outgoing = trades.filter(t => !t.is_incoming)

    if (incoming.length) {
      const inHdr = this.add.text(12, y, '📬 Incoming trade offers', {
        fontFamily: 'monospace', fontSize: '11px', color: '#ffd700',
      }).setDepth(1)
      this._container.add(inHdr)
      y += 18

      incoming.forEach((t) => {
        const myA = t.their_animal
        const theirA = t.my_animal
        if (!myA || !theirA) return
        const cardBg = this.add.rectangle(8, y, width - 16, 62, 0x1a1a00).setOrigin(0, 0)
        const line1 = this.add.text(14, y + 6, `They offer: ${theirA.emoji} ${theirA.nickname || theirA.species_name}`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#cccccc',
        })
        const line2 = this.add.text(14, y + 20, `For your:   ${myA.emoji} ${myA.nickname || myA.species_name}`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#cccccc',
        })
        const acceptBtn = this.add.text(width / 2 - 4, y + 38, '✅ Accept', {
          fontFamily: 'monospace', fontSize: '11px', color: '#44cc44',
          backgroundColor: '#001a00', padding: { x: 6, y: 3 },
        }).setOrigin(1, 0).setDepth(2).setInteractive({ useHandCursor: true })
        const declineBtn = this.add.text(width / 2 + 4, y + 38, '❌ Decline', {
          fontFamily: 'monospace', fontSize: '11px', color: '#cc4444',
          backgroundColor: '#1a0000', padding: { x: 6, y: 3 },
        }).setOrigin(0, 0).setDepth(2).setInteractive({ useHandCursor: true })
        acceptBtn.on('pointerdown', () => this._doRespondTrade(t.trade_id, 'accept'))
        declineBtn.on('pointerdown', () => this._doRespondTrade(t.trade_id, 'decline'))
        this._container.add([cardBg, line1, line2, acceptBtn, declineBtn])
        y += 68
      })
    }

    if (outgoing.length) {
      const outHdr = this.add.text(12, y, '📤 Your pending offers', {
        fontFamily: 'monospace', fontSize: '11px', color: '#888888',
      }).setDepth(1)
      this._container.add(outHdr)
      y += 18

      outgoing.forEach((t) => {
        const myA = t.my_animal
        const theirA = t.their_animal
        if (!myA || !theirA) return
        const cardBg = this.add.rectangle(8, y, width - 16, 44, 0x111111).setOrigin(0, 0)
        const line1 = this.add.text(14, y + 8, `Your: ${myA.emoji} ${myA.nickname || myA.species_name}`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#888888',
        })
        const line2 = this.add.text(14, y + 22, `For:  ${theirA.emoji} ${theirA.nickname || theirA.species_name}  (awaiting)`, {
          fontFamily: 'monospace', fontSize: '10px', color: '#666666',
        })
        this._container.add([cardBg, line1, line2])
        y += 50
      })
    }

    const proposeHdr = this.add.text(12, y, '🔄 Propose a trade', {
      fontFamily: 'monospace', fontSize: '11px', color: '#ffd700',
    }).setDepth(1)
    this._container.add(proposeHdr)
    y += 20

    const myAnimals = (GameState.animals || []).filter(a => !a.is_breeding)
    const theirAnimals = (this._partner?.animals || []).filter(a => !a.is_breeding)

    if (!myAnimals.length || !theirAnimals.length) {
      const noTxt = this.add.text(width / 2, y, 'Both players need non-breeding animals to trade.', {
        fontFamily: 'monospace', fontSize: '10px', color: '#444444', wordWrap: { width: width - 24 },
      }).setOrigin(0.5, 0).setDepth(1)
      this._container.add(noTxt)
      return
    }

    const colW = (width - 24) / 2
    const yourHdr = this.add.text(12, y, 'Your animal', {
      fontFamily: 'monospace', fontSize: '9px', color: '#888888',
    }).setDepth(1)
    const theirHdr = this.add.text(12 + colW + 4, y, "Partner's animal", {
      fontFamily: 'monospace', fontSize: '9px', color: '#888888',
    }).setDepth(1)
    this._container.add([yourHdr, theirHdr])
    y += 14

    const maxRows = Math.max(myAnimals.length, theirAnimals.length)
    const myPick = this._selectingMyAnimal
    const theirPick = this._tradeTheirPick

    myAnimals.forEach((a, i) => {
      const ry = y + i * 32
      const isSelected = myPick?.animal_id === a.animal_id
      const rowBg = this.add.rectangle(8, ry, colW, 28, isSelected ? 0x1a3a5a : 0x0d1b2a)
        .setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const txt = this.add.text(14, ry + 14, `${a.emoji} ${(a.nickname || a.species_name || '?').slice(0, 10)}`, {
        fontFamily: 'monospace', fontSize: '9px', color: isSelected ? '#ffd700' : '#aaaaaa',
      }).setOrigin(0, 0.5)
      rowBg.on('pointerdown', () => { this._selectingMyAnimal = a; this._render() })
      this._container.add([rowBg, txt])
    })

    theirAnimals.forEach((a, i) => {
      const ry = y + i * 32
      const isSelected = theirPick?.animal_id === a.animal_id
      const rowBg = this.add.rectangle(12 + colW + 4, ry, colW, 28, isSelected ? 0x1a3a5a : 0x0d1b2a)
        .setOrigin(0, 0).setInteractive({ useHandCursor: true })
      const txt = this.add.text(12 + colW + 10, ry + 14, `${a.emoji} ${(a.nickname || a.species_name || '?').slice(0, 10)}`, {
        fontFamily: 'monospace', fontSize: '9px', color: isSelected ? '#ffd700' : '#aaaaaa',
      }).setOrigin(0, 0.5)
      rowBg.on('pointerdown', () => { this._tradeTheirPick = a; this._render() })
      this._container.add([rowBg, txt])
    })

    y += maxRows * 32 + 8

    if (this._selectingMyAnimal && this._tradeTheirPick) {
      const myA = this._selectingMyAnimal
      const thA = this._tradeTheirPick
      const propBtn = this.add.rectangle(16, y, width - 32, 36, 0x1a2a00).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: true })
      const propTxt = this.add.text(width / 2, y + 18,
        `🔄 Propose: ${myA.emoji} ↔ ${thA.emoji}`, {
          fontFamily: 'monospace', fontSize: '11px', color: '#88ff44',
        }).setOrigin(0.5).setDepth(2)
      propBtn.on('pointerover', () => propBtn.setFillStyle(0x2a4000))
      propBtn.on('pointerout', () => propBtn.setFillStyle(0x1a2a00))
      propBtn.on('pointerdown', () => this._doProposeTrade(myA.animal_id, thA.animal_id))
      this._container.add([propBtn, propTxt])
      y += 44
    }

    this._attachScroll(this._container, y - TOP, height - TOP - 56)
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  async _doFeed() {
    try {
      const res = await api.visitFeed()
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._partner = await api.getPartner()
      this._showToast(res.message)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _doGift(animal_id) {
    try {
      const res = await api.giftAnimal(animal_id)
      const animals = await api.getAnimals()
      GameState.setAnimals(animals)
      this._partner = await api.getPartner()
      this._selectingMyAnimal = null
      this._showToast(res.message)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _doProposeTrade(myId, theirId) {
    try {
      const res = await api.proposeTrade(myId, theirId)
      const t = await api.getTrades()
      this._trades = t
      this._selectingMyAnimal = null
      this._tradeTheirPick = null
      this._showToast(res.message)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _doRespondTrade(trade_id, action) {
    try {
      const res = await api.respondTrade(trade_id, action)
      const [animals, t, partner] = await Promise.all([
        api.getAnimals(), api.getTrades(), api.getPartner(),
      ])
      GameState.setAnimals(animals)
      this._trades = t
      this._partner = partner
      this._showToast(res.message)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

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
      fontFamily: 'monospace', fontSize: '12px', color: '#ffd700',
      backgroundColor: '#000000cc', padding: { x: 8, y: 4 },
    }).setOrigin(0.5).setDepth(200)
    this.time.delayedCall(2800, () => t.destroy())
  }
}
