import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'

const POWERUP_LABELS = [
  ['lucky_catch_active', '🎯'],
  ['mood_booster_active', '✨'],
  ['catch_net_active', '🪤'],
  ['rare_magnet_active', '🧲'],
  ['epic_magnet_active', '💜'],
  ['streak_shield_active', '🛡️'],
]

const NAV = [
  { label: 'CATCH', scene: 'Catch' },
  { label: 'BREED', scene: 'Breed' },
  { label: 'ZOO', scene: 'Zoo' },
  { label: 'STORE', scene: 'Store' },
  { label: 'QUESTS', scene: 'Quests' },
  { label: 'GAMES', scene: 'Games' },
]

export default class HUD {
  constructor(scene) {
    this.scene = scene
    this.depth = 100
    this._build()
  }

  _build() {
    const s = this.scene
    const W = s.scale.width

    // Top bar background
    this.topBar = s.add.rectangle(0, 0, W, 40, 0x0d1b2a, 0.95).setOrigin(0, 0).setDepth(this.depth)
    this.topBarBorder = s.add.rectangle(0, 40, W, 2, 0xffd700).setOrigin(0, 0).setDepth(this.depth)

    // Coins
    this.coinsText = s.add.text(8, 6, '🪙 0', {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffd700',
    }).setDepth(this.depth)

    // Streak
    this.streakText = s.add.text(W / 2, 6, '🔥 0', {
      fontFamily: 'monospace', fontSize: '14px', color: '#ff9944',
    }).setOrigin(0.5, 0).setDepth(this.depth)

    // Achievements trophy button
    this.trophyBtn = s.add.text(W - 8, 6, '🏆', {
      fontSize: '16px',
    }).setOrigin(1, 0).setDepth(this.depth).setInteractive({ useHandCursor: true })
    this.trophyBtn.on('pointerdown', () => s.scene.start('Achievements'))

    // Power-ups (right of streak, left of trophy)
    this.powerupText = s.add.text(W - 28, 6, '', {
      fontFamily: 'monospace', fontSize: '12px', color: '#aaddff',
    }).setOrigin(1, 0).setDepth(this.depth)

    // Quest banner
    this.questBar = s.add.rectangle(0, 42, W, 24, 0x1a3a1a, 0.9).setOrigin(0, 0).setDepth(this.depth)
    this.questText = s.add.text(8, 46, '📜 —', {
      fontFamily: 'monospace', fontSize: '11px', color: '#88ff88',
    }).setDepth(this.depth)

    // Bottom nav bar
    const H = s.scale.height
    this.navBar = s.add.rectangle(0, H - 48, W, 48, 0x0d1b2a, 0.95).setOrigin(0, 0).setDepth(this.depth)
    this.navBorder = s.add.rectangle(0, H - 48, W, 2, 0xffd700).setOrigin(0, 0).setDepth(this.depth)

    const btnW = W / NAV.length
    this.navButtons = NAV.map((item, i) => {
      const x = btnW * i + btnW / 2
      const isActive = item.scene === s.scene.key
      const btn = s.add.text(x, H - 24, item.label, {
        fontFamily: 'monospace', fontSize: '10px', color: isActive ? '#ffd700' : '#cccccc',
      }).setOrigin(0.5).setDepth(this.depth).setInteractive({ useHandCursor: true })
      btn.on('pointerdown', () => { if (!isActive) s.scene.start(item.scene) })
      btn.on('pointerover', () => btn.setColor('#ffd700'))
      btn.on('pointerout', () => btn.setColor(isActive ? '#ffd700' : '#cccccc'))
      return btn
    })

    this.update()
    this._startPoll()
  }

  _startPoll() {
    this.scene.time.addEvent({
      delay: 20000,
      loop: true,
      callback: async () => {
        try {
          const user = await api.getMe()
          GameState.setUser(user)
          this.update()
        } catch (_) {}
      },
    })
  }

  update() {
    const u = GameState.user
    if (!u) return
    this.coinsText.setText(`🪙 ${u.coins}`)
    this.streakText.setText(`🔥 ${u.streak_windows}`)
    const active = POWERUP_LABELS.filter(([k]) => u[k]).map(([, icon]) => icon).join(' ')
    this.powerupText.setText(active)

    const task = GameState.activeQuestTask()
    if (task) this.questText.setText(`📜 ${task}`)
  }

  setQuestBanner(text) {
    this.questText.setText(`📜 ${text}`)
  }

  resize(W, H) {
    this.topBar.setSize(W, 40)
    this.topBarBorder.setSize(W, 2)
    this.streakText.setX(W / 2)
    this.trophyBtn.setX(W - 8)
    this.powerupText.setX(W - 28)
    this.questBar.setSize(W, 24)
    this.navBar.setPosition(0, H - 48).setSize(W, 48)
    this.navBorder.setPosition(0, H - 48)
    const btnW = W / NAV.length
    this.navButtons.forEach((btn, i) => btn.setPosition(btnW * i + btnW / 2, H - 24))
  }
}
