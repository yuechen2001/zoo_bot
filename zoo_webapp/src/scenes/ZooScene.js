import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'
import HUD from './HUD.js'

const HABITATS = [
  { key: 'woodland', name: 'Woodland', emoji: '🌲' },
  { key: 'savanna', name: 'Savanna', emoji: '🌾' },
  { key: 'tropical', name: 'Tropical', emoji: '🌴' },
  { key: 'aquatic', name: 'Aquatic', emoji: '🐠' },
  { key: 'tundra', name: 'Tundra', emoji: '❄️' },
  { key: 'mythic', name: 'Mythic', emoji: '✨' },
  { key: 'spectral', name: 'Spectral', emoji: '👻' },
  { key: 'desert', name: 'Desert', emoji: '🏜️' },
]

const RARITY_COLORS = { common: '#888888', rare: '#4488ff', epic: '#aa44ff', legendary: '#ffaa00' }
const COLS = 2
const TILE_W = 140
const TILE_H = 110
const PAD_X = 8
const PAD_Y = 8
const TOP_OFFSET = 68   // below HUD + quest banner
const BOTTOM_OFFSET = 56

export default class ZooScene extends Phaser.Scene {
  constructor() { super('Zoo') }

  create() {
    this.hud = new HUD(this)
    this._animalPanel = null
    this._tiles = []
    this._animalSprites = []

    this._buildWorld()
    this._setupBreedPoller()

    this.scale.on('resize', (gameSize) => {
      this.hud.resize(gameSize.width, gameSize.height)
      this._rebuildWorld()
    })
  }

  _buildWorld() {
    const { width, height } = this.scale
    this._tiles.forEach(o => o.destroy())
    this._animalSprites.forEach(o => o.destroy())
    this._tiles = []
    this._animalSprites = []

    const animalsByHabitat = GameState.animalsByHabitat()
    const scrollH = Math.ceil(HABITATS.length / COLS) * (TILE_H + PAD_Y) + TOP_OFFSET + BOTTOM_OFFSET

    // Make the scene scrollable if content overflows
    if (this.scrollContainer) this.scrollContainer.destroy()
    this.scrollContainer = this.add.container(0, 0)

    HABITATS.forEach(({ key, name, emoji }, i) => {
      const col = i % COLS
      const row = Math.floor(i / COLS)
      const x = PAD_X + col * (TILE_W + PAD_X)
      const y = TOP_OFFSET + row * (TILE_H + PAD_Y)

      // Habitat background
      const bg = this.add.image(x, y, `bg_${key}`).setOrigin(0, 0).setDisplaySize(TILE_W, TILE_H)
      this._tiles.push(bg)
      this.scrollContainer.add(bg)

      // Habitat label
      const label = this.add.text(x + 4, y + 4, `${emoji} ${name}`, {
        fontFamily: 'monospace', fontSize: '10px', color: '#ffffff',
        stroke: '#000000', strokeThickness: 2,
      })
      this._tiles.push(label)
      this.scrollContainer.add(label)

      // Enclosure level badge
      const encLevel = GameState.enclosures[key]?.level || 1
      const lvlBadge = this.add.text(x + TILE_W - 4, y + 4, `Lv${encLevel}`, {
        fontFamily: 'monospace', fontSize: '9px', color: '#ffd700',
        stroke: '#000000', strokeThickness: 1,
      }).setOrigin(1, 0)
      this._tiles.push(lvlBadge)
      this.scrollContainer.add(lvlBadge)

      // Animals
      const animals = animalsByHabitat[key] || []
      animals.slice(0, 8).forEach((animal, ai) => {
        const ac = ai % 4
        const ar = Math.floor(ai / 4)
        const ax = x + 6 + ac * 32
        const ay = y + 22 + ar * 36

        const sprite = this.add.image(ax, ay, `animal_${animal.rarity}`)
          .setOrigin(0, 0)
          .setDisplaySize(22, 22)
          .setInteractive({ useHandCursor: true })

        sprite.on('pointerdown', () => this._showAnimalPanel(animal))
        sprite.on('pointerover', () => sprite.setAlpha(0.7))
        sprite.on('pointerout', () => sprite.setAlpha(1))

        // Emoji label
        const emojiLabel = this.add.text(ax + 11, ay, animal.emoji || '🐾', {
          fontSize: '14px',
        }).setOrigin(0.5, 0)

        // Hunger bar
        const barBg = this.add.rectangle(ax, ay + 24, 22, 3, 0x333333).setOrigin(0, 0)
        const barFill = this.add.rectangle(ax, ay + 24, Math.round(22 * animal.hunger / 100), 3,
          animal.hunger > 50 ? 0x44ff44 : animal.hunger > 20 ? 0xffaa00 : 0xff3333
        ).setOrigin(0, 0)

        // Breeding lock
        if (animal.is_breeding) {
          this.add.text(ax + 11, ay + 10, '🔒', { fontSize: '10px' }).setOrigin(0.5)
        }

        // Shiny sparkle
        if (animal.is_shiny) {
          this.add.text(ax + 20, ay, '⭐', { fontSize: '8px' }).setOrigin(0.5, 0)
        }

        this._animalSprites.push(sprite, emojiLabel, barBg, barFill)
        this.scrollContainer.add([sprite, emojiLabel, barBg, barFill])
      })

      // Empty slot indicator
      if (animals.length === 0) {
        const empty = this.add.text(x + TILE_W / 2, y + TILE_H / 2, 'Empty', {
          fontFamily: 'monospace', fontSize: '10px', color: '#555555',
        }).setOrigin(0.5)
        this._tiles.push(empty)
        this.scrollContainer.add(empty)
      }
    })

    // Enable drag-to-scroll if content is taller than screen
    const usableH = height - TOP_OFFSET - BOTTOM_OFFSET
    const contentH = Math.ceil(HABITATS.length / COLS) * (TILE_H + PAD_Y)
    if (contentH > usableH) {
      this.input.on('pointermove', (p) => {
        if (p.isDown) {
          this.scrollContainer.y = Phaser.Math.Clamp(
            this.scrollContainer.y + p.velocity.y * 0.3,
            -(contentH - usableH),
            0,
          )
        }
      })
    }
  }

  _rebuildWorld() {
    this._buildWorld()
  }

  _showAnimalPanel(animal) {
    if (this._animalPanel) {
      this._animalPanel.forEach(o => o.destroy())
      this._animalPanel = null
    }

    const { width, height } = this.scale
    const panelW = Math.min(260, width - 20)
    const panelH = 180
    const px = (width - panelW) / 2
    const py = (height - panelH) / 2

    const objs = []
    const bg = this.add.rectangle(px, py, panelW, panelH, 0x0d1b2a, 0.97).setOrigin(0, 0).setDepth(50)
    const border = this.add.rectangle(px, py, panelW, panelH).setStrokeStyle(2, 0xffd700).setOrigin(0, 0).setDepth(50)

    const name = animal.nickname || animal.species_name || '?'
    const rarity = animal.rarity || 'common'
    const rarityColor = RARITY_COLORS[rarity] || '#ffffff'

    const title = this.add.text(px + panelW / 2, py + 12, `${animal.emoji || '🐾'} ${name}`, {
      fontFamily: 'monospace', fontSize: '14px', color: '#ffffff',
    }).setOrigin(0.5, 0).setDepth(50)

    const rarityLabel = this.add.text(px + panelW / 2, py + 30, rarity.toUpperCase(), {
      fontFamily: 'monospace', fontSize: '11px', color: rarityColor,
    }).setOrigin(0.5, 0).setDepth(50)

    const hungerLabel = this.add.text(px + panelW / 2, py + 50, `Hunger: ${animal.hunger}/100`, {
      fontFamily: 'monospace', fontSize: '11px', color: '#aaaaaa',
    }).setOrigin(0.5, 0).setDepth(50)

    // Action buttons
    const actions = [
      { label: '🍖 Feed', action: () => this._feedAnimal(animal) },
      { label: '✏️ Name', action: () => this._promptName(animal) },
      { label: '💰 Sell', action: () => this._sellAnimal(animal) },
      { label: '✕ Close', action: () => { objs.forEach(o => o.destroy()); this._animalPanel = null } },
    ]

    const btnW = (panelW - 16) / 2
    actions.forEach((act, i) => {
      const bx = px + 8 + (i % 2) * (btnW + 4)
      const by = py + 75 + Math.floor(i / 2) * 40
      const btnBg = this.add.rectangle(bx, by, btnW, 30, 0x1a3a5a).setOrigin(0, 0).setDepth(50).setInteractive({ useHandCursor: true })
      const btnLabel = this.add.text(bx + btnW / 2, by + 15, act.label, {
        fontFamily: 'monospace', fontSize: '11px', color: '#ffffff',
      }).setOrigin(0.5).setDepth(51)
      btnBg.on('pointerdown', act.action)
      btnBg.on('pointerover', () => btnBg.setFillStyle(0x2a5a8a))
      btnBg.on('pointerout', () => btnBg.setFillStyle(0x1a3a5a))
      objs.push(btnBg, btnLabel)
    })

    objs.push(bg, border, title, rarityLabel, hungerLabel)
    this._animalPanel = objs
  }

  async _feedAnimal(animal) {
    try {
      const res = await api.feedAnimal(animal.animal_id)
      animal.hunger = res.hunger
      GameState.user.coins -= res.coins_spent
      this.hud.update()
      this._rebuildWorld()
      if (this._animalPanel) {
        this._animalPanel.forEach(o => o.destroy())
        this._animalPanel = null
      }
    } catch (err) {
      this._showToast(err.message)
    }
  }

  async _sellAnimal(animal) {
    try {
      const res = await api.sellAnimal(animal.animal_id)
      GameState.user.coins += res.coins_earned
      GameState.setAnimals(GameState.animals.filter(a => a.animal_id !== animal.animal_id))
      this.hud.update()
      this._rebuildWorld()
      if (this._animalPanel) {
        this._animalPanel.forEach(o => o.destroy())
        this._animalPanel = null
      }
      this._showToast(`Sold for ${res.coins_earned} 🪙`)
    } catch (err) {
      this._showToast(err.message)
    }
  }

  _promptName(animal) {
    const nickname = prompt(`Name for ${animal.emoji || ''} ${animal.species_name}:`, animal.nickname || '')
    if (nickname !== null && nickname.trim()) {
      api.nameAnimal(animal.animal_id, nickname.trim()).then(() => {
        animal.nickname = nickname.trim()
        this._rebuildWorld()
        if (this._animalPanel) {
          this._animalPanel.forEach(o => o.destroy())
          this._animalPanel = null
        }
      }).catch(err => this._showToast(err.message))
    }
  }

  _showToast(msg) {
    const { width, height } = this.scale
    const t = this.add.text(width / 2, height - 70, msg, {
      fontFamily: 'monospace', fontSize: '12px', color: '#ff6666',
      backgroundColor: '#000000cc', padding: { x: 8, y: 4 },
    }).setOrigin(0.5).setDepth(200)
    this.time.delayedCall(2500, () => t.destroy())
  }

  _setupBreedPoller() {
    this.time.addEvent({
      delay: 30000,
      loop: true,
      callback: async () => {
        try {
          const breed = await api.getBreed()
          if (breed.active && breed.is_ready && !breed.collected) {
            this.hud.setQuestBanner('🐣 Your breed is ready! Open BREED to collect.')
          }
        } catch (_) {}
      },
    })
  }
}
