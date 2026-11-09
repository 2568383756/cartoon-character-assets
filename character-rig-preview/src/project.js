import { createScene } from './scene.js'

// Add independent scene factories here. Each receives its own SDK instance.
export function createProject() {
  return {
    id: 'character-rig-preview',
    name: '卡通人物 · 绑骨预览',
    defaultSceneId: 'main',
    scenes: [{ id: 'main', name: '角色绑定', createScene }],
  }
}
