import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

export default class GamesScene extends Phaser.Scene {
  constructor() { super('Games') }

  create() {
    this.hud = new HUD(this)
    this._objs = []
    this._scrollContainer = null
    this._scrollY = 0
    this._scrollHandler = null
    this._wheelHandler = null
    this._triviaState = null
    this._triviaWager = 0
    this._investData = null
    this._investAmt = 100
    this._render()
    this._loadInvestment()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  async _loadInvestment() {
    try {
      this._investData = await api.getInvestment()
      this._render()
    } catch (_) {}
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

    this._scrollContainer = this.add.container(0, -this._scrollY)
    this._objs.push(this._scrollContainer)

    let y = 78

    const title = this.add.text(width / 2, y, '🎮 MINI-GAMES', {
      fontFamily: 'monospace', fontSize: '16px', color: '#ffd700',
    }).setOrigin(0.5)
    this._scrollContainer.add(title)
    y += 30

    y = this._renderMassageCard(y)
    y = this._renderDailyCard(y)
    y = this._renderTriviaCard(y)
    y = this._renderSlotsCard(y)
    y = this._renderGambleCard(y)
    y = this._renderInvestCard(y)
    y = this._renderAutofeedCard(y)

    this._attachScroll(this._scrollContainer, y - 78, height - 78 - 56)
  }

  _renderAutofeedCard(y) {
    const { width } = this.scale
    const innerY = this._cardBg(y, 56)
    const heading = this.add.text(12, innerY + 4, '⚙️ Auto-Feed', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    })
    const sub = this.add.text(12, innerY + 22, 'Auto-feed hungry animals on a timer', {
      fontFamily: 'monospace', fontSize: '10px', color: '#666666',
    })
    const btn = this.add.text(width - 14, innerY + 16, 'SETTINGS →', {
      fontFamily: 'monospace', fontSize: '11px', color: '#ffd700',
    }).setOrigin(1, 0.5).setInteractive({ useHandCursor: true })
    btn.on('pointerdown', () => this.scene.start('Autofeed'))
    this._scrollContainer.add([heading, sub, btn])
    return y + 64
  }

  // ── Daily Claim ──────────────────────────────────────────────────────────────

  _renderDailyCard(y) {
    const { width } = this.scale
    const streak = GameState.user?.daily_streak || 0
    const reward = streak >= 14 ? 150 : streak >= 7 ? 100 : streak >= 3 ? 75 : 50

    const innerY = this._cardBg(y, 80)
    const heading = this.add.text(12, innerY + 8, '📅 Daily Claim', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)
    const streakTxt = this.add.text(12, innerY + 28, `Streak: ${streak} days  →  ${reward} 🪙`, {
      fontFamily: 'monospace', fontSize: '11px', color: '#aaaaaa',
    }).setDepth(1)

    const btn = this.add.rectangle(width - 14, innerY + 38, 100, 26, 0x1a4a1a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
    const btnLabel = this.add.text(width - 14, innerY + 38, 'CLAIM', {
      fontFamily: 'monospace', fontSize: '12px', color: '#88ff88',
    }).setOrigin(1, 0.5).setDepth(2)
    btn.on('pointerdown', () => this._claimDaily())
    btn.on('pointerover', () => btn.setFillStyle(0x2a6a2a))
    btn.on('pointerout', () => btn.setFillStyle(0x1a4a1a))
    this._scrollContainer.add([heading, streakTxt, btn, btnLabel])
    return innerY + 88
  }

  async _claimDaily() {
    try {
      const res = await api.claimDaily()
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._showToast(`📅 Claimed ${res.coins} 🪙! Streak: ${res.streak}`)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Trivia ───────────────────────────────────────────────────────────────────

  _renderTriviaCard(y) {
    const { width } = this.scale
    const cardH = this._triviaState ? 220 : 72
    const innerY = this._cardBg(y, cardH)

    const heading = this.add.text(12, innerY + 8, '🧠 Trivia', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)
    this._scrollContainer.add(heading)

    if (!this._triviaState) {
      const btn = this.add.rectangle(width - 14, innerY + 36, 110, 26, 0x1a3a6a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(width - 14, innerY + 36, 'GET QUESTION', {
        fontFamily: 'monospace', fontSize: '10px', color: '#aaddff',
      }).setOrigin(1, 0.5).setDepth(2)
      btn.on('pointerdown', () => this._fetchTrivia())
      btn.on('pointerover', () => btn.setFillStyle(0x2a5a9a))
      btn.on('pointerout', () => btn.setFillStyle(0x1a3a6a))
      this._scrollContainer.add([btn, btnLabel])
    } else {
      const { question, choices, answer_key, answered, result } = this._triviaState

      const qTxt = this.add.text(12, innerY + 28, question, {
        fontFamily: 'monospace', fontSize: '10px', color: '#cccccc', wordWrap: { width: width - 24 },
      }).setDepth(1)
      this._scrollContainer.add(qTxt)

      choices.forEach((choice, ci) => {
        const by = innerY + 90 + ci * 28
        let color = 0x1a2a4a
        if (answered) {
          if (choice[0] === answer_key) color = 0x1a4a1a
          else if (choice[0] === answered && choice[0] !== answer_key) color = 0x4a1a1a
        }
        const cbtn = this.add.rectangle(12, by, width - 24, 22, color).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: !answered })
        const clabel = this.add.text(18, by + 11, choice, {
          fontFamily: 'monospace', fontSize: '10px', color: '#cccccc',
        }).setOrigin(0, 0.5).setDepth(2)
        if (!answered) {
          cbtn.on('pointerdown', () => this._answerTrivia(choice[0]))
          cbtn.on('pointerover', () => cbtn.setFillStyle(0x2a4a7a))
          cbtn.on('pointerout', () => cbtn.setFillStyle(0x1a2a4a))
        }
        this._scrollContainer.add([cbtn, clabel])
      })

      if (answered) {
        const coin = result?.coins || 0
        const coinTxt = this.add.text(width / 2, innerY + cardH - 18, coin >= 0 ? `+${coin} 🪙` : `${coin} 🪙`, {
          fontFamily: 'monospace', fontSize: '12px', color: coin >= 0 ? '#44ff44' : '#ff4444',
        }).setOrigin(0.5).setDepth(2)

        const nextBtn = this.add.text(width - 12, innerY + cardH - 18, '→ Next question', {
          fontFamily: 'monospace', fontSize: '10px', color: '#888888',
        }).setOrigin(1, 0.5).setDepth(2).setInteractive({ useHandCursor: true })
        nextBtn.on('pointerdown', () => { this._triviaState = null; this._render() })
        this._scrollContainer.add([coinTxt, nextBtn])
      }
    }
    return innerY + cardH + 8
  }

  async _fetchTrivia() {
    try {
      const q = await api.getTriviaQuestion()
      this._triviaState = { question: q.question, choices: q.choices, answer_key: q._answer_key, answered: null, result: null }
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _answerTrivia(choice) {
    try {
      const result = await api.answerTrivia(this._triviaState.question, choice, 0)
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._triviaState.answered = choice
      this._triviaState.result = result
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Slots ────────────────────────────────────────────────────────────────────

  _renderSlotsCard(y) {
    const { width } = this.scale
    const innerY = this._cardBg(y, 90)

    const heading = this.add.text(12, innerY + 8, '🎰 Slots  (10 🪙/spin)', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)
    this._scrollContainer.add(heading)

    if (this._slotsResult) {
      const { reels, net } = this._slotsResult
      const reelsTxt = this.add.text(width / 2, innerY + 38, reels.join('  '), {
        fontFamily: 'monospace', fontSize: '22px',
      }).setOrigin(0.5).setDepth(2)
      const netTxt = this.add.text(width / 2, innerY + 66, net >= 0 ? `+${net} 🪙` : `${net} 🪙`, {
        fontFamily: 'monospace', fontSize: '12px', color: net >= 0 ? '#44ff44' : '#ff4444',
      }).setOrigin(0.5).setDepth(2)
      this._scrollContainer.add([reelsTxt, netTxt])
    }

    const btn = this.add.rectangle(width - 14, innerY + 38, 80, 26, 0x4a2a0a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
    const btnLabel = this.add.text(width - 14, innerY + 38, '🎰 SPIN', {
      fontFamily: 'monospace', fontSize: '11px', color: '#ffcc44',
    }).setOrigin(1, 0.5).setDepth(2)
    btn.on('pointerdown', () => this._spinSlots())
    btn.on('pointerover', () => btn.setFillStyle(0x6a4a1a))
    btn.on('pointerout', () => btn.setFillStyle(0x4a2a0a))
    this._scrollContainer.add([btn, btnLabel])
    return innerY + 98
  }

  async _spinSlots() {
    try {
      const res = await api.spinSlots()
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._slotsResult = res
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Gamble ───────────────────────────────────────────────────────────────────

  _renderGambleCard(y) {
    const { width } = this.scale
    const innerY = this._cardBg(y, 90)
    if (!this._gambBet) this._gambBet = 50

    const heading = this.add.text(12, innerY + 8, '💰 Coin Flip', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)

    const minusBtn = this.add.text(14, innerY + 44, '[-]', {
      fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
    }).setDepth(2).setInteractive({ useHandCursor: true })
    minusBtn.on('pointerdown', () => { this._gambBet = Math.max(10, this._gambBet - 10); this._render() })

    const betLabel = this.add.text(70, innerY + 44, `${this._gambBet} 🪙`, {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffd700',
    }).setOrigin(0, 0.5).setDepth(2)

    const plusBtn = this.add.text(140, innerY + 44, '[+]', {
      fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
    }).setDepth(2).setInteractive({ useHandCursor: true })
    plusBtn.on('pointerdown', () => { this._gambBet = Math.min(500, this._gambBet + 10); this._render() })

    const toAdd = [heading, minusBtn, betLabel, plusBtn]

    if (this._gambResult) {
      const { won, delta } = this._gambResult
      const resultTxt = this.add.text(width / 2, innerY + 66, won ? `✅ +${delta} 🪙` : `❌ ${delta} 🪙`, {
        fontFamily: 'monospace', fontSize: '13px', color: won ? '#44ff44' : '#ff4444',
      }).setOrigin(0.5).setDepth(2)
      toAdd.push(resultTxt)
    }

    const btn = this.add.rectangle(width - 14, innerY + 44, 80, 26, 0x3a1a4a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
    const btnLabel = this.add.text(width - 14, innerY + 44, '🪙 FLIP', {
      fontFamily: 'monospace', fontSize: '11px', color: '#dd88ff',
    }).setOrigin(1, 0.5).setDepth(2)
    btn.on('pointerdown', () => this._gamble())
    btn.on('pointerover', () => btn.setFillStyle(0x5a2a6a))
    btn.on('pointerout', () => btn.setFillStyle(0x3a1a4a))
    toAdd.push(btn, btnLabel)

    this._scrollContainer.add(toAdd)
    return innerY + 98
  }

  async _gamble() {
    try {
      const res = await api.gamble(this._gambBet)
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._gambResult = res
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Foot Massage ─────────────────────────────────────────────────────────────

  _getMassageStatus() {
    const ts = GameState.user?.massage_active_until
    if (!ts) return { state: 'available' }
    const untilMs = new Date(ts + 'Z').getTime()
    const now = Date.now()
    if (untilMs > now) {
      return { state: 'active', minsLeft: Math.ceil((untilMs - now) / 60000) }
    }
    const cooldownEnd = untilMs + 4 * 3600 * 1000
    if (now < cooldownEnd) {
      return { state: 'cooldown', minsLeft: Math.ceil((cooldownEnd - now) / 60000) }
    }
    return { state: 'available' }
  }

  _renderMassageCard(y) {
    const { width } = this.scale
    const innerY = this._cardBg(y, 72)
    const heading = this.add.text(12, innerY + 8, '🦶 Foot Massage  (25 🪙)', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)

    const status = this._getMassageStatus()
    let statusText = ''
    if (status.state === 'active') statusText = `Active — ${status.minsLeft}m left`
    else if (status.state === 'cooldown') statusText = `Cooldown — ${status.minsLeft}m`
    const subTxt = this.add.text(12, innerY + 28, statusText || 'Halves hunger decay for 1h', {
      fontFamily: 'monospace', fontSize: '10px', color: '#aaaaaa',
    }).setDepth(1)

    const canMassage = status.state === 'available'
    const btn = this.add.rectangle(width - 14, innerY + 38, 100, 26, canMassage ? 0x1a2a4a : 0x111111)
      .setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: canMassage })
    const btnLabel = this.add.text(width - 14, innerY + 38, 'MASSAGE', {
      fontFamily: 'monospace', fontSize: '11px', color: canMassage ? '#aaddff' : '#555555',
    }).setOrigin(1, 0.5).setDepth(2)
    if (canMassage) {
      btn.on('pointerdown', () => this._massage())
      btn.on('pointerover', () => btn.setFillStyle(0x2a4a7a))
      btn.on('pointerout', () => btn.setFillStyle(0x1a2a4a))
    }
    this._scrollContainer.add([heading, subTxt, btn, btnLabel])
    return innerY + 80
  }

  async _massage() {
    try {
      await api.massageAnimals()
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._showToast('🦶 Massage activated! Hunger decays slower for 1h')
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Investment Bank ───────────────────────────────────────────────────────────

  _renderInvestCard(y) {
    const { width } = this.scale
    const d = this._investData
    const cardH = 100
    const innerY = this._cardBg(y, cardH)

    const heading = this.add.text(12, innerY + 8, '📈 Investment Bank', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)
    this._scrollContainer.add(heading)

    if (!d) {
      const loadTxt = this.add.text(12, innerY + 30, 'Loading…', {
        fontFamily: 'monospace', fontSize: '10px', color: '#555555',
      }).setDepth(1)
      this._scrollContainer.add(loadTxt)
      return innerY + cardH + 8
    }

    if (d.active) {
      const readyLabel = d.is_ready ? '✅ READY TO COLLECT' : `⏳ ${this._fmtSecs(d.seconds_remaining)}`
      const amtTxt = this.add.text(12, innerY + 28, `${d.amount} 🪙  →  ${d.return_amount} 🪙  (+${d.rate_pct}%)`, {
        fontFamily: 'monospace', fontSize: '10px', color: '#aaaaaa',
      }).setDepth(1)
      const statusTxt = this.add.text(12, innerY + 46, readyLabel, {
        fontFamily: 'monospace', fontSize: '11px', color: d.is_ready ? '#44ff44' : '#ffd700',
      }).setDepth(1)
      this._scrollContainer.add([amtTxt, statusTxt])

      if (d.is_ready) {
        const btn = this.add.rectangle(width - 14, innerY + 60, 100, 26, 0x1a4a1a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
        const btnLabel = this.add.text(width - 14, innerY + 60, 'COLLECT', {
          fontFamily: 'monospace', fontSize: '11px', color: '#88ff88',
        }).setOrigin(1, 0.5).setDepth(2)
        btn.on('pointerdown', () => this._collectInvest())
        btn.on('pointerover', () => btn.setFillStyle(0x2a6a2a))
        btn.on('pointerout', () => btn.setFillStyle(0x1a4a1a))
        this._scrollContainer.add([btn, btnLabel])
      }
    } else {
      const rateTxt = this.add.text(12, innerY + 28, `${d.rate_pct}% return after ${d.hours}h`, {
        fontFamily: 'monospace', fontSize: '10px', color: '#aaaaaa',
      }).setDepth(1)

      const minus = this.add.text(12, innerY + 60, '[-]', {
        fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
      }).setDepth(2).setInteractive({ useHandCursor: true })
      minus.on('pointerdown', () => { this._investAmt = Math.max(10, this._investAmt - 10); this._render() })

      const amtLabel = this.add.text(60, innerY + 60, `${this._investAmt} 🪙`, {
        fontFamily: 'monospace', fontSize: '13px', color: '#ffd700',
      }).setOrigin(0, 0.5).setDepth(2)

      const plus = this.add.text(130, innerY + 60, '[+]', {
        fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
      }).setDepth(2).setInteractive({ useHandCursor: true })
      plus.on('pointerdown', () => { this._investAmt = Math.min(9999, this._investAmt + 10); this._render() })

      const btn = this.add.rectangle(width - 14, innerY + 60, 100, 26, 0x1a3a1a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(width - 14, innerY + 60, 'INVEST', {
        fontFamily: 'monospace', fontSize: '11px', color: '#88ff88',
      }).setOrigin(1, 0.5).setDepth(2)
      btn.on('pointerdown', () => this._invest())
      btn.on('pointerover', () => btn.setFillStyle(0x2a5a2a))
      btn.on('pointerout', () => btn.setFillStyle(0x1a3a1a))
      this._scrollContainer.add([rateTxt, minus, amtLabel, plus, btn, btnLabel])
    }

    return innerY + cardH + 8
  }

  _fmtSecs(s) {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    return h ? `${h}h ${m}m` : `${m}m`
  }

  async _invest() {
    try {
      const res = await api.createInvestment(this._investAmt)
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._investData = { active: true, amount: res.amount, return_amount: res.return_amount, rate_pct: res.rate_pct, hours: res.hours, is_ready: false, seconds_remaining: res.hours * 3600 }
      this._showToast(`📈 Invested ${res.amount} 🪙!`)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _collectInvest() {
    try {
      const res = await api.collectInvestment()
      const user = await api.getMe()
      GameState.setUser(user)
      this.hud.update()
      this._investData = { active: false, rate_pct: this._investData?.rate_pct || 25, hours: this._investData?.hours || 24 }
      this._showToast(`💰 Collected ${res.return_amount} 🪙! (+${res.profit})`)
      this._render()
    } catch (err) {
      this._showToast(err.message)
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  _cardBg(y, h) {
    const { width } = this.scale
    const bg = this.add.rectangle(8, y, width - 16, h, 0x1a2a3a).setOrigin(0, 0).setDepth(0)
    this._scrollContainer.add(bg)
    return y + 8
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
