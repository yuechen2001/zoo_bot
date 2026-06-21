import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

export default class GamesScene extends Phaser.Scene {
  constructor() { super('Games') }

  create() {
    this.hud = new HUD(this)
    this._objs = []
    this._triviaState = null  // null | { question, choices, answer_key, wager }
    this._triviaWager = 0
    this._render()
    this.scale.on('resize', (s) => { this.hud.resize(s.width, s.height); this._render() })
  }

  _clear() { this._objs.forEach(o => o.destroy()); this._objs = [] }

  _render() {
    this._clear()
    const { width } = this.scale
    let y = 78

    const title = this.add.text(width / 2, y, '🎮 MINI-GAMES', {
      fontFamily: 'monospace', fontSize: '16px', color: '#ffd700',
    }).setOrigin(0.5)
    this._objs.push(title)
    y += 30

    y = this._renderDailyCard(y)
    y = this._renderTriviaCard(y)
    y = this._renderSlotsCard(y)
    y = this._renderGambleCard(y)
  }

  // ── Daily Claim ──────────────────────────────────────────────────────────────

  _renderDailyCard(y) {
    const { width } = this.scale
    const streak = GameState.user?.daily_streak || 0
    const reward = streak >= 14 ? 150 : streak >= 7 ? 100 : streak >= 3 ? 75 : 50

    y = this._cardBg(y, 80)
    this.add.text(12, y + 8, `📅 Daily Claim`, {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)
    this.add.text(12, y + 28, `Streak: ${streak} days  →  ${reward} 🪙`, {
      fontFamily: 'monospace', fontSize: '11px', color: '#aaaaaa',
    }).setDepth(1)

    const btn = this.add.rectangle(width - 14, y + 38, 100, 26, 0x1a4a1a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
    const btnLabel = this.add.text(width - 14, y + 38, 'CLAIM', {
      fontFamily: 'monospace', fontSize: '12px', color: '#88ff88',
    }).setOrigin(1, 0.5).setDepth(2)
    btn.on('pointerdown', () => this._claimDaily())
    btn.on('pointerover', () => btn.setFillStyle(0x2a6a2a))
    btn.on('pointerout', () => btn.setFillStyle(0x1a4a1a))
    this._objs.push(btn, btnLabel)
    return y + 88
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
    y = this._cardBg(y, cardH)

    this.add.text(12, y + 8, '🧠 Trivia', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)

    if (!this._triviaState) {
      const btn = this.add.rectangle(width - 14, y + 36, 110, 26, 0x1a3a6a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(width - 14, y + 36, 'GET QUESTION', {
        fontFamily: 'monospace', fontSize: '10px', color: '#aaddff',
      }).setOrigin(1, 0.5).setDepth(2)
      btn.on('pointerdown', () => this._fetchTrivia())
      btn.on('pointerover', () => btn.setFillStyle(0x2a5a9a))
      btn.on('pointerout', () => btn.setFillStyle(0x1a3a6a))
      this._objs.push(btn, btnLabel)
    } else {
      const { question, choices, answer_key, answered, result } = this._triviaState

      this.add.text(12, y + 28, question, {
        fontFamily: 'monospace', fontSize: '10px', color: '#cccccc', wordWrap: { width: width - 24 },
      }).setDepth(1)

      choices.forEach((choice, ci) => {
        const by = y + 90 + ci * 28
        let color = 0x1a2a4a
        if (answered) {
          if (choice === answer_key) color = 0x1a4a1a
          else if (choice === answered && choice !== answer_key) color = 0x4a1a1a
        }
        const cbtn = this.add.rectangle(12, by, width - 24, 22, color).setOrigin(0, 0).setDepth(1).setInteractive({ useHandCursor: !answered })
        const clabel = this.add.text(18, by + 11, choice, {
          fontFamily: 'monospace', fontSize: '10px', color: '#cccccc',
        }).setOrigin(0, 0.5).setDepth(2)
        if (!answered) {
          cbtn.on('pointerdown', () => this._answerTrivia(choice))
          cbtn.on('pointerover', () => cbtn.setFillStyle(0x2a4a7a))
          cbtn.on('pointerout', () => cbtn.setFillStyle(0x1a2a4a))
        }
        this._objs.push(cbtn, clabel)
      })

      if (answered) {
        const coin = result?.coins || 0
        this.add.text(width / 2, y + cardH - 18, coin >= 0 ? `+${coin} 🪙` : `${coin} 🪙`, {
          fontFamily: 'monospace', fontSize: '12px', color: coin >= 0 ? '#44ff44' : '#ff4444',
        }).setOrigin(0.5).setDepth(2)

        const nextBtn = this.add.text(width - 12, y + cardH - 18, '→ Next question', {
          fontFamily: 'monospace', fontSize: '10px', color: '#888888',
        }).setOrigin(1, 0.5).setDepth(2).setInteractive({ useHandCursor: true })
        nextBtn.on('pointerdown', () => { this._triviaState = null; this._render() })
        this._objs.push(nextBtn)
      }
    }
    return y + cardH + 8
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
    y = this._cardBg(y, 90)

    this.add.text(12, y + 8, '🎰 Slots  (10 🪙/spin)', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)

    if (this._slotsResult) {
      const { reels, net } = this._slotsResult
      this.add.text(width / 2, y + 38, reels.join('  '), {
        fontFamily: 'monospace', fontSize: '22px',
      }).setOrigin(0.5).setDepth(2)
      this.add.text(width / 2, y + 66, net >= 0 ? `+${net} 🪙` : `${net} 🪙`, {
        fontFamily: 'monospace', fontSize: '12px', color: net >= 0 ? '#44ff44' : '#ff4444',
      }).setOrigin(0.5).setDepth(2)
    }

    const btn = this.add.rectangle(width - 14, y + 38, 80, 26, 0x4a2a0a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
    const btnLabel = this.add.text(width - 14, y + 38, '🎰 SPIN', {
      fontFamily: 'monospace', fontSize: '11px', color: '#ffcc44',
    }).setOrigin(1, 0.5).setDepth(2)
    btn.on('pointerdown', () => this._spinSlots())
    btn.on('pointerover', () => btn.setFillStyle(0x6a4a1a))
    btn.on('pointerout', () => btn.setFillStyle(0x4a2a0a))
    this._objs.push(btn, btnLabel)
    return y + 98
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
    y = this._cardBg(y, 90)
    if (!this._gambBet) this._gambBet = 50

    this.add.text(12, y + 8, '💰 Coin Flip', {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffffff',
    }).setDepth(1)

    // Bet controls
    const minusBtn = this.add.text(14, y + 44, '[-]', {
      fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
    }).setDepth(2).setInteractive({ useHandCursor: true })
    minusBtn.on('pointerdown', () => { this._gambBet = Math.max(10, this._gambBet - 10); this._render() })

    const betLabel = this.add.text(70, y + 44, `${this._gambBet} 🪙`, {
      fontFamily: 'monospace', fontSize: '13px', color: '#ffd700',
    }).setOrigin(0, 0.5).setDepth(2)

    const plusBtn = this.add.text(140, y + 44, '[+]', {
      fontFamily: 'monospace', fontSize: '13px', color: '#aaaaaa',
    }).setDepth(2).setInteractive({ useHandCursor: true })
    plusBtn.on('pointerdown', () => { this._gambBet = Math.min(500, this._gambBet + 10); this._render() })

    if (this._gambResult) {
      const { won, delta } = this._gambResult
      this.add.text(width / 2, y + 66, won ? `✅ +${delta} 🪙` : `❌ ${delta} 🪙`, {
        fontFamily: 'monospace', fontSize: '13px', color: won ? '#44ff44' : '#ff4444',
      }).setOrigin(0.5).setDepth(2)
    }

    const btn = this.add.rectangle(width - 14, y + 44, 80, 26, 0x3a1a4a).setOrigin(1, 0.5).setDepth(1).setInteractive({ useHandCursor: true })
    const btnLabel = this.add.text(width - 14, y + 44, '🪙 FLIP', {
      fontFamily: 'monospace', fontSize: '11px', color: '#dd88ff',
    }).setOrigin(1, 0.5).setDepth(2)
    btn.on('pointerdown', () => this._gamble())
    btn.on('pointerover', () => btn.setFillStyle(0x5a2a6a))
    btn.on('pointerout', () => btn.setFillStyle(0x3a1a4a))

    this._objs.push(minusBtn, betLabel, plusBtn, btn, btnLabel)
    return y + 98
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

  // ── Helpers ──────────────────────────────────────────────────────────────────

  _cardBg(y, h) {
    const { width } = this.scale
    const bg = this.add.rectangle(8, y, width - 16, h, 0x1a2a3a).setOrigin(0, 0).setDepth(0)
    this._objs.push(bg)
    return y + 8
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
