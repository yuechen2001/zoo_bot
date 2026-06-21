// Singleton holding live player state, shared across all scenes
const GameState = {
  user: null,       // user row from /user/me
  animals: [],      // from /animals
  enclosures: {},   // from /enclosures

  setUser(u) { this.user = u },
  setAnimals(a) { this.animals = a },
  setEnclosures(e) { this.enclosures = e },

  animalsByHabitat() {
    const map = {}
    for (const a of this.animals) {
      const h = a.habitat || 'woodland'
      if (!map[h]) map[h] = []
      map[h].push(a)
    }
    return map
  },
}

export default GameState
