// Singleton holding live player state, shared across all scenes
const GameState = {
  user: null,
  animals: [],
  enclosures: {},
  quests: null,
  inventory: [],

  setUser(u) { this.user = u },
  setAnimals(a) { this.animals = a },
  setEnclosures(e) { this.enclosures = e },
  setQuests(q) { this.quests = q },
  setInventory(inv) { this.inventory = inv },

  animalsByHabitat() {
    const map = {}
    for (const a of this.animals) {
      const h = a.habitat || 'woodland'
      if (!map[h]) map[h] = []
      map[h].push(a)
    }
    return map
  },

  activeQuestTask() {
    if (!this.quests) return null
    const active = this.quests.chapters?.find(ch => ch.is_active)
    if (!active) return null
    const task = active.tasks?.find(t => !t.done)
    return task
      ? `Ch${active.chapter_num}: ${task.desc}`
      : `Ch${active.chapter_num}: ${active.title} ✅`
  },

  lureQty(key) {
    return this.inventory?.lures?.[key] ?? 0
  },
}

export default GameState
