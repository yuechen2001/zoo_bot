const API_BASE = '/api/v1'

function getInitData() {
  return window.Telegram?.WebApp?.initData || ''
}

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
    },
  }
  if (body !== null) opts.body = JSON.stringify(body)
  const res = await fetch(API_BASE + path, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getMe: () => request('GET', '/user/me'),
  getAnimals: () => request('GET', '/animals'),
  feedAnimal: (id) => request('POST', `/animals/${id}/feed`),
  nameAnimal: (id, nickname) => request('POST', `/animals/${id}/name`, { nickname }),
  sellAnimal: (id) => request('POST', `/animals/${id}/sell`),

  startCatch: (lure_key = null) => request('POST', '/catch/start', { lure_key }),

  getBreed: () => request('GET', '/breed'),
  startBreed: (animal_a_id, animal_b_id) => request('POST', '/breed/start', { animal_a_id, animal_b_id }),
  collectBreed: () => request('POST', '/breed/collect'),

  getEnclosures: () => request('GET', '/enclosures'),
  upgradeEnclosure: (habitat) => request('POST', `/enclosures/${habitat}/upgrade`),
  collectEnclosure: () => request('POST', '/enclosures/collect'),

  getStore: () => request('GET', '/store'),
  buyItem: (item_key) => request('POST', '/store/buy', { item_key }),

  getInventory: () => request('GET', '/inventory'),
  useItem: (item_key) => request('POST', '/inventory/use', { item_key }),
  equipTitle: (title_key) => request('POST', '/inventory/equip', { title_key }),
  unequipTitle: () => request('POST', '/inventory/equip', { title_key: null }),

  getQuests: () => request('GET', '/quests'),
  getAchievements: () => request('GET', '/achievements'),
  getDirectory: () => request('GET', '/directory'),
  getAutofeed: () => request('GET', '/autofeed'),
  setAutofeed: (threshold, max_coins) => request('POST', '/autofeed', { threshold, max_coins }),
  disableAutofeed: () => request('POST', '/autofeed', {}),

  getPendingEscape: () => request('GET', '/escapes/pending'),
  resolveEscape: (escape_id, action) => request('POST', `/escapes/${escape_id}/resolve`, { action }),

  getActiveWildEvent: () => request('GET', '/wild-events/active'),
  claimWildEvent: (event_id) => request('POST', `/wild-events/${event_id}/claim`),

  getInvestment: () => request('GET', '/investments'),
  createInvestment: (amount) => request('POST', '/investments/create', { amount }),
  collectInvestment: () => request('POST', '/investments/collect'),

  massageAnimals: () => request('POST', '/minigames/massage'),

  claimDaily: () => request('POST', '/daily/claim'),
  getTriviaQuestion: () => request('GET', '/trivia/question'),
  answerTrivia: (question, answer, wager = 0) => request('POST', '/trivia/answer', { question, answer, wager }),
  gamble: (bet) => request('POST', '/gamble', { bet }),
  spinSlots: () => request('POST', '/slots/spin'),
}
