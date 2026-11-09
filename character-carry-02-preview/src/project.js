import { createScene } from './scene.js'

// Add independent scene factories here. Each receives its own SDK instance.
export function createProject() {
  return {
    id: 'red-girl-carry-02',
    name: '红衣卡通女孩 · 搬运走路',
    defaultSceneId: 'main',
    scenes: [{ id: 'main', name: '搬运走路', createScene }],
  }
}
