import Phaser from 'phaser'
import { api } from '../api.js'
import GameState from '../GameState.js'

const HABITATS = ['woodland', 'savanna', 'tropical', 'aquatic', 'tundra', 'mythic', 'spectral', 'desert']
const RARITY_COLORS = { common: 0x888888, rare: 0x4488ff, epic: 0xaa44ff, legendary: 0xffaa00 }

export default class BootScene extends Phaser.Scene {
  constructor() { super('Boot') }

  preload() {
    // Generate placeholder pixel sprites for each rarity
    const g = this.make.graphics({ x: 0, y: 0, add: false })
    for (const [rarity, color] of Object.entries(RARITY_COLORS)) {
      g.clear()
      g.fillStyle(color)
      g.fillRect(0, 0, 16, 16)
      g.generateTexture(`animal_${rarity}`, 16, 16)
    }
    // Habitat background tiles
    const habitatColors = {
      woodland: 0x1a4a1a, savanna: 0x6b5a1a, tropical: 0x1a4a3a,
      aquatic: 0x1a2a6b, tundra: 0xd0e8ff, mythic: 0x2a1a4a,
      spectral: 0x1a1a2a, desert: 0x8b6914,
    }
    for (const [hab, color] of Object.entries(habitatColors)) {
      g.clear()
      g.fillStyle(color)
      g.fillRect(0, 0, 120, 80)
      g.fillStyle(0x000000, 0.15)
      g.strokeRect(0, 0, 120, 80)
      g.generateTexture(`bg_${hab}`, 120, 80)
    }
    // Player character placeholder
    g.clear()
    g.fillStyle(0xffe0b0)
    g.fillRect(4, 0, 8, 8)   // head
    g.fillStyle(0x4466cc)
    g.fillRect(3, 8, 10, 8)  // body
    g.generateTexture('player', 16, 16)
    g.destroy()
  }

  async create() {
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()
    }

    const { width, height } = this.scale

    // Loading screen
    this.add.text(width / 2, height / 2 - 20, '🐾 ZOO BOT', {
      fontFamily: 'monospace', fontSize: '28px', color: '#ffd700',
    }).setOrigin(0.5)

    const status = this.add.text(width / 2, height / 2 + 20, 'Loading your zoo...', {
      fontFamily: 'monospace', fontSize: '14px', color: '#aaaaaa',
    }).setOrigin(0.5)

    try {
      const [user, animals, enclosures] = await Promise.all([
        api.getMe(),
        api.getAnimals(),
        api.getEnclosures(),
      ])
      GameState.setUser(user)
      GameState.setAnimals(animals)
      GameState.setEnclosures(enclosures)
      this.scene.start('Zoo')
    } catch (err) {
      status.setText(`Error: ${err.message}`)
    }
  }
}
