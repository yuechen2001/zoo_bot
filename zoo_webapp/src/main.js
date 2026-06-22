import Phaser from 'phaser'
import BootScene from './scenes/BootScene.js'
import ZooScene from './scenes/ZooScene.js'
import CatchScene from './scenes/CatchScene.js'
import BreedScene from './scenes/BreedScene.js'
import EnclosureScene from './scenes/EnclosureScene.js'
import StoreScene from './scenes/StoreScene.js'
import QuestScene from './scenes/QuestScene.js'
import GamesScene from './scenes/GamesScene.js'
import InventoryScene from './scenes/InventoryScene.js'
import AchievementsScene from './scenes/AchievementsScene.js'
import InspectScene from './scenes/InspectScene.js'
import DirectoryScene from './scenes/DirectoryScene.js'
import AutofeedScene from './scenes/AutofeedScene.js'

const config = {
  type: Phaser.AUTO,
  width: window.innerWidth,
  height: window.innerHeight,
  backgroundColor: '#1a1a2e',
  pixelArt: true,
  scene: [BootScene, ZooScene, CatchScene, BreedScene, EnclosureScene, StoreScene, QuestScene, GamesScene, InventoryScene, AchievementsScene, InspectScene, DirectoryScene, AutofeedScene],
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
}

window.game = new Phaser.Game(config)
